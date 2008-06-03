from google.appengine.ext import db
from google.appengine.api import users

from xml.etree import ElementTree
from zipfile import ZipFile
from StringIO import StringIO
import logging

import settings

class EpubArchive(db.Model):
    _CONTAINER = 'META-INF/container.xml'
    _OEBPS = 'OEBPS'
    _NSMAP = { 'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
               'opf': 'http://www.idpf.org/2007/opf',
               'dc':'http://purl.org/dc/elements/1.1/'}

    name = db.StringProperty(required=True)
    title = db.StringProperty()
    author = db.StringProperty()
    content = db.BlobProperty()
    toc = db.TextProperty()
    opf = db.TextProperty()
    container = db.TextProperty()
    
    def explode(self):
        '''Explodes an epub archive'''
        e = StringIO(self.content)
        z = ZipFile(e)
        logging.info(z.namelist())
        self.container = z.read(self._CONTAINER)
        self.opf = z.read(self._get_opf())
        
        parsed_opf = ElementTree.fromstring(self.opf)
        self.toc = z.read(self._get_toc(parsed_opf))
        self.author = self._get_author(parsed_opf)
        self.title = self._get_title(parsed_opf)

    def _get_opf(self):
        '''Parse the container to get the name of the opf file'''
        xml = ElementTree.fromstring(self.container)
        opf_filename = xml.find('.//{%s}rootfile' % self._NSMAP['container']).get('full-path')
        logging.info("Got opf filename as %s" % opf_filename)
        return opf_filename

    def _get_toc(self, xml):
        '''Parse the opf file to get the name of the TOC'''
        items = xml.findall('.//{%s}item' % self._NSMAP['opf'])
        for item in items:
            if item.get('id') == 'ncx':
                toc_filename = item.get('href')
                logging.info('Got toc filename as %s' % toc_filename)
                return "%s/%s" % (self._OEBPS, toc_filename)

    def _get_author(self, xml):
        author = xml.findtext('.//{%s}creator' % self._NSMAP['dc'])
        logging.info('Got author as %s' % author)
        return author

    def _get_title(self, xml):
        title = xml.findtext('.//{%s}title' % self._NSMAP['dc'])
        logging.info('Got title as %s' % title)
        return title
    


class HTMLFile(db.Model):
    file = db.TextProperty()
    archive = db.ReferenceProperty(EpubArchive)
    


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


