from django.utils.translation import ugettext as _

from django.core.mail import EmailMessage

import logging, sys, urllib, urllib2, MySQLdb, os.path, unicodedata, traceback, urlparse
from cStringIO import StringIO
from zipfile import BadZipfile
from xml.sax.saxutils import escape as xml_escape

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
from django.views.decorators.cache import cache_page, cache_control, never_cache
from django.views.decorators.vary import vary_on_headers, vary_on_cookie

from django_authopenid.views import signin

from bookworm.library.epub import InvalidEpubException
from bookworm.library.models import EpubArchive, HTMLFile, StylesheetFile, ImageFile, SystemInfo, get_file_by_item, order_fields, DRMEpubException, UserArchive
from bookworm.library.forms import EpubValidateForm, ProfileForm
from bookworm.library.epub import constants as epub_constants
from bookworm.library.google_books.search import Request
from bookworm.library.epub import epubcheck

log = logging.getLogger('library.views')

@never_cache
def index(request):
    '''Public home page.  This should be heavily cached (in fact eventually should be
    served only by the web server.)'''
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('library'))
    # If this is a mobile user, skip the public page
    if settings.MOBILE:
        return signin(request)
    return direct_to_template(request, "public.html", {})


@login_required
@never_cache
def library(request,
          page_number=settings.DEFAULT_START_PAGE, 
          order=settings.DEFAULT_ORDER_FIELD,
          dir=settings.DEFAULT_ORDER_DIRECTION):
    '''Users's library listing.  The page itself should not be cached although 
    individual items in the library should be cached at the model level.'''
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
    paginator = Paginator(EpubArchive.objects.filter(user_archive__user=user).order_by(order_computed).distinct(), settings.DEFAULT_NUM_RESULTS)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        page_number = settings.DEFAULT_START_PAGE
        # If we somehow got to an invalid page number, start over
        return HttpResponseRedirect(reverse('library-paginate', args=[page_number]))

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
                                             'order_direction': _('ascending') if dir == 'asc' else _('descending'),
                                             'order_adverb': _('alphabetically') if order != 'created_time' else _('by date value'),
                                             }
                              )

# We can't cache this at the page level because the user may be
# going to the last-read page rather than the document start
@never_cache
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
        try:
            toc = document.get_toc()
            first_item = toc.first_item()
            chapter = get_file_by_item(first_item, document)
        except InvalidEpubException:
            # We got some kind of catastrophic error while trying to 
            # parse this document
            message = _('There was a problem reading the metadata for this document.')
            return view_chapter(request, title, key, None, message=message)
        if chapter is None:
            log.error('Could not find an item with the id of %s' % first_item)
            raise Http404
        if first:
            log.debug("Forcing first chapter")
            # Force an HTTP redirect so we get a clean URL but go to the correct chapter ID
            return HttpResponseRedirect(reverse('view_chapter', kwargs={'title':document.safe_title(), 'key': document.id, 'chapter_id':chapter.filename}))
    return view_chapter(request, title, key, None, chapter=chapter, document=document)


# Not cacheable either because it may be a different user
@never_cache
def view_chapter(request, title, key, chapter_id, chapter=None, document=None, google_books=None, message=None):
    if chapter is not None:
        chapter_id = chapter.id

    log.debug("Looking up title %s, key %s, chapter %s" % (title, key, chapter_id))    

    if not document:
        document = _get_document(request, title, key)

    if chapter is None:
        # Legacy objects may have more than one duplicate representation
        h =  HTMLFile.objects.filter(archive=document, filename=chapter_id)
        if h.count() == 0:
            raise Http404
        chapter = h[0]

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
        stylesheets = chapter.stylesheets.all()[0:settings.MAX_CSS_FILES]

        # If we got 0 stylesheets, this may be a legacy book
        if len(stylesheets) == 0:
            stylesheets = StylesheetFile.objects.filter(archive=document)[0:settings.MAX_CSS_FILES]

    except InvalidEpubException, e:
        log.error(traceback.format_exc())
        chapter = None
        stylesheets = None
        message = _('''
This book contained content that Bookworm couldn't read.  You may need to check with the 
publisher that this is a valid ePub book that contains either XHTML or DTBook-formatted
content.''')



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


