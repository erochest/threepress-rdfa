import sys, os, time
from os.path import isfile
sys.path.append('/usr/local/google_appengine')
sys.path.append('/usr/local/google_appengine/lib/yaml/lib')

import unittest
from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub
from google.appengine.api import mail_stub
from google.appengine.api import urlfetch_stub
from google.appengine.api import user_service_stub
from google.appengine.ext import db, search 

from models import *

logging.basicConfig(level=logging.INFO)


APP_ID = u'test'
AUTH_DOMAIN = 'gmail.com'
LOGGED_IN_USER = 'test@example.com'

# Data for public epub documents
DATA_DIR = '/home/liza/threepress/bookworm-tests/data'

# Local documents should be added here and will be included in tests,
# but not in the svn repository
PRIVATE_DATA_DIR = '%s/private' % DATA_DIR

class TestSearch(unittest.TestCase):

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
       apiproxy_stub_map.apiproxy.RegisterStub(
         'mail', mail_stub.MailServiceStub())

       # Add all our test data
       self.documents = [d for d in os.listdir(DATA_DIR) if isfile('%s/%s' % (DATA_DIR, d))] + \
           [d for d in os.listdir(PRIVATE_DATA_DIR) if isfile('%s/%s' % (PRIVATE_DATA_DIR, d))] 
       
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

    def testGetOpf(self):
        title = 'Pride and Prejudice'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        self.assertEquals(title, document.title)
            
    def testCreateDocument(self):
        d = self.create_document(self.documents[0])
        self.assert_(d)


    def create_document(self, document):
        epub = EpubArchive(name=document)
        try:
            epub.content = open('%s/%s' % (DATA_DIR, document)).read()
        except IOError:
            epub.content = open('%s/%s' % (PRIVATE_DATA_DIR, document)).read()        

        epub.put()
        return epub


if __name__ == '__main__':
    unittest.main() 
