from django.core.mail import EmailMessage

import logging, sys, urllib, MySQLdb, cStringIO, os.path, unicodedata, time
from zipfile import BadZipfile

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.forms import UserCreationForm
from django.contrib import auth
from django.template import RequestContext
from django.core.paginator import Paginator, EmptyPage
from django.views.generic.simple import direct_to_template
from django.conf import settings

from django_authopenid.views import signin

from search import epubindexer
from library.epub import InvalidEpubException
from library.models import EpubArchive, HTMLFile, StylesheetFile, ImageFile, SystemInfo, get_file_by_item, order_fields, DRMEpubException, UnknownContentException, UserArchive
from library.forms import EpubValidateForm, ProfileForm
from library.epub import constants as epub_constants
from library.google_books.search import Request

log = logging.getLogger('library.views')

def index(request, 
          page_number=settings.DEFAULT_START_PAGE, 
          order=settings.DEFAULT_ORDER_FIELD,
          dir=settings.DEFAULT_ORDER_DIRECTION):
    if request.user.is_authenticated():
        return logged_in_home(request, page_number, order, dir)

    # If this is a mobile user, skip the public page
    if settings.MOBILE:
        return signin(request)
    return direct_to_template(request, "public.html", {})

def logged_in_home(request, page_number, order, dir):
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
  
    if page_number is None:
        page_number = settings.DEFAULT_START_PAGE
    user = request.user
    form = EpubValidateForm()
    paginator = Paginator(EpubArchive.objects.filter(user_archive__user=user,is_deleted=False).order_by(order_computed).distinct(), settings.DEFAULT_NUM_RESULTS)
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

    sysinfo = SystemInfo()
    return direct_to_template(request, 'index.html', {'documents':paginator, 
                                             'page':page,
                                             'form':form,
                                             'order':order,
                                             'dir':dir,
                                             'total_users':sysinfo.get_total_users(),
                                             'total_books':sysinfo.get_total_books(),
                                             'reverse_dir':reverse_dir,
                                             'order_text': order_fields[order],
                                             'order_direction': 'ascending' if dir == 'asc' else 'descending',
                                             'order_adverb': 'alphabetically' if order != 'created_time' else 'by date value',
                                             }
                              )

def view(request, title, key, first=False, resume=False):
    '''If we view just a document, we want to either see our last chapter,
    or see the first item in the <opf:spine>, as required by the epub specification.'''

    log.debug("Looking up title %s, key %s" % (title, key))

    document = _get_document(request, title, key)

    # If we got 'None' from get_document with an anonymous user, then prompt them
    # to login; this is probably just a bookmark with an unauthenticated user
    if document is None and request.user.is_anonymous():
        return HttpResponseRedirect(reverse('user_signin'))

    if not request.user.is_anonymous():
        uprofile = request.user.get_profile()
        last_chapter_read = document.get_last_chapter_read(request.user)
    else:
        last_chapter_read = None
        uprofile = None

    if resume and last_chapter_read is not None:
        chapter = last_chapter_read
    elif not first and uprofile and uprofile.open_to_last_chapter and last_chapter_read:
        chapter = last_chapter_read
    else:
        toc = document.get_toc()
        first = toc.first_item()
        chapter = get_file_by_item(first, document)
        if chapter is None:
            log.error('Could not find an item with the id of %s' % first)
            raise Http404
    return view_chapter(request, title, key, None, chapter=chapter)

def view_chapter(request, title, key, chapter_id, chapter=None, google_books=None, message=None):
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
    # Check whether this will render without throwing an exception
    try:
        chapter.render()
    except InvalidEpubException, e:
        import traceback
        tb =  traceback.format_exc()
        log.error(tb)
        log.error(e)
        chapter = None
        message = '''
This book contained content that Bookworm couldn't read.  You may need to check with the 
publisher that this is a valid ePub book that contains either XHTML or DTBook-formatted
content.'''

    return direct_to_template(request, 'view.html', {'chapter':chapter,
                                            'document':document,
                                            'next':next,
                                            'message':message,      
                                            'toc':toc,
                                            'subchapter_href':subchapter_href,
                                            'parent_chapter':parent_chapter,
                                            'stylesheets':stylesheets,
                                            'google_books':google_books,
                                            'previous':previous})

def view_chapter_image(request, title, key, image):
    log.debug("Image request: looking up title %s, key %s, image %s" % (title, key, image))        
    document = _get_document(request, title, key)
    try: 
        image_obj = get_object_or_404(ImageFile, archive=document, filename=image)
    except Http404:
        image = os.path.basename(image)
        image_obj = get_object_or_404(ImageFile, archive=document, filename=image)
    response = HttpResponse(content_type=str(image_obj.content_type))
    if image_obj.content_type == 'image/svg+xml':
        response.content = image_obj.file
    else:
        response.content = image_obj.get_data()

    return response


