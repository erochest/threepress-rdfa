from django.core.mail import EmailMessage

import logging, sys, StringIO, urllib
from zipfile import BadZipfile

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.forms import UserCreationForm
from django.contrib import auth
from django.template import RequestContext
from django.core.paginator import Paginator, EmptyPage

from models import EpubArchive, HTMLFile, UserPref, StylesheetFile, ImageFile, SystemInfo, get_file_by_item, order_fields
from forms import EpubValidateForm, ProfileForm
from epub import constants as epub_constants
from epub import InvalidEpubException
from django.conf import settings

log = logging.getLogger('views')

def register(request):
    form = UserCreationForm()
                                            
    if request.method == 'POST':
        data = request.POST.copy()
        errors = form.get_validation_errors(data)
        if not errors:
            new_user = form.save(data)
            user = auth.authenticate(username=new_user.username, password=request.POST['password1'])
            if user is not None and user.is_active:
                auth.login(request, user)
                return HttpResponseRedirect(reverse('library.views.index'))
    else:
        data, errors = {}, {}

    return render_to_response("auth/register.html", 
                              { 'form' : form })


@login_required
def index(request, 
          page_number=settings.DEFAULT_START_PAGE, 
          order=settings.DEFAULT_ORDER_FIELD,
          dir=settings.DEFAULT_ORDER_DIRECTION):

    if not dir in settings.VALID_ORDER_DIRECTIONS:
        raise Exception("Direction %s was not in our list of known ordering directions" % dir)
    if not order in settings.VALID_ORDER_FIELDS:
        raise Exception("Field %s was not in our list of known ordering fields" % order)
    if dir == 'desc':
        order_computed = '-%s' % order
        reverse_dir = 'asc'
    else:
        order_computed = order
        reverse_dir = 'desc'

    _common(request, load_prefs=True)
    if page_number is None:
        page_number = settings.DEFAULT_START_PAGE
    user = request.user
    form = EpubValidateForm()
    paginator = Paginator(EpubArchive.objects.filter(owner=user).order_by(order_computed), settings.DEFAULT_NUM_RESULTS)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        page_number = settings.DEFAULT_START_PAGE
        # If we somehow got to an invalid page number, start over
        return HttpResponseRedirect(reverse('index-paginate', args=[page_number]))

    for d in page.object_list:
        if d.orderable_author == '':
            # Populate the author field if it was empty before
            d.orderable_author = d.safe_author()
            d.save()
        
    return render_to_response('index.html', {'documents':paginator, 
                                             'page':page,
                                             'form':form,
                                             'order':order,
                                             'dir':dir,
                                             'reverse_dir':reverse_dir,
                                             'order_text': order_fields[order],
                                             'order_direction': 'ascending' if dir == 'asc' else 'descending',
                                             'order_adverb': 'alphabetically' if order != 'created_time' else 'by date value',
                                             },
                                             context_instance=RequestContext(request)
                              )

@login_required
def profile(request):
    _check_switch_modes(request)

    uprofile = request.user.get_profile()
    
    if request.openid:
        sreg = request.openid.sreg
        # If we have the email from OpenID and not in their profile, pre-populate it
        if not request.user.email and sreg.has_key('email'):
            request.user.email = sreg['email']
        if sreg.has_key('fullname'):
            uprofile.fullname = sreg['fullname']
        if sreg.has_key('nickname'):
            uprofile.nickname = sreg['nickname']
        if sreg.has_key('timezone'):
            uprofile.timezone = sreg['timezone']
        if sreg.has_key('language'):
            uprofile.language = sreg['language']
        if sreg.has_key('country'):
            uprofile.country = sreg['country']
        uprofile.save()
        _check_switch_modes(request)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=uprofile)
        if form.is_valid():
            form.save()
        message = "Your profile has been updated."
    else:
        form = ProfileForm(instance=uprofile)
        message = None

    return render_to_response('auth/profile.html', {'form':form, 'prefs':uprofile, 'message':message}, context_instance=RequestContext(request))

