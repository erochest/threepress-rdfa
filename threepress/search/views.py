# Create your views here.
import sys
sys.path.append('/home/liza/threepress')

from threepress.search.models import Document, Chapter, Part, Result
from django.http import *
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.core.exceptions import *
from django.newforms import *
from django.conf import settings
import os.path
import xapian

def document_chapter_view(request, id, chapter_id):
    return document_view(request, id, chapter_id)

def document_view(request, id, chapter_id=None):
    document = get_object_or_404(Document, pk=id)
    #show_spacing = True if request.GET.has_key('show_spacing') else False
    chapter = None
    next = None
    previous = None
    chapter_preview = None
    show_pdf = False
    for d in settings.TEMPLATE_DIRS:
        if os.path.exists('%s/static/pdf/%s.pdf' % (d, id)):
            show_pdf = True
            break
                              


    if chapter_id:
        chapter_query = document.chapter_set.filter(id=chapter_id)
        if chapter_query.count() == 0:
            raise Http404
        chapter = chapter_query[0]
        next_set = document.chapter_set.filter(ordinal=chapter.ordinal+1)
        previous_set = document.chapter_set.filter(ordinal=chapter.ordinal-1)
        if len(next_set) > 0:
            next = next_set[0]
        if len(previous_set) > 0:
            previous = previous_set[0]
    else:
        chapter_preview = document.chapter_set.all()[0]

    return render_to_response('documents/view.html', 
                              {'document':document, 
                               'chapter':chapter,
                               'chapter_preview':chapter_preview,
                               'next':next,
                               'previous':previous,
                               'show_pdf':show_pdf,
                               })

def page_view(request, page):
    try:
        page = Page.objects.get(name=page)
    except ObjectDoesNotExist:
        page_filename = "%s/%s.html" % ('/Users/liza/threepress/threepress/search/templates/pages', page)
        if os.path.exists(page_filename):
            content = open(page_filename).read()
            page = Page(content=content, name=page)
            #page.save()
        else:
            raise Http404
    return render_to_response('pages/view.html',
                              {'page':page})
def index(request):
    documents = get_list_or_404(Document)
    return render_to_response('index.html', {'documents':documents})

def search(request, doc_id=None):
    if doc_id:
        document = get_object_or_404(Document, pk=doc_id)
    else:
        document = None
    if not request.GET.has_key('search'):
        return HttpResponseRedirect('/')

    search_term = request.GET['search']
    start = int(request.GET['start']) if request.GET.has_key('start') else 1
    end = int(request.GET['end']) if request.GET.has_key('end') else settings.RESULTS_PAGESIZE
    
    sort = settings.SORT_ORDINAL if request.GET.has_key('sort') and request.GET['sort'] == 'appearance' else settings.SORT_RELEVANCE

    # Open the database for searching.
    if document:
        database = xapian.Database('%s/%s' % (settings.DB_DIR, doc_id))
    else:
        database = xapian.Database('%s/%s' % (settings.DB_DIR, 'threepress'))

    #document = Document.objects.get(id=doc_id)

    # Start an enquire session.
    enquire = xapian.Enquire(database)
    # Parse the query string to produce a Xapian::Query object.
    qp = xapian.QueryParser()
    stemmer = xapian.Stem("english")
    qp.set_stemmer(stemmer)
    qp.set_database(database)
    qp.set_stemming_strategy(xapian.QueryParser.STEM_SOME)
    query = qp.parse_query(search_term)
    stem = stemmer(search_term)
    print "Stem is : " + stem
    for t in qp.unstemlist("Z%s" % stem):
        print t

    print "Parsed query is: %s" % query.get_description()

    # Find the top 10 results for the query.
    enquire.set_query(query)
    
    if start == 1:
        set_start = 0
    else:
        set_start = start

    if sort == settings.SORT_ORDINAL:
        enquire.set_sort_by_value(settings.SEARCH_ORDINAL, False)

    matches = enquire.get_mset(set_start, end, 101)

    # Display the results.
    estimate = matches.get_matches_estimated()

    size = matches.size()
    if size < end - start:
        end = start + size
    next_end = end + settings.RESULTS_PAGESIZE

    show_previous = True if start != 1 else False
    show_next = True if end < estimate else False
    
    next_start = start + settings.RESULTS_PAGESIZE

    previous_start = start - settings.RESULTS_PAGESIZE
    previous_end = previous_start + settings.RESULTS_PAGESIZE

    results = [Result(match.docid, match.document) for match in matches]
    for r in results:
        words = []
        for word in r.xapian_document.get_data().split(" "):
            term = word.replace('?', '').replace('"', '').replace('.', '').replace(',', '')
            term = term.lower()
            for t in enquire.matching_terms(r.id):
                if "Z%s" % stemmer(term) == t or term == t:
                    word = '<span class="match">%s</span>' % word
            words.append(word)

        r.highlighted_content = ' '.join(words)
    return render_to_response('results.html', {'results': results, 
                                               'settings':settings,
                                               'estimate': estimate, 
                                               'document': document,
                                               'search': search_term,
                                               'sort': sort,
                                               'size': size,
                                               'multiple_pages': True if show_next or show_previous else False,
                                               'start': start,
                                               'next_start': next_start,
                                               'next_end' : next_end,
                                               'previous_start': previous_start,
                                               'previous_end' : previous_end,
                                               'end': end,
                                               'show_next': show_next,
                                               'show_previous': show_previous
                                               })

