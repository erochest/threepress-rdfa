import sys, os, time
from os.path import isfile, isdir
sys.path.append('/usr/local/google_appengine')
sys.path.append('/usr/local/google_appengine/lib/yaml/lib')

import unittest
from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub
from google.appengine.api import mail_stub
from google.appengine.api import urlfetch_stub
from google.appengine.api import user_service_stub
from google.appengine.ext import db, search 
from google.appengine.api import users

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from models import *
import views


logging.basicConfig(level=logging.INFO)


APP_ID = u'test'
AUTH_DOMAIN = 'gmail.com'
LOGGED_IN_USER = 'test@example.com'

# Data for public epub documents
DATA_DIR = 'tests/data'

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
       
    def testTest(self):
        b = HTMLFile(idref='test')
        b.put()

        a = HTMLFile.gql('WHERE idref = :title',
                         title='test').get()
        self.assertEquals(a.idref, 'test')


    def testGetAllDocuments(self):
        '''Run through all the documents at a high level'''
        for d in self.documents:
            doc = self.create_document(d)
            doc.explode()

    def testGetTitle(self):
        '''Did we get back the correct title?'''
        title = u'Pride and Prejudice'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        self.assertEquals(title, document.title)

    def testGetSingleAuthor(self):
        '''Did we get a single author from our author() method?'''
        author = u'Jane Austen'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        self.assertEquals(author, document.author())        

    def testGetMultipleAuthors(self):
        '''Do we return the correct number of authors in the correct order?'''
        test_authors = [u'First Author', u'Second Author']
        opf_file = 'two-authors.opf'
        document = MockEpubArchive(name=opf_file)
        opf = document.xml_from_string(open('%s/%s' % (DATA_DIR, opf_file)).read())
        authors = document.get_authors(opf)
        self.assertEquals(authors, test_authors)

    def testCreateDocument(self):
        '''Assert that we created a non-None document'''
        d = self.create_document(self.documents[0])
        self.assert_(d)

    def testFindDocument(self):
        author = u'Jane Austen'
        title = u'Pride and Prejudice'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.put()
        logging.info(users.get_current_user())
        d = _get_document(title, author)
        self.assert_(d)

    def create_document(self, document):
        epub = MockEpubArchive(name=document)
        try:
            epub.content = open('%s/%s' % (DATA_DIR, document)).read()
        except IOError:
            epub.content = open('%s/%s' % (PRIVATE_DATA_DIR, document)).read()        
        epub.owner = users.get_current_user()
        epub.put()
        return epub

def _get_document(title, author):
    '''@todo Mock this out better instead of overwriting the real view'''
    return MockEpubArchive.gql('WHERE title = :title AND authors = :authors AND owner = :owner',
                               owner=users.get_current_user(),
                               title=unsafe_name(title), 
                               authors=unsafe_name(author),
                               ).get()
    


class MockEpubArchive(EpubArchive):
    '''Mock object to expose some protected methods for testing purposes.'''

    def xml_from_string(self, string):
        return self._xml_from_string(string)

    def get_authors(self, opf):
        return self._get_authors(opf)


if __name__ == '__main__':
    unittest.main() 