@login_required
def view(request, title, key, first=False, resume=False):
    '''If we view just a document, we want to either see our last chapter,
    or see the first item in the <opf:spine>, as required by the epub specification.'''

    log.debug("Looking up title %s, key %s" % (title, key))

    _check_switch_modes(request)
    document = _get_document(request, title, key)

    uprofile = request.user.get_profile()

    if resume and document.last_chapter_read is not None:
        chapter = document.last_chapter_read
    elif not first and uprofile.open_to_last_chapter and document.last_chapter_read is not None:
        chapter = document.last_chapter_read
    else:
        toc = document.get_toc()
        first = toc.first_item()
        chapter = get_file_by_item(first, document)
        if chapter is None:
            log.error('Could not find an item with the id of %s' % first)
            raise Http404
    return view_chapter(request, title, key, None, chapter=chapter)

  
@login_required
def view_document_metadata(request, title, key):
    log.debug("Looking up metadata %s, key %s" % (title, key))
    _check_switch_modes(request)
    document = _get_document(request, title, key)
    return render_to_response('view.html', {'document':document}, 
                              context_instance=RequestContext(request))


def about(request):
    _common(request)
    return render_to_response('about.html', context_instance=RequestContext(request))
    
@login_required
def delete(request):
    '''Delete a book and associated metadata, and decrement our total books counter'''

    if request.POST.has_key('key') and request.POST.has_key('title'):
        title = request.POST['title']
        key = request.POST['key']
        log.debug("Deleting title %s, key %s" % (title, key))
        if request.user.is_superuser:
            document = _get_document(request, title, key, override_owner=True)
        else:
            document = _get_document(request, title, key)
        _delete_document(request, document)

    return HttpResponseRedirect('/')

@login_required
def profile_delete(request):
    _common(request)

    if not request.POST.has_key('delete'):
        # Extra sanity-check that this is a POST request
        log.error('Received deletion request but was not POST')
        message = "There was a problem with your request to delete this profile."
        return render_to_response('profile.html', { 'message':message})

    if not request.POST['delete'] == request.user.email:
        # And that we're POSTing from our own form (this is a sanity check, 
        # not a security feature.  The current logged-in user profile is always
        # the one to be deleted, regardless of the value of 'delete')
        log.error('Received deletion request but nickname did not match: received %s but current user is %s' % (request.POST['delete'], request.user.nickname()))
        message = "There was a problem with your request to delete this profile."
        return render_to_response('profile.html', { 'message':message})

    userprefs = _prefs(request)
    userprefs.delete()

    # Decrement our total-users counter
    counter = _get_system_info(request)
    counter.decrement_total_users()

    # Delete all their books (this is likely to time out for large numbers of books)
    documents = EpubArchive.objects.filter(owner=request.user)

    for d in documents:
        _delete_document(request, d)
    

    return HttpResponseRedirect('/') # fixme: actually log them out here

def _check_switch_modes(request):
    '''Did they switch viewing modes?'''
    _common(request, load_prefs=True)
    userprefs = request.session['common']['prefs']

    if request.GET.has_key('iframe'):
        userprefs.use_iframe = (request.GET['iframe'] == 'yes')
        userprefs.save()

    if request.GET.has_key('iframe_note'):
        userprefs.show_iframe_note = (request.GET['iframe_note'] == 'yes')
        userprefs.save()


@login_required    
def view_chapter(request, title, key, chapter_id, chapter=None):
    if chapter is not None:
        chapter_id = chapter.id

    log.debug("Looking up title %s, key %s, chapter %s" % (title, key, chapter_id))    
    document = _get_document(request, title, key)

    if chapter is None:
        chapter = get_object_or_404(HTMLFile, archive=document, filename=chapter_id)

    stylesheets = StylesheetFile.objects.filter(archive=document)
    next = _chapter_next_previous(document, chapter, 'next')
    previous = _chapter_next_previous(document, chapter, 'previous')

    parent_chapter = None
    subchapter_href = None

    toc = document.get_top_level_toc()

    for t in toc:
        href = chapter.filename.encode(epub_constants.ENC)
        if href in [c.href() for c in t.find_descendants()]:
            parent_chapter = t
            subchapter_href = href
            break

    _check_switch_modes(request)
    return render_to_response('view.html', {'chapter':chapter,
                                            'document':document,
                                            'next':next,
                                            'toc':toc,
                                            'subchapter_href':subchapter_href,
                                            'parent_chapter':parent_chapter,
                                            'stylesheets':stylesheets,
                                            'previous':previous},
                              context_instance=RequestContext(request))
    
    
