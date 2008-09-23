import os.path, re, subprocess, sys, logging, urllib, StringIO
sys.path.append('/home/liza/threepress')

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.conf import settings
from lxml import etree

import xapian

from models import Document, Result, EpubDocument, EpubChapter
from forms import EpubValidateForm
import epubcheck

static_dir = None

def _get_static_dir():
    global static_dir 
    if static_dir:
        logging.info("Returning cached")
        return static_dir
    for d in settings.TEMPLATE_DIRS:
        logging.info("Setting static variable")
        if os.path.exists('%s/static' % d):
            static_dir = '%s/static' % d
            return static_dir
    

def epub_validate(request):
    if request.method == 'POST':
        form = EpubValidateForm(request.POST, request.FILES)
        if form.is_valid():

            data = StringIO.StringIO()
            for c in request.FILES['epub'].chunks():
                data.write(c)
            document_name = form.cleaned_data['epub'].name
            
            validator = epubcheck.validate(document_name, data.getvalue())

            # Strip the filename info from errors
            errors = validator.clean_errors()
            output = validator.output
            return render_to_response('documents/validate.html', 
                                      {'form':form, 
                                       'document':document_name,
                                       'output':output, 
                                       'errors':errors})


                
    else:
        form = EpubValidateForm()
    output = None; errors = None; document = None
     
    return render_to_response('documents/validate.html', {'form':form, 'output':output, 'errors':errors,'document':document})
    

def document_chapter_epub(request, document_id, chapter_id):
    return document_epub(request, document_id, chapter_id)

def document_epub(request, document_id, chapter_id='1'):
    '''Here we do not load a document from the database, but instead 
    render the epub file from the file system.'''
    d = _get_static_dir()
    logging.info("Got document_id as %s" % document_id)

    epub_dir = "%s/epubx/%s" % (d, document_id)
    container = etree.parse("%s/META-INF/container.xml" % epub_dir)
    opf_filename = container.xpath('//opf:rootfile/@full-path', namespaces={'opf':'urn:oasis:names:tc:opendocument:xmlns:container'})[0]
    logging.debug("Got OPF filename as %s" % opf_filename)
    opf = etree.parse("%s/%s" % (epub_dir, opf_filename))
    
    title = opf.xpath('//dc:title/text()', namespaces={'dc':'http://purl.org/dc/elements/1.1/'})[0]
    author = opf.xpath('//dc:creator/text()', namespaces={'dc':'http://purl.org/dc/elements/1.1/'})[0]
    epub = EpubDocument(document_id, title, author)

    ncx_filename = opf.xpath('//opf:item[@id="ncx"]/@href', namespaces={'opf':'http://www.idpf.org/2007/opf'})[0]
    logging.debug("Got NCX filename as %s" % ncx_filename)
    ncx = etree.parse("%s/OEBPS/%s" % (epub_dir, ncx_filename))

    chapter = None
    p = re.compile("(\d+)")
    ordinal = 1

    if ncx:
        for item in ncx.xpath('//ncx:navPoint', 
                              namespaces={'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}):        
            c_href = item.xpath('ncx:content/@src', 
                                namespaces={'ncx': 'http://www.daisy.org/z3986/2005/ncx/'})[0]
            c_id = item.xpath('@id')[0]
            m = p.search(c_id)
            c_numeric_id = m.group(1) if m else None
            c_title = item.xpath('ncx:navLabel/ncx:text/text()', 
                                namespaces={'ncx': 'http://www.daisy.org/z3986/2005/ncx/'})[0]
            c = EpubChapter(c_numeric_id, epub, c_title, None)
            c.ordinal = ordinal
            if c_numeric_id == chapter_id:
                chapter = c
                chapter.content = open("%s/OEBPS/chapter-%s.html" % (epub_dir, chapter_id)).read()
            epub.chapters.append(c)
            ordinal += 1         

    # If we don't have an NCX file then we'll have to read the titles of each 
    # chapter out of the XHTML, by parsing the contents of the OPF file            
    if not ncx:

        for item in opf.xpath('//opf:item[@media-type="application/xhtml+xml"]', 
                              namespaces={'opf':'http://www.idpf.org/2007/opf'}):
            c_href = item.xpath('@href')[0]
            c_id = item.xpath('@href')[0]
            m = p.search(c_id)
            c_numeric_id = m.group(1) if m else None
            c_content = etree.parse('%s/OEBPS/%s' % (epub_dir, c_href))
            c_title = c_content.xpath('//html:title/text()', namespaces={'html':'http://www.w3.org/1999/xhtml'})[0]
            c = EpubChapter(c_numeric_id, epub, c_title, None)
            c.ordinal = ordinal
            if c_numeric_id == chapter_id:
                chapter = c
                chapter.content = open("%s/OEBPS/chapter-%s.html" % (epub_dir, chapter_id)).read()
            epub.chapters.append(c)
            ordinal += 1

    return render_to_response('documents/epubx.html',
                              {'document':epub, 
                               'chapter':chapter})


def document_chapter_view(request, document_id, chapter_id):
    return document_view(request, document_id, chapter_id)

def document_view(request, document_id, chapter_id=None):
    document = get_object_or_404(Document, pk=document_id)
    chapter = None
    next = None
    previous = None
    chapter_preview = None
    show_pdf = False
    for d in settings.TEMPLATE_DIRS:
        if os.path.exists('%s/static/pdf/%s.pdf' % (d, document_id)):
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

def index(request):
    documents = get_list_or_404(Document)
    return render_to_response('index.html', {'documents':documents})

def search(request, document_id=None):
    if document_id:
        document = get_object_or_404(Document, pk=document_id)
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
        database = xapian.Database('%s/%s' % (settings.DB_DIR, document_id))
    else:
        database = xapian.Database('%s/%s' % (settings.DB_DIR, 'threepress'))

    #document = Document.objects.get(id=document_id)

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

