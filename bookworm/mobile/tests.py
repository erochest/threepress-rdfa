#!/usr/bin/env python
# encoding: utf-8
import shutil, os, re, unittest, logging, datetime, sys, shutil
from os.path import isfile, isdir

from django.contrib.auth.models import User
from django.test import TestCase as DjangoTestCase
from django.conf import settings
from django.http import HttpResponseNotFound
from django.core import mail

from bookworm.search import epubindexer, index
from bookworm.library.models import *
from bookworm.library.testmodels import *
from bookworm.library.epub.toc import TOC
from bookworm.library.epub.constants import *
from bookworm.library.tests import TestModels as TestLibraryModels

from twill import get_browser
from twill.errors import TwillAssertionError
from twill import add_wsgi_intercept
from twill.commands import *


settings.SITE_ID = 1

# Delete the cache from earlier runs (otherwise some templates
# will not return a response)
try:
    shutil.rmtree(settings.CACHE_BACKEND.replace('file://', ''))
except:
    pass

# Data for public epub documents
DATA_DIR = unicode(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../library/test-data/data'))

STORAGE_DIR = settings.MEDIA_ROOT

# Local documents should be added here and will be included in tests,
# but not in the svn repository
PRIVATE_DATA_DIR = u'%s/private' % DATA_DIR


# Model tests should work exactly the same as in the standard library
class TestModels(TestLibraryModels):
    pass
    
class TestViews(DjangoTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser",email="test@example.com",password="testuser")
        self.user.save()        

        profile = UserPref(user=self.user)
        profile.language = 'en'
        profile.save()
        
        from django.contrib.sites.models import Site
        Site.objects.get_or_create(id=1)

    def tearDown(self):
        self.user.delete()

    def test_is_inner_path_protected(self):
        self._login()
        self.client.logout()
        response = self.client.get('/account/profile/')
        self.assertRedirects(response, '/account/signin/?next=/account/profile/', 
                             status_code=302, 
                             target_status_code=200)

    def test_home_unprotected(self):
        '''There is no public home on the mobile site; prompt to login immediately'''
        try:
            self.client.logout()
        except:
            pass
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'authopenid/signin.html')
        self._login()

    def test_login(self):
        self._login()
        response = self.client.get('/')
        self.assertRedirects(response, '/library/')
        response = self.client.get('/library/')
        self.assertTemplateUsed(response, 'index.html')
        # self.assertContains(response, 'testuser') mobile UI doesn't show username

    def test_upload(self):
        response = self._upload('Pride-and-Prejudice_Jane-Austen.epub')
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)

    def test_upload_invalid_epub(self):
        response = self._upload('invalid-no-toc.epub')
        self.assertTemplateUsed(response, 'upload.html')
        self.assertContains(response, 'TOC file was referenced in OPF, but not found in archive')
        # Check that we talked to epubcheck too
        self.assertContains(response, 'agrees that')
        self.assertContains(response, 'toc-doesnt-exist.ncx is missing')

    def xxx_test_rights_document(self):
        '''Assert that we correctly recognize a rights-managed epub and email the admin'''
        '''Removed in infrastructure; don't bother sending email now '''
        filename = 'invalid-rights-managed.epub'
        self._upload(filename)

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to[0] == settings.ERROR_EMAIL_RECIPIENTS
        assert 'DRM' in mail.outbox[0].subject

    def test_content_visible(self):
        response = self._upload('Cory_Doctorow_-_Little_Brother.epub')

        id = '1'
        response = self.client.get('/view/Little-Brother/%s/main5.xml' % id)
        self.assertTemplateUsed(response, 'view.html')

    def test_upload_with_nested_urls(self):
        response = self._upload('Bible.epub')
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)        
        id = '1'
        response = self.client.get('/view/The+Bible/%s/Genesis/Genesis3.html' % id)
        self.assertTemplateUsed(response, 'view.html')

    def test_reload(self):
        '''Test the ability to reload an existing book'''
        response = self._upload('Cory_Doctorow_-_Little_Brother.epub')
        response = self.client.get('/view/Little-Brother/1/')
        self.assertTemplateUsed(response, 'view.html')        

        self.assertContains(response, 'Doctorow')
        self.assertNotContains(response, 'Prejudice')

        # Now replace it with a different book
        fh = _get_filehandle('Pride-and-Prejudice_Jane-Austen.epub')
        response = self.client.post('/reload/Little-Brother/1/', {'epub':fh})

        self.assertTrue(type(response) != HttpResponseNotFound)
        response = self.client.get('/view/Little-Brother/1/')
        self.assertTemplateUsed(response, 'view.html')        
        self.assertNotContains(response, 'Doctorow')
        self.assertContains(response, 'Prejudice')

        response = self.client.get('/metadata/test/1/')
        self.assertContains(response, 'Reload this book')

        epub = EpubArchive.objects.get(id=1)
        epub.is_public = True
        epub.save()

        # Public books should still be overwriteable by the owner
        response = self.client.get('/metadata/test/1/')
        self.assertTemplateUsed(response, 'view.html')
        self.assertContains(response, 'Reload this book')        

        # But not by users who aren't the owner
        self.client.logout()
        response = self.client.post('/account/signup/', { 'username':'reload2test',
                                                          'email':'reload2test@example.com',
                                                          'password1':'reload2test',
                                                          'password2':'reload2test'})

        response = self.client.get('/metadata/test/1/')        
        self.assertTemplateUsed(response, 'view.html')
        self.assertNotContains(response, 'Reload this book')        

    def test_no_reload_if_not_owner(self):
        '''Don't allow reloading of a book if you don't own it'''
        response = self._upload('Cory_Doctorow_-_Little_Brother.epub')
        response = self.client.get('/view/Little-Brother/1/')
        self.assertTemplateUsed(response, 'view.html')        
        epub = EpubArchive.objects.get(id=1)


        self.client.logout()
        response = self.client.post('/account/signup/', { 'username':'reloadtest',
                                                          'email':'reloadtest@example.com',
                                                          'password1':'reloadtest',
                                                          'password2':'reloadtest'})


        # Try viewing it; this should fail
        response = self.client.get('/view/Little-Brother/1/')
        self.assertTrue(type(response) == HttpResponseNotFound)

        epub.is_public = True
        epub.save()

        response = self.client.get('/view/Little-Brother/1/')
        self.assertTemplateUsed(response, 'view.html')        
        
        # View the document so we have a UserArchive record but NOT ownership
        fh = _get_filehandle('Pride-and-Prejudice_Jane-Austen.epub')
        response = self.client.post('/reload/Little-Brother/1/', {'epub':fh})
        self.assertTrue(type(response) == HttpResponseNotFound)

    def test_upload_with_images(self):
        ''' Image uploads should work whether or not their path is specified'''
        response = self._upload('alice-fromAdobe.epub')
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)        
        response = self.client.get('/view/alice/1/images/alice01a.gif')
        self.assertEquals(response.status_code, 200)

        response = self.client.get('/view/alice/1/alice01a.gif')
        self.assertEquals(response.status_code, 200)

    def test_upload_with_pathless_image(self):
        response = self._upload(u'天.epub')
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)        

        response = self.client.get('/view/chinese/1/cover.jpg')
        self.assertEquals(response.status_code, 200)

        response = self.client.get('/view/chinese/1/www/cover.jpg')
        self.assertEquals(response.status_code, 200)

    def test_upload_no_title(self):
        response = self._upload('invalid-no-title.epub')
        self.assertTemplateUsed(response, 'upload.html')
        self.assertContains(response, 'This ePub document does not have a title.')
        


    def test_next_previous(self):
        '''Assert that we can move next and previous through our list of books'''
        # Load enough books to exceed our settings pagination label
        for a in range(1, (settings.DEFAULT_NUM_RESULTS * 2) ):
            response = self._upload('Cory_Doctorow_-_Little_Brother.epub')
            self.assertRedirects(response, '/library/', 
                                 status_code=302, 
                                 target_status_code=200)        

        response = self.client.get('/library/')
        self.assertContains(response, 'Page 1 of 2')


        response = self.client.get('/page/2')
        self.assertTemplateUsed(response, 'index.html')
        self.assertContains(response, 'Page 2 of 2')

        response = self.client.get('/page/1')
        self.assertTemplateUsed(response, 'index.html')
        self.assertContains(response, 'Page 1 of 2')

        # Going to an incorrect range should redirect us back to the first page
        response = self.client.get('/page/99')
        self.assertRedirects(response, '/page/1',
                             status_code=302,
                             target_status_code=200)

    def test_ordering(self):
        '''Test our re-ordering of books'''
        # Load enough books to exceed our settings pagination label
        for a in range(1, (settings.DEFAULT_NUM_RESULTS * 2) ):
            response = self._upload('Cory_Doctorow_-_Little_Brother.epub')
            self.assertRedirects(response, '/library/', 
                                 status_code=302, 
                                 target_status_code=200)        
        
        response = self.client.get('/library/')
        self.assertContains(response, 'Page 1 of 2')

        response = self.client.get('/page/1/order/title/dir/asc')
        self.assertContains(response, 'Page 1 of 2')

        response = self.client.get('/page/1/order/orderable_author/dir/asc')
        self.assertContains(response, 'Page 1 of 2')

        response = self.client.get('/page/1/order/created_time/dir/desc')
        self.assertContains(response, 'Page 1 of 2')

        # Test that the next page preserves this and generates the right link
        response = self.client.get('/page/2/order/created_time/dir/desc')
        self.assertContains(response, 'Page 2 of 2')
        
        self.assertContains(response, '<a href="/page/1/order/created_time/dir/desc">← previous </a>')

        # Test that the prev page preserves this and generates the right link
        response = self.client.get('/page/1/order/created_time/dir/desc')
        self.assertContains(response, 'Page 1 of 2')
        
        self.assertContains(response, '<a href="/page/2/order/created_time/dir/desc">next →</a>')



    def test_upload_with_utf8(self):
        response = self._upload('The-Adventures-of-Sherlock-Holmes_Arthur-Conan-Doyle.epub')
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)        

        # Make sure it's in the list
        response = self.client.get('/library/')
        self.assertContains(response, '/view/The+Adventures+of+Sherlock')

    def test_delete_with_utf8(self):
        response = self._upload('The-Adventures-of-Sherlock-Holmes_Arthur-Conan-Doyle.epub')
        # Make sure it's in the list
        response = self.client.get('/library/')
        self.assertContains(response, '/view/The+Adventures+of+Sherlock')


        response = self.client.post('/delete/', { 'title':'The+Adventures+of+Sherlock+Holmes',
                                       'key':'1'})
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/library/')
        self.assertNotContains(response, '/view/The+Adventures+of+Sherlock')


    def test_upload_with_entities(self):
        response = self._upload('html-entities.epub')
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)   

    def test_view_document(self):
        self._upload('Pride-and-Prejudice_Jane-Austen.epub')
        response = self.client.get('/view/Pride-and-Prejudice/1/')
        self.assertTemplateUsed(response, 'view.html')
        self.assertContains(response, 'Pride and Prejudice', status_code=200)

    def test_view_chapter(self):
        self._upload('Pride-and-Prejudice_Jane-Austen.epub')
        response = self.client.get('/view/Pride-and-Prejudice/1/chapter-1.html')
        self.assertTemplateUsed(response, 'view.html')
        self.assertContains(response, 'It is a truth universally acknowledged', status_code=200)

    def test_view_svg(self):
        self._upload('EPUBBestPractices-1_0_2.epub')
        response = self.client.get('/view/EPUB+Best+Practices/1/Container_(OCF).xhtml')
        self.assertTemplateUsed(response, 'view.html')
        self.assertContains(response, 'View linked image in SVG format')
        response = self.client.get('/view/EPUB+Best+Practices/1/images/OPS.svg')
        self.assertEquals(response.status_code, 200)

    def test_delete_book(self):
        self._upload('Pride-and-Prejudice_Jane-Austen.epub')        
        response = self.client.post('/delete/', { 'title':'Pride+and+Prejudice',
                                       'key':'1'})
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)   
        

    def test_delete_not_owner(self):
        self._upload('Pride-and-Prejudice_Jane-Austen.epub')        
        user = User.objects.create_user(username="testnotowner",email="testnotowner@example.com",password="testnowowner")        
        book = EpubArchive.objects.get(id=1)
        book.set_owner(user)

        self.assertTrue(book.is_owner(user))
        
        response = self.client.post('/delete/', { 'title':'Pride+and+Prejudice',
                                       'key':'1'})
        assert response.status_code == 404

        # Make sure the book is still there
        book = EpubArchive.objects.get(id=1)        

        # Ensure this works for public books too
        book.is_public = True
        book.save()
        response = self.client.post('/delete/', { 'title':'Pride+and+Prejudice',
                                       'key':'1'})
        assert response.status_code == 404

        # Make sure the book is still there
        book = EpubArchive.objects.get(id=1)        

    def test_view_profile(self):
        self._login()
        response = self.client.get('/account/profile/')
        self.assertTemplateUsed(response, 'auth/profile.html')
        self.assertContains(response, 'testuser', status_code=200)        

    def test_view_about_not_logged_in(self):
        '''This throws an exception if the user profile isn't properly handled for anonymous requests'''
        response = self.client.get('/about/')
        self.assertContains(response, 'About', status_code=200)                


    def test_open_to_last_chapter(self):
        self._upload('Pride-and-Prejudice_Jane-Austen.epub')

        uprofile = UserPref.objects.get(user=self.user)
        uprofile.open_to_last_chapter = True
        uprofile.save()

        response = self.client.get('/view/Pride-and-Prejudice/1/')
        self.assertTemplateUsed(response, 'view.html')        
        first_page = response.content

        # Read a page somewhere in the document
        response = self.client.get('/view/Pride-and-Prejudice/1/chapter-10.html')
        self.assertTemplateUsed(response, 'view.html')
        last_chapter_content = response.content

        # Now go to the default page; should be last chapter
        response = self.client.get('/view/Pride-and-Prejudice/1/')
        self.assertTemplateUsed(response, 'view.html')        
        self.assertEquals(last_chapter_content, response.content)

        # Now change our user profile to not select this behavior
        uprofile.open_to_last_chapter = False
        uprofile.save()

        response = self.client.get('/view/Pride-and-Prejudice/1/')
        self.assertTemplateUsed(response, 'view.html')        
        self.assertNotEquals(last_chapter_content, response.content)        
        self.assertEquals(first_page, response.content)

        # But we should still be able to force it with the resume parameter
        response = self.client.get('/view/Pride-and-Prejudice/1/chapter-10.html')
        self.assertTemplateUsed(response, 'view.html')
        last_chapter_content = response.content

        response = self.client.get('/view/resume/Pride-and-Prejudice/1/')
        self.assertTemplateUsed(response, 'view.html')        
        self.assertEquals(last_chapter_content, response.content)        
        self.assertNotEquals(first_page, response.content)        

    def test_force_first_page(self):
        self._upload('Pride-and-Prejudice_Jane-Austen.epub')

        uprofile = UserPref.objects.get(user=self.user)
        uprofile.open_to_last_chapter = True
        uprofile.save()

        response = self.client.get('/view/Pride-and-Prejudice/1/')
        self.assertTemplateUsed(response, 'view.html')        
        first_page = response.content

        # Read a page somewhere in the document
        response = self.client.get('/view/Pride-and-Prejudice/1/chapter-10.html')
        self.assertTemplateUsed(response, 'view.html')
        last_chapter_content = response.content

        # Force first chapter chapter
        response = self.client.get('/view/first/Pride-and-Prejudice/1/')
        self.assertRedirects(response, '/view/Pride+and+Prejudice/1/chapter-1.html')

    def test_dtbook(self):
        '''We should be able to parse and expand out a DTBook-format
        book'''
        self._upload('hauy.epub')
        response = self.client.get('/view/dtbook/1/')
        self.assertTemplateUsed(response, 'view.html')        
        self.assertContains(response, 'Enlightenment')
        
    def test_public_book(self):
        '''A book marked as 'is_public' should be viewable to
        all users'''
        # Upload a book 
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)

        document = EpubArchive.objects.filter(name=name)[0]
        document.is_public = False
        document.save()

        # The user should be able to see their own book
        response = self.client.get('/view/a/%s/' % document.id)
        self.assertContains(response, 'Pride')

        self.client.logout()

        # This shouldn't throw an exception, just complain we're not logged in
        response = self.client.get('/metadata/a/%s/' % document.id)
        self.assertEquals(response.status_code, 404)

        response = self.client.get('/css/a/%s/' % document.id)
        self.assertEquals(response.status_code, 404)

        user = User.objects.create_user(username="testuser2",email="test2@example.com",password="testuser2")
        user.save()        
        profile = UserPref(user=user)
        profile.save()
        
        self.assertTrue(self.client.login(username='testuser2', password='testuser2'))

        response = self.client.get('/view/a/%s/' % document.id)
        self.assertEquals(response.status_code, 404)

        # Because of Django's weirdness, a URL not ending in a / will 302 
        # in response to a 404
        response = self.client.get('/view/a/%s/chapter-2.html' % document.id)
        self.assertEquals(response.status_code, 302)
        
        document.is_public = True
        document.save()        
        
        response = self.client.get('/view/a/%s/chapter-2.html' % document.id)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Pride')

        # The 2ndary user shouldn't have a user-archive entry for this
        self.assertEquals(user.user_archive.count(), 0)
        self.assertEquals(self.user.user_archive.order_by('-id')[0].last_chapter_read.filename, 'chapter-1.html')

        # Now log out altogether and make sure the links all work
        self.client.logout()

        response = self.client.get('/view/a/%s/' % document.id)
        self.assertEquals(response.status_code, 200)

        response = self.client.get('/view/a/%s/chapter-2.html' % document.id)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Pride')
        
    def test_list_books_singly(self):
        '''New code caused multiple duplicate items in the user's library list'''
        name = 'test-single-listing.epub'
        self._upload(name)
        document = EpubArchive.objects.filter(name=name)[0]

        response = self.client.get('/library/')
        self.assertContains(response, 'Single Listing', 1)

        response = self.client.get('/view/a/%s/' % document.id)
        self.assertEquals(response.status_code, 200)

        # Make sure the title only appears once
        response = self.client.get('/library/')
        self.assertContains(response, 'Single Listing', 1)

    def test_download_utf8_title(self):
        '''Django won't allow content-disposition to contain non-ASCII chars,
        so check that we handle this gracefully'''
        self._upload(u'天.epub')
        response = self.client.get('/download/epub/天/1/')
        self.assertEquals(response.status_code, 200)
        self.assertTrue( '\u5929.epub' in response['Content-Disposition'])
        
        # Other files should decompose better
        self._upload(u'halála.epub')
        response = self.client.get('/download/epub/halála/2/')        
        self.assertEquals(response.status_code, 200)
        self.assertTrue('.epub' in response['Content-Disposition'])

    def test_invalid_file_with_utf8(self):
        '''Exception was being thrown from error handling on non-ASCII data'''
        response = self._upload(u'invalid_天.epub')
        self.assertContains(response, 'problems')

    def test_invalid_container(self):
        '''Give a helpful message if the container is broken'''
        response = self._upload(u'invalid-no-namespaced-container.epub')
        self.assertContains(response, 'Check that your META-INF/container.xml file is correct')


    def test_duplicate_filerefs(self):
        response = self._upload(u'duplicate-itemref.epub')
        archive = EpubArchive.objects.get(id=1)
        HTMLFile.objects.create(archive=archive, filename='chapter-1.html')

        # Now there should be two; verify
        self.assertEquals(2, HTMLFile.objects.filter(archive=archive, filename='chapter-1.html').count())
        
        # Now make sure we can still read it anyway
        response = self.client.get('/view/a/1/chapter-1.html')
        self.assertTemplateUsed(response, 'view.html')

    def test_dc_description(self):
        '''Retrieve dc description field'''
        document = self._upload('dc-description.epub')
        response = self.client.get('/metadata/a/1/')
        self.assertContains(response, 'This is a description')

    def test_view_with_multiple_dates(self):
        '''Was returning 'Unknown' rather than displaying a date.  Ultimately should
        be able to handle all dates and provide appropriate opf:event information.'''
        name = 'multiple-dc-dates.epub'
        self._upload(name)
        response = self.client.get('/metadata/test/1/')        
        self.assertNotContains(response, 'Unknown')
        self.assertContains(response, '01') # should be January but Python inanely doesn't handle <1900 dates
        self.assertContains(response, '1888')
        
    def test_duplicate_images_in_opf(self):
        '''Don't complain when images are defined multiple times in the OPF, 
        even though this is an error'''
        name = 'duplicate-images-in-opf.epub'
        self._upload(name)
        response = self.client.get('/view/a/1/image1.gif')
        assert response.status_code == 200

        archive = EpubArchive.objects.get(id=1)

        # If we force-create duplicates, handle this deprecated case gracefully
        ImageFile.objects.create(archive=archive, filename='image1.gif')
        
        # Make sure we have two now
        assert ImageFile.objects.filter(archive=archive, filename='image1.gif').count() == 2
        
        response = self.client.get('/view/a/1/image1.gif')
        assert response.status_code == 200        
        
    def test_spaces_in_opf_items(self):
        '''Allow for encoded spaces in hrefs inside <opf:item>'''
        name = 'images-with-spaces.epub'
        self._upload(name)
        response = self.client.get('/view/a/1/graphics/the%20stamp.png')
        assert response.status_code == 200

    def test_style_in_head(self):
        '''<style> blocks declared in the document head should be included in the output'''
        name ='style-in-head.epub'
        self._upload(name)

        response = self.client.get('/view/a/1/chapter-1.html')

        # Test that head_extra has been populated
        html = HTMLFile.objects.filter(archive__pk=1)[0]
        assert html.head_extra() is not None

        # Check for only inline styles and not the external stylesheet
        assert 'color: red' in response.content
        # If no stylesheets are found it will now fall back to displaying all;
        # so this test no longer applies
        # assert not 'stylesheet.css' in response.content

        assert 'font-weight: bold' in response.content

        response = self.client.get('/view/a/1/with-external-link.html')

        # Check for both inline styles and the external stylesheet
        assert 'color: red' in response.content
        assert 'stylesheet.css' in response.content
        assert 'font-weight: bold' in response.content


    def test_public_pages(self):
        '''Test that public pages render with 200s in all supported languages'''

        for lang in settings.LANGUAGES:
            lang_code = lang[0]
            log.debug("Testing in %s..." % lang[1])
            response = self.client.post('/i18n/setlang/',
                                        { 'language':lang_code})

            response = self.client.get('/about/')
            assert response.status_code == 200
            
            response = self.client.get('/help/')
            assert response.status_code == 200
            assert settings.DISPLAY_ADMIN_EMAIL in response.content

            response = self.client.get('/about/tour/')
            assert response.status_code == 200
            
            response = self.client.get('/publishers/epub/')
            assert response.status_code == 200
            
            response = self.client.get('/publishers/ebook-testing/')
            assert response.status_code == 200
            
            response = self.client.get('/search/help/')
            assert response.status_code == 200
            
            response = self.client.get('/search/language/')
            assert response.status_code == 200
            
            response = self.client.get('/about/reading-mode/')
            assert response.status_code == 200

        # Reset to the default language
        response = self.client.post('/i18n/setlang/',
                                    { 'language':'en'})        

    def test_account_page(self):
        '''This page should redirect to our profile page'''
        self._login()
        response = self.client.get('/account/')
        self.assertTemplateUsed(response, 'auth/profile.html')

    def test_add_by_url(self):
        '''Test trying to acquire a non-existent ePub'''
        self._login()
        response = self.client.get('/add/')
        assert response.status_code == 404

        response = self.client.get('/add/', { 'epub':'http://idontexist-asdasdsad.com/'})
        assert response.status_code != 404
        assert 'The address you provided does not ' in response.content

        response = self.client.get('/add/', { 'epub':'http://example.com/test.epub'})
        assert response.status_code != 404
        assert 'The address you provided does not ' in response.content

        response = self.client.get('/add/', { 'epub':'http://www.threepress.org/static/epub/Sense-and-Sensibility_Jane-Austen.epub'})
        assert response.status_code != 404
        self.assertRedirects(response, '/library/')
        response = self.client.get('/library/')
        assert 'Sensibility' in response.content

    def test_feedbooks(self):
        '''Test that we get a list of feedbooks books from the main page'''
        self._login()
        response = self.client.get('/library/')
        assert 'feedbooks.com/book' in response.content

    def _login(self):
        self.assertTrue(self.client.login(username='testuser', password='testuser'))
        
    def _upload(self, f):
        self._login()
        fh = _get_filehandle(f)
        response = self.client.post('/upload/', {'epub':fh})
        return response



        
def _get_document(title, id):
    '''@todo Mock this out better instead of overwriting the real view'''
    return MockEpubArchive(id=id)

def _get_file(f):
    '''Get a file from either the public or private data directories'''
    return _get_filehandle(f).read()

def _get_filehandle(f):
    '''Get a file from either the public or private data directories'''
    path = _get_filepath(f)
    return open(path)

def _get_filepath(f):
    data_dir = u'%s/%s' % (DATA_DIR, f)
    if os.path.exists(data_dir):
        return data_dir

    data_dir = u'%s/%s' % (PRIVATE_DATA_DIR, f)
    if os.path.exists(data_dir):
        return data_dir    
    raise OSError('Could not find file %s in either data dir' % f)


if __name__ == '__main__':
    logging.error('Invoke this using "manage.py test"')