@cache_page(60 * 15)
@cache_control(private=True)
def view_chapter_image(request, title, key, image):
    log.debug("Image request: looking up title %s, key %s, image %s" % (title, key, image))        
    document = _get_document(request, title, key)
    try: 
        image_obj = ImageFile.objects.filter(archive=document, filename=image)[0]
    except IndexError:
        image = os.path.basename(image)
        try:
            image_obj = ImageFile.objects.filter(archive=document, filename=image)[0]
        except IndexError:
            raise Http404
    response = HttpResponse(content_type=str(image_obj.content_type))
    if image_obj.content_type == 'image/svg+xml':
        response.content = image_obj.file
    else:
        try:
            response.content = image_obj.get_data()
        except AttributeError: # Zero-length image
            raise Http404

    return response

@cache_page(60 * 15)
@cache_control(public=True)
def view_stylesheet(request, title, key, stylesheet_id):
    document = _get_document(request, title, key)
    log.debug('getting stylesheet %s' % stylesheet_id)
    stylesheets = StylesheetFile.objects.filter(archive=document,filename=stylesheet_id)
    if len(stylesheets) == 0:
        raise Http404
    stylesheet = stylesheets[0]
    response = HttpResponse(content=stylesheet.file, content_type='text/css')
    return response

@cache_control(private=True)
def download_epub(request, title, key, nonce=None):
    '''Return the epub archive content.  If it's accidentally been deleted
    off the storage mechanism (usually this happens in development), return
    a 404 instead of a zero-byte download.'''
    document = _get_document(request, title, key, nonce=nonce)
    if document is None:
        raise Http404        
    if document.get_content() is None: # This occurs if the file has been deleted unexpected from the filesystem
        raise Http404        
    content = document.get_content().read()
    if content is None:
        raise Http404
    response = HttpResponse(content=content, content_type=epub_constants.MIMETYPE)
    safe_name = unicodedata.normalize('NFKC', document.name).encode('ASCII', 'backslashreplace').replace(' ', '_')
    response['Content-Disposition'] = 'attachment; filename=%s' % safe_name
    return response    
  
def view_document_metadata(request, title, key):
    log.debug("Looking up metadata %s, key %s" % (title, key))
    document = _get_document(request, title, key)
    if not document:
        raise Http404
    google_books = _get_google_books_info(document, request)
    form = EpubValidateForm()        
    return direct_to_template(request, 'view.html', {'document':document, 'form': form, 'google_books':google_books})

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

        # They should be the owner of this book to delete it
        if document is not None and document.is_owner(request.user):
            _delete_document(request, document)
        else:
            raise Http404
    return HttpResponseRedirect(reverse('library'))

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
@never_cache
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
        message = _("Your profile has been updated.")
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
        message = _("There was a problem with your request to delete this profile.")
        return direct_to_template(request, 'profile.html', { 'message':message})

    if not request.POST['delete'] == request.user.email:
        # And that we're POSTing from our own form (this is a sanity check, 
        # not a security feature.  The current logged-in user profile is always
        # the one to be deleted, regardless of the value of 'delete')
        log.error('Received deletion request but nickname did not match: received %s but current user is %s' % (request.POST['delete'], request.user.nickname()))
        message = _("There was a problem with your request to delete this profile.")
        return direct_to_template(request, 'profile.html', { 'message':message})

    request.user.get_profile().delete()

    # Delete all their books (this is likely to time out for large numbers of books)
    documents = EpubArchive.objects.filter(user_archive__user=request.user)

    for d in documents:
        _delete_document(request, d)

    return HttpResponseRedirect('/') # fixme: actually log them out here


@login_required
def profile_toggle_reading_mode(request):
    '''Toggle whether to use the simple reading more or the default mode.'''
    if request.method == 'POST':
        profile = request.user.get_profile()
        profile.simple_reading_mode = not(profile.simple_reading_mode)
        log.debug('setting reading mode to %s' % profile.simple_reading_mode)
        profile.save()
    url = request.META.get('HTTP_REFERER')
    if url is None:
        url = '/library/'
    return HttpResponseRedirect(url)

@login_required
def profile_change_font_size(request, size):
    '''Change the font size associated with the user's account'''
    if request.method == 'POST':
        profile = request.user.get_profile()
        profile.font_size = size;
        log.debug('setting font size to %s' % profile.font_size)
        profile.save()
    return HttpResponse('1')

