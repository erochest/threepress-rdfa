#!/usr/bin/env python
# encoding: utf-8

import os
import re
import sys
import time
import unittest
import logging

from os.path import isfile, isdir

sys.path.append('/usr/local/google_appengine')
sys.path.append('/usr/local/google_appengine/lib/yaml/lib')

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub
from google.appengine.api import mail_stub
from google.appengine.api import urlfetch_stub
from google.appengine.api import user_service_stub
from google.appengine.api import users

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Could we get this with the relative imports in 2.5 __future__?
# Tried this but relative imports do not work in 2.5 if the script is run as '__main__' -ld 
dir_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))
sys.path.append(dir_path)

from library.models import *
import library.views as views
from library.epub.toc import TOC
from library.epub.constants import *

APP_ID = u'test'
AUTH_DOMAIN = 'gmail.com'
LOGGED_IN_USER = 'test@example.com'

# Data for public epub documents
DATA_DIR = os.path.abspath('./data')

# Local documents should be added here and will be included in tests,
# but not in the svn repository
PRIVATE_DATA_DIR = '%s/private' % DATA_DIR

class TestModels(unittest.TestCase):

    def setUp(self):
        # Ensure we're in UTC.
        os.environ['TZ'] = 'UTC'
        time.tzset()
        
        # Start with a fresh api proxy.
        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
        
        # Use a fresh stub datastore.
        stub = datastore_file_stub.DatastoreFileStub(APP_ID, '/dev/null', '/dev/null')
        apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)

        # Use a fresh stub UserService.
        apiproxy_stub_map.apiproxy.RegisterStub(
            'user', user_service_stub.UserServiceStub())
        os.environ['AUTH_DOMAIN'] = AUTH_DOMAIN
        os.environ['USER_EMAIL'] = LOGGED_IN_USER
        
        # Use a fresh urlfetch stub.
        apiproxy_stub_map.apiproxy.RegisterStub(
            'urlfetch', urlfetch_stub.URLFetchServiceStub())
        
        # Use a fresh mail stub.
        apiproxy_stub_map.apiproxy.RegisterStub('mail', mail_stub.MailServiceStub())

        # Add all our test data
        self.documents = [d for d in os.listdir(DATA_DIR) if '.epub' in d and isfile('%s/%s' % (DATA_DIR, d))]

        if isdir(PRIVATE_DATA_DIR):
            self.documents += [d for d in os.listdir(PRIVATE_DATA_DIR) if '.epub' in d and isfile('%s/%s' % (PRIVATE_DATA_DIR, d))] 
        


    def testGetAllDocuments(self):
        '''Run through all the documents at a high level'''
        for d in self.documents:
            if d.startswith("invalid"):
                # Test bad documents here?
                pass
            else:
                doc = self.create_document(d)
                doc.explode()

    def testGetTitle(self):
        '''Did we get back the correct title?'''
        title = u'Pride and Prejudice'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        self.assertEquals(title, document.title)

    def testSingleAuthor(self):
        '''Did we get a single author from our author() method?'''
        author = u'Jane Austen'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        self.assertEquals(author, document.author())        

    def testGetMultipleAuthors(self):
        '''Do we return the correct number of authors in the correct order?'''
        expected_authors = [u'First Author', u'Second Author']
        opf_file = 'two-authors.opf'
        document = MockEpubArchive(name=opf_file)
        opf = document.xml_from_string(open('%s/%s' % (DATA_DIR, opf_file)).read())
        authors = document.get_authors(opf)
        self.assertEquals(expected_authors, authors)

    def testGetMultipleAuthorsAsAuthor(self):
        '''Multiple authors should be displayable in a short space.'''
        opf_file = 'two-authors.opf'
        expected_authors = [u'First Author', u'Second Author']
        document = MockEpubArchive(name=opf_file)
        opf = document.xml_from_string(open('%s/%s' % (DATA_DIR, opf_file)).read())
        
        fuzz = 4
        len_first_author = len(expected_authors[0])
        len_short_author_str = len(document.get_author(opf))
        difference = len_short_author_str - len_first_author
        self.assert_(difference < fuzz)

    def testNoAuthor(self):
        '''An OPF document with no authors should return None.'''
        no_author_opf_file = 'no-author.opf'
        no_author_document = MockEpubArchive(name=no_author_opf_file)
        opf = no_author_document.xml_from_string(open('%s/%s' % (DATA_DIR, no_author_opf_file)).read())

        author = no_author_document.get_author(opf)
        self.failIf(author)

    def testCreateDocument(self):
        '''Assert that we created a non-None document.'''
        d = self.create_document(self.documents[0])
        self.assert_(d)

    def testFindDocument(self):
        """Documents should be findable by title and author."""
        author = u'Jane Austen'
        title = u'Pride and Prejudice'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.put()
        logging.info(users.get_current_user())
        key = document.key()
        d = _get_document(title, key)
        self.failUnless(d)

    def testBadEpubFails(self):
        """ePub documents with missing compontent should raise errors."""
        filename = 'invalid_no_container.epub'
        document = self.create_document(filename)
        self.assertRaises(InvalidEpubException, document.explode)

    def testSafeName(self):
        """Names should be safely quoted for URLs."""
        name = u'John Q., CommasAreForbidden'
        sn = safe_name(name)
        comma_re = re.compile(",")
        result = comma_re.match(sn)
        self.failIf(result)

    def testCountTOC(self):
        '''Check that in a simple document, the number of chapter items equals the number of top-level nav items'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.put()

        toc = TOC(document.toc)
        self.failUnless(toc)

        chapters = HTMLFile.gql('WHERE archive = :parent',
                                parent=document).fetch(100)
        self.assertEquals(len(chapters), len(toc.find_points(1)))

    def testCountDeepTOC(self):
        '''Check a complex document with multiple nesting levels'''
        toc = TOC(open('%s/complex-ncx.ncx' % DATA_DIR).read())
        self.failUnless(toc)
        self.assert_(len(toc.find_points(3)) > len(toc.find_points(2)) > len(toc.find_points(1)))

    def testOrderedTOC(self):
        '''TOC should preserve the playorder of the NCX'''
        toc = TOC(open('%s/complex-ncx.ncx' % DATA_DIR).read())
        self.failUnless(toc)
        # First item is the Copyright statement, which has no children
        copyright_statement = toc.tree[0]
        self.assertEquals(copyright_statement.title(), 'Copyright')

        # Second item should be the preface 
        preface = toc.tree[1]
        self.assertEquals(preface.title(), 'Preface')        

        # Last item is the Colophon
        colophon = toc.tree[-1:][0]
        self.assertEquals(colophon.title(), 'Colophon')

    def testGetChildren(self):
        '''Get the children of a particular nested TOC node, by node'''
        toc = TOC(open('%s/complex-ncx.ncx' % DATA_DIR).read())
        self.failUnless(toc)

        # First item is the Copyright statement, which has no children
        copyright_section = toc.tree[0]
        children = toc.find_children(copyright_section)
        self.failIf(children)

        # Second item is the Preface, which has 8 children
        preface = toc.tree[1]
        children = toc.find_children(preface)
        self.assertEquals(8, len(children))

    def testTOCHref(self):
        '''Ensure that we are returning the correct href for an item'''
        toc = TOC(open('%s/complex-ncx.ncx' % DATA_DIR).read())
        preface = toc.tree[1]
        self.assertEquals("pr02.html", preface.href())

    def testMetadata(self):
        opf_file = 'all-metadata.opf'
        document = MockEpubArchive(name=opf_file)
        opf = open('%s/%s' % (DATA_DIR, opf_file)).read()

        self.assertEquals('en-US', document.get_metadata(DC_LANGUAGE_TAG, opf))
        self.assertEquals('Public Domain', document.get_metadata(DC_RIGHTS_TAG, opf))
        self.assertEquals('threepress.org', document.get_metadata(DC_PUBLISHER_TAG, opf))
        self.assertEquals(3, len(document.get_metadata(DC_SUBJECT_TAG, opf)))
        self.assertEquals('Subject 1', document.get_metadata(DC_SUBJECT_TAG, opf)[0])
        self.assertEquals('Subject 2', document.get_metadata(DC_SUBJECT_TAG, opf)[1])
        self.assertEquals('Subject 3', document.get_metadata(DC_SUBJECT_TAG, opf)[2])

    def create_document(self, document):
        epub = MockEpubArchive(name=document)
        try:
            epub.content = open('%s/%s' % (DATA_DIR, document)).read()
        except IOError:
            epub.content = open('%s/%s' % (PRIVATE_DATA_DIR, document)).read()        
        epub.owner = users.get_current_user()
        epub.put()
        return epub


def _get_document(title, key):
    '''@todo Mock this out better instead of overwriting the real view'''
    return MockEpubArchive.get(key)


class MockEpubArchive(EpubArchive): 
    '''Mock object to expose some protected methods for testing purposes.'''

    def xml_from_string(self, string):
        return self._xml_from_string(string)

    def get_author(self, opf):
        self.authors = self._get_authors(opf)
        return self.author()

    def get_authors(self, opf):
        return self._get_authors(opf)

    def get_metadata(self, tag, opf):
        return self._get_metadata(tag, opf)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main() 
