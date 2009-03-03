from lxml import etree
import logging, urllib2

from django.conf import settings

from bookworm.library.epub import constants

API = 'http://www.librarything.com/api'
COVERS_API = 'http://covers.librarything.com/devkey/%s/medium/isbn' % settings.LIBRARYTHING_KEY
LINK_API = 'http://www.librarything.com/isbn'
REST_API = 'http://www.librarything.com/services/rest/1.0/?method=librarything.ck.getwork&apikey=%s' % settings.LIBRARYTHING_KEY

LT_NS = 'http://www.librarything.com/'

ALTERNATIVE_WORKS = 'thingISBN'
TITLE_TO_ISBN = 'thingTitle'
ISBN_TO_LANG = 'thingLang'
MAX_RESULTS = 10



log = logging.getLogger('librarything.init')

def get_isbns(document):
    '''Get a candidate list of IBSNs for a document, either from itself, or from a LibraryThing query.
    Returns a tuple of zero, one or more isbns.'''
    if document.identifier_type() == constants.IDENTIFIER_ISBN:
        return (document.get_identifier(), )
    
    # Try getting it from LibraryThing
    request = urllib2.Request('%s/%s/%s' % (API, TITLE_TO_ISBN, document.safe_title()))
    log.debug("Requesting %s" % request)
    try:
        response = urllib2.urlopen(request)
    except urllib2.URLError, e:
        log.error('Got URL error from response: %s for \n%s' % (e, response))       
        return []
    try:
        results = etree.fromstring(response.read())
    except etree.XMLSyntaxError, e:
        log.error('Got syntax error from response: %s for \n%s' % (e, response))
        return []
    return [ LibraryThingWork(i.text) for i in results.xpath('//isbn')][:20]

class LibraryThingWork(object):
    def __init__(self, isbn):
        self.isbn=isbn
        self.cached_info = None
        self.cached_img = None

    @property
    def img(self):
        if self.cached_img:
            return self.cached_img
        self.cached_img = "%s/%s" % (COVERS_API, self.isbn)
        return self.cached_img

    @property
    def info(self):
        '''Return the LibraryThing Common Knowledge info for this work'''
        if self.cached_info is not None:
            return self.cached_info
        request = urllib2.Request('%s&isbn=%s' % (REST_API, self.isbn))
        response = urllib2.urlopen(request).read()
        try:
            results = etree.fromstring(response)
        except etree.XMLSyntaxError, e:
            log.error('Got syntax error from response: %s for \n%s' % (e, response))
            results = etree.fromstring('<resp/>')
        self.cached_info = results
        return self.cached_info

    @property
    def quotations(self):
        return self._fields('quotations')

    @property
    def first_words(self):
        '''The first words from this work'''
        return self._field('firstwords')

    @property
    def originalpublicationdate(self):
        return self._field('originalpublicationdate')

    @property
    def canonical_title(self):
        return self._field('canonicaltitle')
    
    @property
    def character_names(self):
        return self._fields('characternames')[:10]

    def _fields(self, fieldname):
        '''Return multiple items with fact names'''
        info = self.info
        facts = info.xpath('//lt:field[@name="%s"]//lt:fact' % fieldname, namespaces={'lt':LT_NS})
        facts = [f.text.replace('<![CDATA[ ', '').replace(']]>', '') for f in facts]
        return facts

    def _field(self, fieldname):
        '''Return a field with a single fact'''
        info = self.info
        t = info.xpath('//lt:field[@name="%s"]//lt:fact' % fieldname, namespaces={'lt':LT_NS})
        if not t or len(t) == 0:
            return None
        t = t[0].text
        # Remove when LibraryThing fixes this
        t = t.replace('<![CDATA[ ', '')
        t = t.replace(']]>', '')
        return t
        
