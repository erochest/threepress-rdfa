from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.generic.simple import direct_to_template
from django.core.urlresolvers import reverse

from bookworm.library import models 
from bookworm.library.views import download_epub, add_by_url_field, add_data_to_document
from bookworm.api import HttpResponseCreated, BookwormHttpResponseNotAcceptable 
from bookworm.api.forms import APIUploadForm

@never_cache
@login_required
def main(request, SSL=True):
    '''Main entry point; dispatch by request type for upload vs. GET operations'''
    if request.method == 'GET':
        # No-arg GET request is a library listing; return all the user's documents
        documents = models.EpubArchive.objects.filter(user_archive__user=request.user).order_by(settings.DEFAULT_ORDER_FIELD).distinct()
        return direct_to_template(request, 'api/list.html', 
                                  {'documents': documents})

    # Accept an epub file either by URL or by direct POST file upload with epub bytes as `epub_data`
    elif request.method == 'POST':
        resp = None
        if 'epub_url' in request.POST:
            resp = add_by_url_field(request, request.POST['epub_url'], redirect_success_to_page=False)        

        elif request.FILES:
            form = APIUploadForm(request.POST, request.FILES)
            if form.is_valid():
                temp_file = request.FILES['epub_data'].temporary_file_path()
                document_name = form.cleaned_data['epub_data'].name
                document = models.EpubArchive.objects.create(name=document_name)
                document.save()
                resp = add_data_to_document(request, document, open(temp_file), form, redirect_success_to_page=False)
                
            else:
                return BookwormHttpResponseNotAcceptable('You did not provide a correctly-formatted epub_data parameter: %s' % form.errors) 
        else:
            return BookwormHttpResponseNotAcceptable("You must either include epub_url or epub_data in your request")

        if isinstance(resp, models.EpubArchive):
            # This was a successful add and we got back a document
            return HttpResponseCreated("%s%s" % (settings.SECURE_HOSTNAME, reverse('api_download', args=[resp.id])))

        # Otherwise this was an error condition
        return BookwormHttpResponseNotAcceptable(resp) # Include the complete Bookworm response

    else:
        return HttpResponseNotAllowed('GET, POST')


@never_cache
@login_required
def api_download(request, epub_id, SSL=True):
    '''Download an epub file by its ID'''
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')

    return download_epub(request, '', epub_id)


