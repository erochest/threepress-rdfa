from google.appengine.ext import db
from google.appengine.api import users

from xml.etree import ElementTree
from zipfile import ZipFile
from StringIO import StringIO
import logging
from urllib import quote_plus, unquote_plus

import settings
# Functions
def safe_name(name):
    return quote_plus(name)

def unsafe_name(name):
    return unquote_plus(name)

class EpubArchive(db.Model):
    _CONTAINER = 'META-INF/container.xml'
    _NSMAP = { 'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
               'opf': 'http://www.idpf.org/2007/opf',
               'dc':'http://purl.org/dc/elements/1.1/',
               'ncx':'http://www.daisy.org/z3986/2005/ncx/'}

    _content_path = 'OEBPS' # Default
    _archive = ''

    name = db.StringProperty(required=True)
    title = db.StringProperty()
    author = db.StringProperty()
    content = db.BlobProperty()
    toc = db.TextProperty()
    opf = db.TextProperty()
    container = db.TextProperty()
    owner = db.UserProperty()

    def explode(self):
        '''Explodes an epub archive'''
        e = StringIO(self.content)
        z = ZipFile(e)
        self._archive = z
        logging.info(z.namelist())
        self.container = z.read(self._CONTAINER)
        self.opf = z.read(self._get_opf())

        parsed_opf = ElementTree.fromstring(self.opf)

        self.toc = unicode(z.read(self._get_toc(parsed_opf)), 'utf-8')

        parsed_toc = ElementTree.fromstring(self.toc.encode('utf-8'))

        self.author = self._get_author(parsed_opf)
        self.title = self._get_title(parsed_opf)

        self._get_content(parsed_opf, parsed_toc)

    def _get_opf(self):
        '''Parse the container to get the name of the opf file'''
        xml = ElementTree.fromstring(self.container)
        opf_filename = xml.find('.//{%s}rootfile' % self._NSMAP['container']).get('full-path')
        path = opf_filename.split('/')[0] # fixme, use basename
        self._content_path = path
        logging.info("Got opf filename as %s" % opf_filename)
        return opf_filename
 
    def _get_toc(self, xml):
        '''Parse the opf file to get the name of the TOC'''
        items = xml.findall('.//{%s}item' % self._NSMAP['opf'])
        for item in items:
            if item.get('id') == 'ncx':
                toc_filename = item.get('href').strip()
                logging.info('Got toc filename as %s' % toc_filename)
                return "%s/%s" % (self._content_path, toc_filename)

    def _get_author(self, xml):
        author = xml.findtext('.//{%s}creator' % self._NSMAP['dc']).strip()
        logging.info('Got author as %s' % author)
        return author

    def _get_title(self, xml):
        title = xml.findtext('.//{%s}title' % self._NSMAP['dc']).strip()
        logging.info('Got title as %s' % title)
        return title
    
    def _get_content(self, opf, toc):
        # Get all the item references from the <spine>
        refs = opf.findall('.//{%s}spine/{%s}itemref' % (self._NSMAP['opf'], self._NSMAP['opf']) )
        navs = toc.findall('.//{%s}navPoint' % (self._NSMAP['ncx']))
        navMap = {}
        itemMap = {}

        items = opf.findall(".//{%s}item" % (self._NSMAP['opf']))
        for item in items:
            itemMap[item.get('id')] = item.get('href')

        for nav in navs:
            order = int(nav.get('playOrder')) 
            title = nav.findtext('.//{%s}text' % (self._NSMAP['ncx']))
            href = nav.find('.//{%s}content' % (self._NSMAP['ncx'])).get('src')
            filename = href.split('#')[0]
            logging.info('adding filename %s to navmap' % filename)
            navMap[filename] = NavPoint(title, href, order)
        
        for ref in refs:
            idref = ref.get('idref')
            if itemMap.has_key(idref):
                href = itemMap[idref]
                logging.info("checking href %s" % href)
                if navMap.has_key(href):
                    logging.info('Adding navmap item %s' % navMap[href])
                    filename = '%s/%s' % (self._content_path, href)
                    content = self._archive.read(filename)
                    html = HTMLFile(title=navMap[href].title,
                                    idref=idref,
                                    file=unicode(content, 'utf-8'),
                                    archive=self,
                                    order=navMap[href].order)
                    html.put()


    def safe_title(self):
        return safe_name(self.title)  
    def safe_author(self):
        return safe_name(self.author)


class NavPoint():
    def __init__(self, title, href, order):
        self.title = title
        self.href = href
        self.order = order
    def __repr__(self):
        return "%s (%s) %d" % (self.title, self.href, self.order)

class HTMLFile(db.Model):
    idref = db.StringProperty()
    title = db.StringProperty()
    file = db.TextProperty()
    archive = db.ReferenceProperty(EpubArchive)
    order = db.IntegerProperty()

    def render(self):
        return self.file

class AbstractDocument(db.Model):
    '''An AbstractDocument could be either from our database or from
    an epub source'''
    def __init__(self, id, title, author):
        self.id = id
        self.title = title
        self.author = author

    def get_absolute_url(self):
        '''Implement in subclasses'''
        pass

    def link(self, text=None):
        if not text:
            text = self.title
        return '<a href="%s">%s</a>' % (self.get_absolute_url(), self.title)

    def chapter_list(self):
        '''The implementation here will be different for each model type'''
        pass

    def part_list(self):
        '''The implementation here will be different for each model type'''
        pass

class AbstractChapter(db.Model):
    '''A Chapter in an AbstractDocument'''
    ordinal = 0

    def __init__(self, id, document, title, content):
        self.document = document 
        self.id = id
        self.title = title
        self.content = content

    def render(self):
        return self.content

    def get_absolute_url(self):
        '''Implement in subclasses'''
        pass

    def link(self, text=None):
        if not text:
            text = self.title
        return '<a href="%s">%s</a>' % (self.get_absolute_url(), self.title)

class EpubDocument(AbstractDocument):
    '''A document derived out of an epub package'''
    chapters = []
    
    def __init__(self, id, document, title, content, stylesheet=None):
        self.stylesheet = stylesheet
        AbstractDocument.__init__(self, id, document, title, content)

    def get_absolute_url(self):
        return ('threepress.search.views.document_epub', [self.id])

    def chapter_list(self):
        return self.chapters


class EpubChapter(AbstractChapter):
    '''A chapter of content from an epub package'''

    def get_absolute_url(self):
        return ('threepress.search.views.document_chapter_epub', [self.document.id, self.id])