@login_required
def profile_change_font_family(request, font):
    '''Change the font family associated with the user's account'''
    if request.method == 'POST':
        profile = request.user.get_profile()
        profile.font_family = font;
        log.debug('setting font family to %s' % profile.font_family)
        profile.save()
    return HttpResponse('1')


@login_required
def upload(request, title=None, key=None):
    '''Uploads a new document and stores it in the database.  If 'title' and 'key'
    are provided then this is a reload of an existing document, which should retain
    the same ID.  The user must be an existing owner to reload a book.'''
    document = None 

    if request.method == 'POST':
        form = EpubValidateForm(request.POST, request.FILES)

        if form.is_valid():
            # The temporary file assigned by Django
            temp_file = request.FILES['epub'].temporary_file_path()
            document_name = form.cleaned_data['epub'].name
            if not key:
                log.debug("Creating new document: '%s'" % document_name)
                document = EpubArchive(name=document_name)
                document.save()
            else:
                log.debug("Reloading existing document: '%s'" % document_name) 
                try:
                    document = EpubArchive.objects.get(id__exact=key)
                    log.debug(document.title)
                    log.debug(request.user)

                    # Is thie an owner of the document?
                    if UserArchive.objects.filter(user=request.user,
                                                  owner=True,
                                                  archive=document).count() == 0:
                        raise Http404

                    # Save off some metadata about it
                    is_public = document.is_public

                    # Delete the old one
                    document.delete()

                    # Create a new one with the possibly-new name
                    document = EpubArchive(name=document_name,id=key)
                    document.is_public = is_public
                    document.save()
                    successful_redirect = reverse('view_first', kwargs={'key':key,
                                                                        'title':title,
                                                                        })

                except EpubArchive.DoesNotExist:
                    log.error("Key %s did not exist; creating new document" % (key))
                    document = EpubArchive(name=document_name)                    
                    document.save()

            return add_data_to_document(request, document, open(temp_file, 'rb+'), form)

        # The form isn't valid (generally because we didn't actually upload anything)
        return direct_to_template(request, 'upload.html', {'form':form})


    else:
        form = EpubValidateForm()        

    return direct_to_template(request, 'upload.html', {'form':form})

def add_data_to_document(request, document, data, form, redirect_success_to_page=True):
    '''Add epub data (as a file-like object) to a document, then explode it.
       If this returns True, return a successful redirect; otherwise return an error template.
       If the redirect_to_page parameter is True (default), the code will redirect

       '''
    successful_redirect = reverse('library')

    document.set_content(data)

    try:
        document.explode()
        document.user_archive.create(archive=document,
                                     owner=True,
                                     user=request.user)
        document.save()

    except BadZipfile, e:
        # The user tried to upload something that wasn't a zip
        # file. This error isn't interesting; don't send email
        m = _('The file you uploaded was not recognized as an ePub archive and could not be added to your library.')
        return _report_error(request, document, data, m, form, e, email=False)

    except MySQLdb.OperationalError, e:
        # This occurs normally when a single large transaction
        # is passed to MySQL. If you get many of these,
        # increase the value of the MySQL config value
        # max_allowed_packet (> 16M recommended).
        m = _(u"We detected a problem with your ebook that is most likely related to it being too big to display safely in a web browser. This can happen with very large images, or with extremely long chapters. Please check with the publisher that the book has been formatted correctly.  Very large pages would require a lot of scrolling and load very slowly, so they are not allowed to be added to Bookworm.")
        return _report_error(request, document, data, m, form, e, email=True)

    except DRMEpubException, e:
        # DRM is evil
        m = _(u"It appears that you've uploaded a book which contains DRM (Digital Rights Management).  This is a restriction that is meant to prevent illegal copying but also prevents legitimate owners from reading their ebooks wherever they like. You will probably need to use Adobe Digital Editions to read this ebook, but consider contacting the publisher or bookseller to ask them about releasing DRM-free ebooks.")
        return _report_error(request, document, data, m, form, e, email=False)

    except Exception, e:
        # We got some unknown error (usually a malformed epub).  We
        # want to know about these since they are sometimes actually Bookworm bugs.

        if settings.SKIP_EPUBCHECK:
            return direct_to_template(request, 'upload.html', {'form':form, 
                                                               'message':str(e)})                
        _email_errors_to_admin(e, data, document)

        # Delete it first so we don't end up with a broken document in the library
        document.delete()

        # Let's see what's wrong with this by asking epubcheck too, since it will let us know if it's our bug
        valid_resp = epubcheck.validate(data)

        error = _exception_message(e)
        if len(error) > 200:
            error = error[0:200] + u'...'

        message = []
        message.append(_(u"<p class='bw-upload-message'>The file you uploaded looks like an ePub archive, but it has some problems that prevented it from being loaded.  This may be a bug in Bookworm, or it may be a problem with the way the ePub file was created. The complete error message is:</p>"))
        message.append(_(u"<p class='bw-upload-errors'>%s</p>" % xml_escape(error)))

        # Let's see what's wrong with this by asking epubcheck too, since it will let us know if it's our bug
        valid_resp = epubcheck.validate(data)

        if valid_resp is None:
            # We got nothing useful from the validator (oops)
            pass
        elif len(valid_resp) == 0:
            message.append(_(u"<p>(epubcheck thinks this file is valid, so this may be a Bookworm error)</p>"))
        else:
            e = '\n'.join([i.text for i in valid_resp])
            errors = ['<li>%s</li>' % i.replace('\n', '<br/>')  for i in e.split('ERROR:') if i]
            message.append(_(u"<p class='bw-upload-message'><a href='http://code.google.com/p/epubcheck/'>epubcheck</a> agrees that this is not a valid ePub file, so you should check with the publisher or content creator. It returned <strong id='bw-num-errors'>%d</strong> error(s):</p>" % len(errors)))
            message.append(u" <ol id='bw-upload-error-list'>%s</ol>" % ''.join(errors))
        
        return direct_to_template(request, 'upload.html', {'form':form, 
                                                           'message':u''.join(message)})                

    if redirect_success_to_page:
        return HttpResponseRedirect(successful_redirect)
    return document


