import logging
import os

import cssutils

cssutils.log.setLevel(logging.ERROR)

from lxml import etree

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http import HttpResponseNotFound
from django.conf import settings


# It's recommended that these settings be added to a local.py 
# for local testing:
# HOSTNAME = 'http://localhost:9002' (or whatever port you run the Django dev server on)
#
# Secure hostname
# SECURE_HOSTNAME = HOSTNAME


from bookworm.api import models
from bookworm.library import models as library_models
from bookworm.library import test_helper as helper

# Expected failure code for published endpoints
UNAUTHED_STATUS_CODE_PUBLISHED = 403

# Expected failure code for unpublished endpoints
UNAUTHED_STATUS_CODE_UNPUBLISHED = 404

# Expected status code for successful uploads
UPLOAD_STATUS_CODE = 201

# Expected failure code for unacceptable documents
UPLOAD_STATUS_CODE_UNACCEPTABLE = 406

EXTERNAL_EPUB_URL = 'http://www.threepress.org/static/epub/Sense-and-Sensibility_Jane-Austen.epub'

def reset_keys(fn):
    '''Delete any critical data between runs'''        
    def f(*args):
        [a.delete() for a in models.APIKey.objects.all() ]
        return fn(*args)
    return f

def reset_books(fn):
    '''Delete any critical data between runs'''        
    def f(*args):
        [ua.delete() for ua in library_models.UserArchive.objects.all() ]        
        [d.delete() for d in library_models.EpubArchive.objects.all() ]
        return fn(*args)
    return f


