# Represents a response from the Google Books API
from lxml import etree
import urllib2, logging

log = logging.getLogger('google_books.search')

ns = {'atom': 'http://www.w3.org/2005/Atom',
      'openSearch': 'http://a9.com/-/spec/opensearchrss/1.0/',
      'gbs' : 'http://schemas.google.com/books/2008',
      'dc' : 'http://purl.org/dc/terms',
      'gd' : 'http://schemas.google.com/g/2005' }


viewability = { 'FULL' : { 'description' : 'Full view of this work',
                           'value': 'http://schemas.google.com/books/2008#view_all_pages' },
                'PARTIAL' : { 'description' : 'Limited preview of this work',
                              'value': 'http://schemas.google.com/books/2008#view_partial' },
                'NONE': { 'description': 'Basic information only',
                             'value' : 'http://schemas.google.com/books/2008#view_no_pages' },
                'UNKNOWN': { 'description': '',
                             'value' : 'http://schemas.google.com/books/2008#view_unknown'}}

class Request(object):
    def __init__(self, query, remote_addr):
        r = urllib2.Request('http://books.google.com/books/feeds/volumes?%s' % query)
        if remote_addr:
            r.add_header('X-Forwarded-For', remote_addr)
            #r.add_header('X-Forwarded-For', '98.216.48.48')
        self.r = urllib2.urlopen(r)
    def get(self):
        return Response(self.r.read())

class Response(object):
    def __init__(self, resp):
        self.tree = etree.fromstring(resp)
        #log.debug(etree.tostring(self.tree, pretty_print=True))
        self.entries = [ Entry(e) for e in self.tree.xpath("//atom:entry",
                                                           namespaces=ns)]

class Entry(object):
    def __init__(self, xml):
        self.xml = xml

    @property
    def thumbnail(self):
        try:
            return self.xml.xpath("atom:link[@rel='http://schemas.google.com/books/2008/thumbnail']",
                                  namespaces=ns)[0].get('href')
        except IndexError:
            return None

    @property
    def description(self):
        try:
            return self.xml.xpath('dc:description/text()', namespaces=ns)[0]
        except IndexError:
            return None

    @property
    def viewability(self):
        try:
            desc = self.xml.xpath('gbs:viewability', namespaces=ns)[0].get('value')
        except IndexError:
            return None
        for v in viewability.keys():
            if viewability[v]['value'] == desc:
                return viewability[v]['description'] 
    
    @property
    def publisher(self):
        try:
            return self.xml.xpath('dc:publisher/text()', namespaces=ns)[0]
        except IndexError:
            return None

    @property
    def pages(self):
        try:
            return self.xml.xpath('dc:format/text()', namespaces=ns)[0]
        except IndexError:
            return None        

    @property
    def preview(self):
        try:
            return self.xml.xpath("atom:link[@rel='http://schemas.google.com/books/2008/preview']", namespaces=ns)[0].get('href')
        except IndexError:
            return None        

    @property
    def info(self):
        try:
            return self.xml.xpath("atom:link[@rel='http://schemas.google.com/books/2008/info']", namespaces=ns)[0].get('href')
        except IndexError:
            return None        