def view_stylesheet(request, title, key, stylesheet_id):
    document = _get_document(request, title, key)
    log.debug('getting stylesheet %s' % stylesheet_id)
    stylesheet = get_object_or_404(StylesheetFile, archive=document,filename=stylesheet_id)
    response = HttpResponse(content=stylesheet.file, content_type='text/css')
    response['Cache-Control'] = 'public'
    return response

def download_epub(request, title, key, nonce=None):
    '''Return the epub archive content.  If it's accidentally been deleted
    off the storage mechanism (usually this happens in development), return
    a 404 instead of a zero-byte download.'''
    document = _get_document(request, title, key, nonce=nonce)
    content = document.get_content()
    if content is None:
        raise Http404
    response = HttpResponse(content=content, content_type=epub_constants.MIMETYPE)
    safe_name = unicodedata.normalize('NFKC', document.name).encode('ASCII', 'backslashreplace')
    response['Content-Disposition'] = 'attachment; filename=%s' % safe_name
    return response    
  
def view_document_metadata(request, title, key):
    log.debug("Looking up metadata %s, key %s" % (title, key))
    document = _get_document(request, title, key)
    google_books = _get_google_books_info(document, request)
    return direct_to_template(request, 'view.html', {'document':document, 'google_books':google_books})

@login_required
def delete(request):
    '''Delete a book and associated metadata, and decrement our total books counter'''

    if 'key' in request.POST and 'title' in request.POST:
        title = request.POST['title']
        key = request.POST['key']
        log.debug("Deleting title %s, key %s" % (title, key))
        if request.user.is_superuser:
            document = _get_document(request, title, key, override_owner=True)
        else:
            document = _get_document(request, title, key)
        _delete_document(request, document)

    return HttpResponseRedirect('/')

def register(request):
    '''Register a new user on Bookworm'''

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
    return direct_to_template(request, "auth/register.html", { 'form' : form })

@login_required
def profile(request):
    uprofile = RequestContext(request).get('profile')
    
    if request.openid:
        sreg = request.openid.sreg
        # If we have the email from OpenID and not in their profile, pre-populate it
        if not request.user.email and sreg.has_key('email'):
            request.user.email = sreg['email']
        if sreg.has_key('fullname'):
            uprofile.fullname = sreg['fullname']
        if sreg.has_key('nickname'):
            uprofile.nickname = sreg['nickname']

        # These should only be updated if they haven't already been changed
        if uprofile.timezone is None and sreg.has_key('timezone'):
            uprofile.timezone = sreg['timezone']
        if uprofile.language is None and sreg.has_key('language'):
            uprofile.language = sreg['language']
        if uprofile.country is None and sreg.has_key('country'):
            uprofile.country = sreg['country']
        uprofile.save()
    
    if settings.LANGUAGE_COOKIE_NAME in request.session:
        log.debug("Updating language to %s" % request.session.get(settings.LANGUAGE_COOKIE_NAME))
        uprofile.language = request.session.get(settings.LANGUAGE_COOKIE_NAME)
        uprofile.save()

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=uprofile)
        if form.is_valid():
            form.save()
        message = "Your profile has been updated."
    else:
        form = ProfileForm(instance=uprofile)
        message = None
    if 'msg' in request.GET:
        message = request.GET['msg']

    return direct_to_template(request,
                              'auth/profile.html', 
                              {'form':form, 'prefs':uprofile, 'message':message})

@login_required
def profile_delete(request):

    if not request.POST.has_key('delete'):
        # Extra sanity-check that this is a POST request
        log.error('Received deletion request but was not POST')
        message = "There was a problem with your request to delete this profile."
        return direct_to_template(request, 'profile.html', { 'message':message})

    if not request.POST['delete'] == request.user.email:
        # And that we're POSTing from our own form (this is a sanity check, 
        # not a security feature.  The current logged-in user profile is always
        # the one to be deleted, regardless of the value of 'delete')
        log.error('Received deletion request but nickname did not match: received %s but current user is %s' % (request.POST['delete'], request.user.nickname()))
        message = "There was a problem with your request to delete this profile."
        return direct_to_template(request, 'profile.html', { 'message':message})

    request.user.get_profile().delete()

    # Delete all their books (this is likely to time out for large numbers of books)
    documents = EpubArchive.objects.filter(user_archive__user=request.user)

    for d in documents:
        _delete_document(request, d)

    return HttpResponseRedirect('/') # fixme: actually log them out here


