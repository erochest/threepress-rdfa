from django.core.mail import EmailMessage

import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.core.paginator import Paginator, EmptyPage
from django.views.generic.simple import direct_to_template
from django.conf import settings

import results
import epubindexer
import constants
from forms import EpubSearchForm

log = logging.getLogger('search.views')

@login_required
def search(request, book_id=None):

    if not 'q' in request.GET and not 'language' in request.GET:
        return direct_to_template(request, 'results.html')

    form = EpubSearchForm(request.GET)

    if not form.is_valid():
        return direct_to_template(request, 'results.html', { 'search_form': form })     

   
    start = int(request.GET['start']) if request.GET.has_key('start') else 1
    end = int(request.GET['end']) if request.GET.has_key('end') else constants.RESULTS_PAGESIZE
    res = results.search(form.cleaned_data['q'], request.user.username, book_id, start=start, language=form.cleaned_data['language'])
    if len(res) == 0:
        return direct_to_template(request, 'results.html', { 'term': form.cleaned_data['q'] } )        

    total_results = res[0].total_results
    page_size = res[0].page_size

    if page_size < end - start:
        end = start + page_size
    next_end = end + constants.RESULTS_PAGESIZE

    show_previous = True if start != 1 else False
    show_next = True if end < total_results else False
    
    next_start = start + constants.RESULTS_PAGESIZE

    previous_start = start - constants.RESULTS_PAGESIZE
    previous_end = previous_start + constants.RESULTS_PAGESIZE

    return direct_to_template(request, 'results.html', 
                              { 'results':res,
                                'language':request.GET['language'],
                                'start':start,
                                'end': end,
                                'total_results': total_results,
                                'multiple_pages': True if show_next or show_previous else False,
                                'next_start': next_start,
                                'next_end' : next_end,
                                'previous_start': previous_start,
                                'previous_end' : previous_end,
                                'end': end,
                                'show_next': show_next,
                                'show_previous': show_previous,
                                'page_size':page_size,
                                'term':form.cleaned_data['q']})

@login_required
def index(request, book_id=None):
    '''Forceably index a user's books.  The user can only index
    their own books; this will generally be used for testing only.'''
    num_indexed = epubindexer.index_user_library(request.user)
    return HttpResponse("Indexed %d documents" % num_indexed)