class Tests(TestCase):

    def setUp(self):
        # Set up users
        self.user = User.objects.create_user(username="testapi",email="testapi@example.com",password="testapi")
        self.user2 = User.objects.create_user(username="testapi2",email="testapi2@example.com",password="testapi2")
        self.userpref = library_models.UserPref.objects.create(user=self.user)
        self.userpref2 = library_models.UserPref.objects.create(user=self.user2)

        # Set up a Django site
        Site.objects.get_or_create(id=1)

        # Load the XHTML strict schema
        schema_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'schema', 'xhtml', 'xhtml-strict.rng')
        schema = etree.parse(schema_file)
        self.relaxng = etree.RelaxNG(schema)

    @reset_keys
    def test_generate_key(self):
        '''The system should be able to generate a random key'''
        k = models.APIKey.objects.create(user=self.user)
        assert k.key is not None
        # Does it seem vaguely uuid4-ish?
        assert len(k.key) == 32

    @reset_keys
    def test_generate_key_unique(self):
        '''Keys should be unique UUIDs'''
        k = models.APIKey.objects.create(user=self.user)
        k2 = models.APIKey.objects.create(user=self.user2)
        assert k.key != k2.key

    @reset_keys
    def test_generate_key_once(self):
        '''Keys should persist once created'''
        (k, created1) = models.APIKey.objects.get_or_create(user=self.user)
        assert created1
        (k2, created2) = models.APIKey.objects.get_or_create(user=self.user)
        assert not created2
        assert k.key == k2.key

    @reset_keys        
    def test_authenticate_key(self):
        '''It should be possible to test whether an API key is correct'''
        k = models.APIKey.objects.create(user=self.user)
        key = k.key
        assert k.is_valid(key)
        assert not k.is_valid('Not valid')

    @reset_keys        
    def test_authenticate_key_by_user(self):
        '''It should be possible to test whether an API key is correct for any named user'''
        k = models.APIKey.objects.create(user=self.user)
        k2 = models.APIKey.objects.create(user=self.user2)
        key = k.key
        assert key is not None

        assert models.APIKey.objects.is_valid(key, self.user)

        # It shouldn't be valid for user2
        assert not models.APIKey.objects.is_valid(key, self.user2)


        # It should also work if k2 doesn't have any key at all, but raise an exception
        k2.delete()
        self.assertRaises(models.APIException, models.APIKey.objects.is_valid, key, self.user2)

        # Some random string should also not be valid
        assert not models.APIKey.objects.is_valid('not valid', self.user)

    def test_get_key_from_profile_no_key(self):
        '''There should be a method to create an API key by having the user's profile object, even if they have not already created one before.'''
        profile = self.user.get_profile()
        assert profile

        assert models.APIKey.objects.filter(user=self.user).count() == 0
        apikey = profile.get_api_key()
        assert apikey

    def test_get_key_from_profile_existing_key(self):
        '''There should be a method to retrieve an API key by having the user's profile object.'''
        profile = self.user.get_profile()
        assert profile

        # Manually create a key
        apikey1 = models.APIKey.objects.create(user=self.user)
        apikey2 = profile.get_api_key()
        assert apikey1.key == apikey2

    def test_view_api_key_on_profile_page(self):
        '''The user's API key should appear on their profile page'''
        self._login()
        response = self.client.get('/account/profile/')
        self.assertTemplateUsed(response, 'auth/profile.html')
        self.assertContains(response, 'testapi', status_code=200)        

        # Get this API key
        key = self.user.get_profile().get_api_key()
        assert key is not None
        assert len(key) == 32

        assert key in response.content
        
    def test_api_key_change_on_username_change(self):
        '''The user's API key should change when their username is updated'''
        user = User.objects.create_user(username="usernamechange",email="usernamechange@example.com",password="usernamechange")
        library_models.UserPref.objects.create(user=user)
        key1 = user.get_profile().get_api_key()
        
        user.username = 'username2'
        user.save()

        assert key1 != user.get_profile().get_api_key()

    def test_api_key_change_on_password_change(self):
        '''The user's API key should change when their password is updated'''
        user = User.objects.create_user(username="passwordchange",email="passwordchange@example.com",password="passwordchange")
        library_models.UserPref.objects.create(user=user)
        key1 = user.get_profile().get_api_key()
        
        user.password = 'password2'
        user.save()

        assert key1 != user.get_profile().get_api_key()


    def test_api_key_change_not_on_email_change(self):
        '''The user's API key should NOT change when their email is updated'''
        user = User.objects.create_user(username="emailchange",email="emailchange@example.com",password="emailchange")
        library_models.UserPref.objects.create(user=user)
        key1 = user.get_profile().get_api_key()
        
        user.email = 'email2@example.com'
        user.save()

        assert key1 == user.get_profile().get_api_key()

    def test_api_key_change_on_password_web(self):
        '''The user's API key should visibly change on the web site after updating their password from the web'''
        username = 'test_change_password'
        email = 'test_change_password@example.com'
        password = 'test_change_password'
        self._register_standard(username, email, password)
        user = User.objects.get(username=username)
        response = self.client.get('/account/profile/')
        self.assertTemplateUsed(response, 'auth/profile.html')
        self.assertContains(response, username, status_code=200)        

        # Get this API key
        key = user.get_profile().get_api_key()
        assert key is not None
        assert len(key) == 32
        assert key in response.content

        response = self.client.post('/account/password/', { 'oldpw':password,
                                                            'password1':'registertest2',
                                                            'password2':'registertest2'})
        self.assertRedirects(response, '/account/profile/?msg=Password+changed.', 
                             status_code=302, 
                             target_status_code=200)           
        
        response = self.client.get('/account/profile/')

        key2 = user.get_profile().get_api_key()
        assert len(key2) == 32
        assert key not in response.content
        assert key2 in response.content
        assert key2 != key

    def test_api_key_change_on_email_web(self):
        '''The user's API key should NOT visibly change on the web site after updating their email from the web'''
        username = 'test_change_email'
        email = 'test_change_email@example.com'
        password = 'test_change_email'
        self._register_standard(username, email, password)
        user = User.objects.get(username=username)
        response = self.client.get('/account/profile/')
        self.assertTemplateUsed(response, 'auth/profile.html')
        self.assertContains(response, username, status_code=200)        

        # Get this API key
        key = user.get_profile().get_api_key()
        assert key is not None
        assert len(key) == 32
        assert key in response.content

        response = self.client.post('/account/email/', { 'password':password,
                                                         'email':'changedemail@example.com'})

        self.assertRedirects(response, '/account/profile/?msg=Email+changed.', 
                             status_code=302, 
                             target_status_code=200)           
        
        response = self.client.get('/account/profile/')
        assert 'changedemail@example.com' in response.content

        assert key in response.content


    def test_api_key_change_on_username_web(self):
        '''The user's API key should visibly change on the web site after updating their username from the web'''
        pass # There's no method to change a username on Bookworm via the web API

    def test_api_fail_anon(self):
        '''An anonymous user should not be able to log in to the API without an API key'''
        self.client.get('/api/documents/', status_code=UNAUTHED_STATUS_CODE_PUBLISHED)   

    def test_api_fail_logged_in(self):
        '''A logged-in user should not be able to log in to the API without an API key'''
        self._login()
        self.client.get('/api/documents/', status_code=UNAUTHED_STATUS_CODE_PUBLISHED)

    def test_api_fail_bad_key(self):
        '''A logged-in user should not be able to log in to the API with the wrong API key'''
        self._login()
        self.client.get('/api/documents/', { 'api_key': 'None'}, status_code=UNAUTHED_STATUS_CODE_PUBLISHED)

    def test_api_fail_anon_unpublished(self):
        '''An anonymous user should not be able to log in to the unpublished API without an API key'''
        self.client.get('/api/documents/1/', status_code=UNAUTHED_STATUS_CODE_UNPUBLISHED)   

    def test_api_fail_logged_in_unpublished(self):
        '''A logged-in user should not be able to log in to the unpublished API without an API key'''
        self._login()
        self.client.get('/api/documents/1/', status_code=UNAUTHED_STATUS_CODE_UNPUBLISHED)

    def test_api_fail_bad_key(self):
        '''A logged-in user should not be able to log in to the API with the wrong API key'''
        self._login()
        self.client.get('/api/documents/1/', { 'api_key': 'None'}, status_code=UNAUTHED_STATUS_CODE_UNPUBLISHED)

    def test_api_fail_bad_key(self):
        '''A logged-in user should not be able to log in to the unpublished API with the wrong API key'''
        self._login()
        self.client.get('/api/documents/1/', { 'api_key': 'None'}, status_code=UNAUTHED_STATUS_CODE_UNPUBLISHED)


    @reset_books
    def test_api_list_no_results(self):
        '''A user should be able to log in to the API with the correct API key and get a valid XHTML page even with no books.'''
        key = self.userpref.get_api_key()
        response = self.client.get('/api/documents/', { 'api_key': key})
        self._validate_page(response)

    @reset_books
    def test_api_list_results(self):
        '''A user should be able to log in to the API with the correct API key and get a valid XHTML listing of their books..'''        
        self._login()
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)

        self.client.logout()
        response = self.client.get('/api/documents/', { 'api_key': self.userpref.get_api_key()})
        self._validate_page(response)
        assert name in response.content

    @reset_books
    def test_api_list_results_ordered(self):
        '''API Documents should be presented in an ordered list.'''
        self._login()
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        name2 = 'alice-fromAdobe.epub'
        self._upload(name)
        self._upload(name2)

        self.client.logout()
        response = self.client.get('/api/documents/', { 'api_key': self.userpref.get_api_key()})
        self._validate_page(response)
        assert '<ol>' in response.content
        assert '<li>' in response.content
        assert name in response.content
        assert name2 in response.content

    @reset_books
    def test_api_list_results_title(self):
        '''API Documents should include their title.'''
        self._login()
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)

        self.client.logout()
        response = self.client.get('/api/documents/', { 'api_key': self.userpref.get_api_key()})
        self._validate_page(response)
        assert 'Pride and Prejudice' in response.content

    @reset_books
    def test_api_list_results_author(self):
        '''API Documents should include their author.'''
        self._login()
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)

        self.client.logout()
        response = self.client.get('/api/documents/', { 'api_key': self.userpref.get_api_key()})
        self._validate_page(response)
        assert 'Jane Austen' in response.content

    @reset_books
    def test_api_list_results_date_added(self):
        '''API Documents should include the date the epub was added.'''
        self._login()
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)

        self.client.logout()
        response = self.client.get('/api/documents/', { 'api_key': self.userpref.get_api_key()})
        self._validate_page(response)
        document = library_models.EpubArchive.objects.get(name=name)
        assert str(document.created_time) in response.content

    @reset_books
    def test_api_list_ordering(self):
        '''API document lists should be ordered by date added'''
        self._login()
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)
        name2 = 'alice-fromAdobe.epub'
        self._upload(name2)
        
        self.client.logout()
        response = self.client.get('/api/documents/', { 'api_key': self.userpref.get_api_key()})

        self._validate_page(response)
        page = etree.fromstring(response.content)

        assert 'Pride' in page.xpath('//xhtml:li[1]/xhtml:span[@class="document-title"]/text()', namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})[0]
        assert 'Alice' in page.xpath('//xhtml:li[2]/xhtml:span[@class="document-title"]/text()', namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})[0]

        # Delete the books and add in the opposite order
        [ua.delete() for ua in library_models.UserArchive.objects.all() ]        
        [d.delete() for d in library_models.EpubArchive.objects.all() ]        

        self._login()
        self._upload(name2)
        self._upload(name)

        self.client.logout()
        response = self.client.get('/api/documents/', { 'api_key': self.userpref.get_api_key()})
        self._validate_page(response)

        page = etree.fromstring(response.content)
        assert 'Alice' in page.xpath('//xhtml:li[1]/xhtml:span[@class="document-title"]/text()', namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})[0]
        assert 'Pride' in page.xpath('//xhtml:li[2]/xhtml:span[@class="document-title"]/text()', namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})[0]


    @reset_books
    def test_api_download(self):
        '''Documents can be downloaded using the API'''
        self._login()
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)

        self.client.logout()

        # Assert that they can't download using the traditional web UI (because they're not authed)
        response = self.client.get('/download/epub/test/1/')
        assert response.status_code == 404
        
        response = self.client.get('/api/documents/1/', { 'api_key': self.userpref.get_api_key()})
        assert 'application/epub+zip' in response['Content-Type'] 

        # Check that it's the same bytes that we started with
        assert response.content == helper.get_file(name)

    @reset_books
    def test_api_download_wrong_user(self):
        '''Documents can be downloaded using the API only if they are owned by the user of the key'''
        self._login()
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)

        self.client.logout()

        # Assert that user2 can't download this
        response = self.client.get('/api/documents/1/', { 'api_key': self.userpref2.get_api_key()})
        assert response.status_code == UNAUTHED_STATUS_CODE_UNPUBLISHED 

        # ...but user1 can
        response = self.client.get('/api/documents/1/', { 'api_key': self.userpref.get_api_key()})
        assert response.status_code == 200

    @reset_books
    def test_api_download_fail(self):
        '''Users who aren't authenticated properly should return an unauthed response instead of a document request.'''
        self._login()
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)
        self.client.logout()
        response = self.client.get('/api/documents/1/', { 'api_key': 'Fail'})
        assert response.status_code == UNAUTHED_STATUS_CODE_UNPUBLISHED

    def test_api_upload_fail_auth(self):
        '''Users who try to upload without being aren't authenticated properly should return an unauthored response.'''
        response = self.client.post('/api/documents/', { 'api_key': 'Fail'})
        assert response.status_code == UNAUTHED_STATUS_CODE_PUBLISHED

    def test_api_upload_no_param(self):
        '''Users who are authenticated properly but don't provide an acceptable parameter for uploading should get a failed response'''
        response = self.client.post('/api/documents/')
        assert response.status_code == UNAUTHED_STATUS_CODE_PUBLISHED

    @reset_books        
    def test_api_upload_param(self):
        '''Users who are authenticated properly and provide an epub_url parameter should be able to upload that document.'''
        response = self.client.post('/api/documents/', { 'api_key': self.userpref.get_api_key(),
                                                         'epub_url': EXTERNAL_EPUB_URL })
        assert response.status_code == UPLOAD_STATUS_CODE

        assert '/api/documents/1/' in response['Content-Location']

       # Assert that we can get the document from the location in the response
        response = self.client.get(response['Content-Location'].replace(settings.HOSTNAME, ''), { 'api_key':self.userpref.get_api_key() })
        assert response.status_code == 200

        # Assert that it's the right number of bytes
        assert len(response.content) == 335933

        # Check that it's in their API list now
        response = self.client.get('/api/documents/', { 'api_key': self.userpref.get_api_key()})
        assert 'Sense and Sensibility' in response.content
        
        # Check that it's in their Bookworm site library too
        self._login()
        response = self.client.get('/library/')
        assert 'Sense and Sensibility' in response.content

    @reset_books        
    def test_api_upload_bytes(self):
        '''Users should be able to upload a document by sending a stream of epub bytes'''
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        assert library_models.EpubArchive.objects.filter(name=name).count() == 0
        response = self.client.post('/api/documents/', { 'api_key': self.userpref.get_api_key(),
                                                         'epub_data': helper.get_filehandle(name) })        
        assert response.status_code == UPLOAD_STATUS_CODE
        assert library_models.EpubArchive.objects.filter(name=name).count() == 1

        # Check that it's in their API list now
        response = self.client.get('/api/documents/', { 'api_key': self.userpref.get_api_key()})
        assert 'Pride and Prejudice' in response.content

        # Check that it's in their Bookworm site library too
        self._login()
        response = self.client.get('/library/')
        assert 'Pride and Prejudice' in response.content

    @reset_books        
    def test_api_upload_bytes_invalid(self):
        '''Users should get a useful reply when a uploaded book is invalid and cannot be added.'''
        name = 'invalid-no-title.epub'
        assert library_models.EpubArchive.objects.filter(name=name).count() == 0
        response = self.client.post('/api/documents/', { 'api_key': self.userpref.get_api_key(),
                                                         'epub_data': helper.get_filehandle(name) })        

        self._wellformed(response, UPLOAD_STATUS_CODE_UNACCEPTABLE)

        # We should still have zero documents
        assert library_models.EpubArchive.objects.filter(name=name).count() == 0

    def test_api_mention_on_help(self):
        '''The help page should mention the API'''
        response = self.client.get('/help/')
        assert 'API' in response.content

    def test_api_key_help_link(self):
        '''The user's API key should link to the API help when displayed'''
        self._login()
        response = self.client.get(reverse('profile')) #'/account/profile/')
        assert reverse('api_help') in response.content

    def _wellformed(self, response, status_code=200):
        '''Ensure that this response is well-formed as XML'''
        assert response.status_code == status_code

        # The response should be well-formed XHTML but have the correct response code
        etree.fromstring(response.content)

    def _validate_page(self, response, status_code=200):
        '''Validate that this response contains a valid XHTML result'''
        assert response.status_code == status_code
        page = etree.fromstring(response.content)
        assert page is not None
        self.relaxng.assertValid(page)

        
    def _register_standard(self, username, email, password):
        '''Register a new account using a standard Django account'''
        response = self.client.post('/account/signup/', { 'username':username,
                                                          'email':email,
                                                          'password1':password,
                                                          'password2':password})
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/library/')
        self.assertTemplateUsed(response, 'index.html')
        self.assertContains(response, username, status_code=200)

    def _upload(self, f):
        self._login()
        fh = helper.get_filehandle(f)
        response = self.client.post('/upload/', {'epub':fh})
        return response
        
    def _login(self):
        self.assertTrue(self.client.login(username='testapi', password='testapi'))