def _chapter_next_previous(document, chapter, dir='next'):
    '''Returns the next or previous data object from the OPF'''
    toc = document.get_toc()
    item = toc.find_item_by_id(chapter.idref)

    if dir == 'next':
        target_item = toc.find_next_item(item)
    else:
        target_item = toc.find_previous_item(item)
    if target_item is None:
        return None
    object = get_file_by_item(target_item, document)
    return object


@login_required    
def view_chapter_image(request, title, key, image):
    log.debug("Image request: looking up title %s, key %s, image %s" % (title, key, image))        
    document = _get_document(request, title, key)
    image = get_object_or_404(ImageFile, archive=document, filename=image)
    response = HttpResponse(content_type=str(image.content_type))
    if image.content_type == 'image/svg+xml':
        response.content = image.file
    else:
        response.content = image.get_data()

    return response

@login_required
def view_chapter_frame(request, title, key, chapter_id):
    '''Generate an iframe to display the document online, possibly with its own stylesheets'''
    document = _get_document(request, title, key)
    chapter = HTMLFile.objects.get(archive=document, filename=chapter_id)
    stylesheets = StylesheetFile.objects.filter(archive=document)
    next = _chapter_next_previous(document, chapter, 'next')
    previous = _chapter_next_previous(document, chapter, 'previous')

    return render_to_response('frame.html', {'document':document, 
                                             'chapter':chapter, 
                                             'next':next,
                                             'previous':previous,
                                             'stylesheets':stylesheets})

@login_required
def view_stylesheet(request, title, key, stylesheet_id):
    document = _get_document(request, title, key)
    log.debug('getting stylesheet %s' % stylesheet_id)
    stylesheet = get_object_or_404(StylesheetFile, archive=document,filename=stylesheet_id)
    response = HttpResponse(content=stylesheet.file, content_type='text/css')
    response['Cache-Control'] = 'public'

    return response

@login_required
def download_epub(request, title, key):
    document = _get_document(request, title, key)
    response = HttpResponse(content=document.get_content(), content_type=epub_constants.MIMETYPE)
    response['Content-Disposition'] = 'attachment; filename=%s' % document.name
    return response

@login_required
def upload(request):
    '''Uploads a new document and stores it in the datastore'''
    
    _common(request)
    
    document = None 
    
    if request.method == 'POST':
        form = EpubValidateForm(request.POST, request.FILES)
        if form.is_valid():

            data = StringIO.StringIO()
            for c in request.FILES['epub'].chunks():
                data.write(c)
            #data.close()
            document_name = form.cleaned_data['epub'].name
            log.debug("Uploading document name: %s" % document_name)
            document = EpubArchive(name=document_name)
            document.owner = request.user
            document.save()
            document.set_content(data.getvalue())

            try:
                document.explode()
                document.save()
                sysinfo = _get_system_info(request)
                sysinfo.increment_total_books()
                # Update the cache
                #memcache.set('total_books', sysinfo.total_books)

            except BadZipfile:
                log.error('Non-zip archive uploaded: %s' % document_name)
                log.error(sys.exc_value)
                message = 'The file you uploaded was not recognized as an ePub archive and could not be added to your library.'
                document.delete()
                return render_to_response('upload.html', {
                                                          'form':form, 
                                                          'message':message})
            except Exception, e:
                # Delete it first so we don't end up with a broken document in the library
                try:
                    # Email it to the admins
                    email = EmailMessage('[bookworm] Failed upload', '', 'no-reply@threepress.org',
                                         ['liza@threepress.org'])
                    email.attach(document_name, data.getvalue(), epub_constants.MIMETYPE)
                    email.send()
                except Exception, f:
                    log.error(f)

                document.delete()

                # Let's see what's wrong with this by asking epubcheck too, since it will let us know if it's our bug
                resp = urllib.urlopen('http://www.threepress.org/epubcheck-service/', data.getvalue())
                epubcheck_response = None
                if resp:
                    d = resp.read()
                    if d:
                        try:
                            from epub import util
                            epubcheck_response =  util.xml_from_string(d)
                        except Exception, e2:
                            log.error('Got an error when trying to XML-ify the epubecheck response; ignoring: %s' % e2)
                
                log.error('Non epub zip file uploaded: %s' % document_name)
                error = e.__str__()
                if len(error) > 100:
                    error = error[0:100] + '...'
                message = "The file you uploaded looks like an ePub archive, but it has some problems that prevented it from being loaded.  This may be a bug in Bookworm, or it may be a problem with the way the ePub file was created. The complete error message is: <p style='color:black;font-weight:normal'>%s</p>" % error
                if epubcheck_response is not None:
                    if epubcheck_response.findtext('.//is-valid') == 'True':
                        message += "<p>(epubcheck thinks this file is valid, so this is probably a Bookworm error)</p>"
                    elif epubcheck_response.findtext('.//is-valid') == 'False':
                        epub_errors = epubcheck_response.findall('.//error')
                        epub_error_list = [i.text for i in epub_errors]

                        epub_errors = '<br/>'.join(epub_error_list)
                        message += "<p><a href='http://code.google.com/p/epubcheck/'>epubcheck</a> agrees that this is not a valid ePub file, so you should check with the publisher or content creator. It returned: <pre style='color:black;font-weight:normal'>%s</pre></p>" % epub_errors
                    else:
                        log.error('Got an unexpected response from epubcheck, ignoring: %s' % d)


                                     

                
                return render_to_response('upload.html', {'form':form, 
                                                          'message':message})                
            #except:
            #    # If we got any error, delete this document
            #    log.error('Got unknown error on request, deleting document')
            #    log.error(sys.exc_value)
            #    document.delete()
            #    raise
            
            log.debug("Successfully added %s" % document.title)
            return HttpResponseRedirect('/')

        return HttpResponseRedirect('/')

    else:
        form = EpubValidateForm()        

    return render_to_response('upload.html', {
                                              'form':form},
                              context_instance=RequestContext(request)) 