@login_required
def upload(request):
    '''Uploads a new document and stores it in the database'''
    document = None 
    
    if request.method == 'POST':
        form = EpubValidateForm(request.POST, request.FILES)
        if form.is_valid():

            data = cStringIO.StringIO()
            for c in request.FILES['epub'].chunks():
                data.write(c)
            document_name = form.cleaned_data['epub'].name
            log.debug("Uploading document name: %s" % document_name)
            document = EpubArchive(name=document_name)
            document.save()
            document.set_content(data.getvalue())

            try:
                document.explode()
                document.user_archive.create(archive=document,
                                             user=request.user)
                document.save()

            except BadZipfile:
                log.error('Non-zip archive uploaded: %s' % document_name)
                log.error(sys.exc_value)
                message = 'The file you uploaded was not recognized as an ePub archive and could not be added to your library.'
                document.delete()
                return direct_to_template(request, 'upload.html', 
                                          { 'form':form, 'message':message})

            except MySQLdb.OperationalError, e:
                log.debug("Got operational error %s" % e)
                message = "We detected a problem with your ebook that is most likely related to it being too big to display safely in a web browser. This can happen with very large images, or with extremely long chapters. Please check with the publisher that the book has been formatted correctly.  Very large pages would require a lot of scrolling and load very slowly, so they are not allowed to be added to Bookworm."
                try:
                    # Email it to the admins
                    email = EmailMessage('[bookworm] Too-large book added: %s' % document_name, e.__str__(), 'no-reply@threepress.org',
                                         ['liza@threepress.org'])
                    email.attach(document_name, data.getvalue(), epub_constants.MIMETYPE)
                    email.send()
                except Exception, f:
                    log.error(f)


                return direct_to_template(request, 'upload.html', {'form':form, 'message':message})                
            except DRMEpubException, e:
                import traceback
                tb =  traceback.format_exc()
                log.error(tb)
                # Delete it first so we don't end up with a broken document in the library
                try:
                    # Email it to the admins
                    email = EmailMessage('[bookworm] Got DRM epub as %s' % document_name, tb, 'no-reply@threepress.org',
                                         ['liza@threepress.org'])
                    email.attach(document_name, data.getvalue(), epub_constants.MIMETYPE)
                    email.send()
                except Exception, f:
                    log.error(f)

                document.delete()
                message = "It appears that you've uploaded a book which contains DRM (Digital Rights Management).  This is a restriction that is meant to prevent illegal copying but also prevents legitimate owners from reading their ebooks wherever they like. You will probably need to use Adobe Digital Editions to read this ebook, but consider contacting the publisher or bookseller to ask them about releasing DRM-free ebooks."
                return direct_to_template(request, 'upload.html', 
                                          { 'form':form, 'message':message})
                
            except Exception, e:
                import traceback
                tb =  traceback.format_exc()
                log.error(tb)
                # Delete it first so we don't end up with a broken document in the library
                try:
                    # Email it to the admins
                    email = EmailMessage('[bookworm] Failed upload for %s' % document_name, tb, 'no-reply@threepress.org',
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
                if len(error) > 200:
                    error = error[0:200] + '...'
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
                
                return direct_to_template(request, 'upload.html', {'form':form, 
                                                                   'message':message})                
            log.debug("Successfully added %s" % document.title)
            return HttpResponseRedirect('/')

        return direct_to_template(request, 'upload.html', {
                'form':form})


    else:
        form = EpubValidateForm()        

    return direct_to_template(request, 'upload.html', {'form':form})

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


def _delete_document(request, document):
    # Delete the chapters of the book
    # Actually this should occur in the indexing phase since these chapters are needed for
    # full deletion
    #toc = HTMLFile.objects.filter(archive=document)
    #if toc:
    #    for t in toc:
    #        t.delete()

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

    # Delete the book itself (here we will only be setting a flag)
    document.delete()

def _get_document(request, title, key, override_owner=False, nonce=None):
    '''Return a document by id and owner.  Setting override_owner
    will search regardless of ownership, for use with admin accounts.'''
    user = request.user

    document = get_object_or_404(EpubArchive, pk=key)

    if nonce:
        if document.is_nonce_valid(nonce):
            return document
        else:
            log.error("Got an expired or invalid nonce: '%s', nonce='%s'" % (title, nonce))
            raise Http404

    # Anonymous users can never access non-public books
    if not document.is_public and user.is_anonymous():
        log.error('Anonymous user tried to access non-public document %s' % (document.title))
        return None
        
    if not document.is_public and not override_owner and not document.is_owner(user) and not user.is_superuser:
        log.error('User %s tried to access document %s, which they do not own' % (user, title))
        raise Http404

    return document

def _get_google_books_info(document, request):
    # Find all the words in the title and all the names in the author by splitting on 
    # spaces and commas
    title_words = document.title.replace(',', '').split(' ')
    author_words = document.author.replace(',', '').split(' ')
    for t in title_words:
        query = 'intitle:%s+' % urllib.quote(t.encode('utf8'))
    for a in author_words:
        query += 'inauthor:%s+' % urllib.quote(a.encode('utf8'))
    if 'REMOTE_ADDR' in request.META:
        remote_addr = request.META['REMOTE_ADDR']
    else:
        remote_addr = None
    return Request(query, remote_addr).get()