@login_required
@never_cache
def add_by_url(request):
    '''Accepts a GET request with parameter 'epub' which should be valid ePub URL.  This will be added
    to the current logged-in user's library'''
    if not 'epub' in request.GET:
        raise Http404
    epub_url = request.GET['epub']
    return add_by_url_field(request, epub_url, redirect_success_to_page=True)

def add_by_url_field(request, epub_url, redirect_success_to_page):
    form = EpubValidateForm()

    try:
        data = urllib2.urlopen(epub_url).read()
        data = StringIO(data)
    except urllib2.URLError:
        message = _("The address you provided does not point to an ePub book")
        return direct_to_template(request, 'upload.html', {'form':form, 
                                                           'message':message})                
        
    document = EpubArchive.objects.create(name=os.path.basename(urlparse.urlparse(epub_url).path))
    document.save()
    return add_data_to_document(request, document, data, form, redirect_success_to_page)
    

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

    # Delete the book itself
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


def _report_error(request, document, data, user_message, form, exception, email=False):
    '''Report an error with an uploaded book to the user.

    Required:
      - The request object
      - The document object created (will be deleted)
      - The data uploaded by the user
      - A message to the user 
      - The form
      - The exception raised

    Setting 'email' to True will send a message to the value defined
    in settings.ERROR_EMAIL_RECIPIENTS (by default this is the first
    admin in settings.ADMINS).  
    '''
    log.error(exception)
    document.delete()
    if email:
        # Email it to the admins
        _email_errors_to_admin(exception, data, document)

    return direct_to_template(request, 'upload.html', { 'form':form, 'message':user_message})    

                              
def _email_errors_to_admin(exception, data, document):
    '''Send am email to the users registered to receive these messages (the value of
    settings.ERROR_EMAIL_RECIPIENTS (by default this is the first admin in settings.ADMINS).  
    '''
    # Email it to the admins
    message = _exception_message(exception)

    email = EmailMessage(u'[bookworm-error] %s (book=%s)' % (message, document.name),
                         settings.REPLYTO_EMAIL,
                         settings.ERROR_EMAIL_RECIPIENTS)
    email.attach(document.name, data, epub_constants.MIMETYPE)


def _exception_message(exception):
    '''Return unicode string from exception.'''

    try:
        return exception.__unicode__()     # Python 2.6
    except AttributeError:
        return unicode(exception.message)  # Python 2.5