def _delete_document(request, document):
    # Delete the chapters of the book 
    toc = HTMLFile.objects.filter(archive=document)
    if toc:
        for t in toc:
            t.delete()

    # Delete all the stylesheets in the book
    css = StylesheetFile.objects.filter(archive=document)
    if css:
        for c in css:
            c.delete()

    # Delete all the images in the book
    images = ImageFile.objects.filter(archive=document)
    if images:
        for i in images:
            i.delete()

    # Delete the book itself, and decrement our counter
    document.delete()
    sysinfo = _get_system_info(request)
    sysinfo.decrement_total_books()

def _get_document(request, title, key, override_owner=False):
    '''Return a document by Google key and owner.  Setting override_owner
    will search regardless of ownership, for use with admin accounts.'''
    user = request.user

    document = get_object_or_404(EpubArchive, pk=key)

    if not override_owner and document.owner != user and not user.is_superuser:
        log.error('User %s tried to access document %s, which they do not own' % (user, title))
        raise Http404

    return document



def _greeting(request):
    return None

def _prefs(request):
    '''Get (or create) a user preferences object for a given user.
    If created, the total number of users counter will be incremented and
    the memcache updated.'''
    user = request.user
    try:
        userprefs = user.get_profile()
    except AttributeError:
        # Occurs when this is called on an anonymous user; ignore
        return None
    except UserPref.DoesNotExist:
        log.debug('Creating a userprefs object for %s' % user.username)
        # Create a preference object for this user
        userprefs = UserPref(user=user)
        userprefs.save()

        # Increment our total-users counter
        counter = _get_system_info(request)

        counter.increment_total_users()
  
    return userprefs

def _common(request, load_prefs=False):
    '''Builds a dictionary of common 'globals' into the request
    @todo cache some of this, like from sysinfo'''

    request.session['common']  = {}
    common = {}
    common['user'] = request.user
    common['is_admin'] = request.user.is_superuser
    common['prefs'] = _prefs(request)
    common['total_users'] = _get_system_info(request).get_total_users()
    common['total_books'] = _get_system_info(request).get_total_books()
    common['greeting'] = _greeting(request)
    common['mobile'] = settings.MOBILE 


    request.session.modified = True
    request.session['common'] = common


def _get_system_info(request):
    '''Super-primitive caching system'''
    if not 'system_info' in request.session:
        request.session['system_info'] = SystemInfo()
    return request.session['system_info']
    
