import os, logging, os.path, shutil
from lxml.html import soupparser
from lxml import etree
import xapian

from django.core.management import setup_environ
import bookworm.settings
from django.core.urlresolvers import reverse

from django.utils.http import urlquote_plus

import bookworm.search.constants as constants
from bookworm.search import indexer

setup_environ(bookworm.settings)

log = logging.getLogger('search.results')

def search(term, username, book_id=None, start=1, end=constants.RESULTS_PAGESIZE, sort=constants.SORT_RELEVANCE, language='en'):

    database = indexer.get_database(username, book_id)

    # Start an enquire session.
    enquire = xapian.Enquire(database)

    # Parse the query string to produce a Xapian::Query object.
    qp = xapian.QueryParser()
    qp.set_database(database)
    qp.set_default_op(xapian.Query.OP_AND)
    terms = [t.term for t in database.allterms()]
    if len(terms) == 0:
        log.warn("NO TERMS found in database %s/%s" % (username,  book_id))
    #log.debug([t.term for t in database.allterms()])
    log.debug("Using language %s" % language)
    qp.set_stemmer(indexer.get_stemmer(language))
    qp.set_stemming_strategy(xapian.QueryParser.STEM_SOME)
    query = qp.parse_query(term)
    #log.debug("Parsed query is: %s" % query.get_description())

    enquire.set_query(query)

    set_start = 0 if start == 1 else start

    if sort == constants.SORT_ORDINAL:
        enquire.set_sort_by_value(constants.SEARCH_ORDINAL, False)

    matches = enquire.get_mset(set_start, end, 101)

    # Display the results.
    page_size = matches.size()
    total_results = matches.get_matches_estimated()
    results = [Result(match.docid, match.document, term, total_results, page_size) for match in matches]
    for r in results:
        words = []
        terms = set(enquire.matching_terms(r.xapian_id))
        for word in r.xapian_document.get_data().split(" "):
            term = word.replace('?', '').replace('"', '').replace('.', '').replace(',', '').replace('-', ' ')
            term = term.lower()
            stemmer = indexer.get_stemmer(r.language)
            if "Z%s" % stemmer(term) in terms or term in terms:
                word = '<%s class="%s">%s</span>' % (constants.RESULT_ELEMENT, constants.RESULT_ELEMENT_CLASS, word)
            words.append(word)
        
        r.set_content(' '.join(words))
    return results


class Result(object):
    highlighted_content = None
    def __init__(self, xapian_id, xapian_document, term, total_results, page_size):
        self.xapian_id = xapian_id
        self.xapian_document = xapian_document
        self.term = term
        self.parsed_content = None
        self.highlighted_content = None
        self.total_results = total_results
        self.page_size = page_size

    @property
    def id(self):
        return int(self.xapian_document.get_value(constants.SEARCH_BOOK_ID))

    @property
    def title(self):
        return self.xapian_document.get_value(constants.SEARCH_BOOK_TITLE)

    @property
    def chapter_id(self):
        return self.xapian_document.get_value(constants.SEARCH_CHAPTER_ID)

    @property
    def chapter_title(self):
        return self.xapian_document.get_value(constants.SEARCH_CHAPTER_TITLE)

    @property
    def chapter_filename(self):
        return self.xapian_document.get_value(constants.SEARCH_CHAPTER_FILENAME)

    @property
    def author(self):
        return self.xapian_document.get_value(constants.SEARCH_AUTHOR_NAME)

    @property
    def language(self):
        return self.xapian_document.get_value(constants.SEARCH_LANGUAGE_VALUE)

    @property
    def namespace(self):
        ns = self.xapian_document.get_value(constants.SEARCH_NAMESPACE)
        if ns:
            ns = '{%s}' % ns
        return ns

    @property
    def url(self):
        # It would be nice if this didn't violate DRY by invoking EpubArchive's 
        # get_absolute_url
        return reverse('view_chapter', args=[urlquote_plus(self.title), str(self.id), str(self.chapter_filename)])

    def set_content(self, content):
        self.highlighted_content = content
        self.parsed_content = soupparser.fromstring(content)

    @property
    def result_fragment(self):
        match_expression = self.parsed_content.xpath("(//%s%s[@class='%s'])[1]" % (self.namespace, constants.RESULT_ELEMENT, constants.RESULT_ELEMENT_CLASS))
        if len(match_expression) == 0:
            # We didn't find a match; for now don't show captioning
            # fixme later to improve term matching
            return None
        match = match_expression[0]
        out = []
        text_preceding = match.xpath('preceding::text()[1]')
        if len(text_preceding) > 0:
            preceding = text_preceding[0].split(' ')
            preceding.reverse()
            length = constants.RESULT_WORD_BREAKS if len(preceding) > constants.RESULT_WORD_BREAKS else len(preceding)
            temp = []
            for word in preceding[0:length]:
                temp.append(word)
            temp.reverse()
            for word in temp:
                out.append(word)
        out.append('<%s class="%s">%s</span>' % (constants.RESULT_ELEMENT,
                                                 constants.RESULT_ELEMENT_CLASS,
                                                 match.text))

        text_following = match.xpath('following::text()[1]')
        if len(text_following) > 0:
            following = text_following[0].split(' ')
            length = constants.RESULT_WORD_BREAKS if len(following) > constants.RESULT_WORD_BREAKS else len(following)
            for word in following[0:length]:
                out.append(word)
        return ' '.join(out)



