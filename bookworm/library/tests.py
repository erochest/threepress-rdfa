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
from bookworm.library import test_helper as helper

from twill import get_browser
from twill.errors import TwillAssertionError
from twill import add_wsgi_intercept
from twill.commands import *

cssutils.log.setLevel(logging.ERROR)

settings.SITE_ID = 1

# Delete the cache from earlier runs (otherwise some templates
# will not return a response)
try:
    shutil.rmtree(settings.CACHE_BACKEND.replace('file://', ''))
except:
    pass

class TestModels(unittest.TestCase):

    def setUp(self):

        # Add all our test data
        self.documents = [d for d in os.listdir(helper.DATA_DIR) if '.epub' in d and isfile('%s/%s' % (helper.DATA_DIR, d))]

        if isdir(helper.PRIVATE_DATA_DIR):
            self.documents += [d for d in os.listdir(helper.PRIVATE_DATA_DIR) if '.epub' in d and isfile('%s/%s' % (helper.PRIVATE_DATA_DIR, d))] 

        
        self.user = User(username='testuser')
        self.user.save()
        profile = UserPref(user=self.user)
        profile.save()

    def tearDown(self):
        self.user.delete()
        for d in os.listdir(helper.STORAGE_DIR):
            shutil.rmtree("%s/%s" % (helper.STORAGE_DIR, d))

    def test_all_documents(self):
        '''Run through all the documents at a high level'''
        for d in self.documents:
            if d.startswith("invalid"):
                # Test bad documents here?
                pass
            else:
                doc = self._create_document(d)
                doc.explode()

    def test_title(self):
        '''Did we get back the correct title?'''
        title = u'Pride and Prejudice'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        self.assertEquals(title, document.title)

    def test_single_author(self):
        '''Did we get a single author from our author() method?'''
        author = u'Jane Austen'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        self.assertEquals(author, document.author)        

    def test_multiple_authors(self):
        '''Do we return the correct number of authors in the correct order?'''
        expected_authors = [u'First Author', u'Second Author']
        opf_file = 'two-authors.opf'
        document = MockEpubArchive(name=opf_file)
        opf = util.xml_from_string(helper.get_file(opf_file))
        authors = [a.name for a in document.get_authors(opf)]
        self.assertEquals(expected_authors, authors)

    def test_multiple_authors_as_author(self):
        '''Multiple authors should be displayable in a short space.'''
        opf_file = 'two-authors.opf'
        expected_authors = [u'First Author', u'Second Author']
        document = MockEpubArchive(name=opf_file)
        document.save()
        opf = util.xml_from_string(helper.get_file(opf_file))
        
        fuzz = 4
        len_first_author = len(expected_authors[0])
        len_short_author_str = len(document.get_author(opf))
        difference = len_short_author_str - len_first_author
        self.assert_(difference < fuzz)

    def test_no_author(self):
        '''An OPF document with no authors should return None.'''
        no_author_opf_file = 'no-author.opf'
        no_author_document = MockEpubArchive(name=no_author_opf_file)
        no_author_document.save()

        opf = util.xml_from_string(helper.get_file(no_author_opf_file))

        author = no_author_document.get_author(opf)
        self.failIf(author)

    def test_no_author_document(self):
        '''A full document should still pass explode() if there is an empty author'''
        a = self._create_document('No-Author.epub')
        a.explode()

    def test_create_document(self):
        '''Assert that we created a non-None document.'''
        d = self._create_document(self.documents[0])
        self.assert_(d)

    def test_find_document(self):
        """Documents should be findable by title"""
        title = u'Pride and Prejudice'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()

    def test_bad_epub_fails(self):
        """ePub documents with missing component should raise errors."""
        filename = 'invalid_no_container.epub'
        document = self._create_document(filename)
        self.assertRaises(InvalidEpubException, document.explode)

    def test_safe_name(self):
        """Names should be safely quoted for URLs."""
        name = u'John Q., CommasAreForbidden'
        sn = safe_name(name)
        comma_re = re.compile(",")
        result = comma_re.match(sn)
        self.failIf(result)

    def test_count_toc(self):
        '''Check that in a simple document, the number of chapter items equals the number of top-level nav items'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()

        toc = TOC(document.toc)
        self.failUnless(toc)

        chapters = HTMLFile.objects.filter(archive=document)
        self.assertEquals(len(chapters), len(toc.find_points(1)))

    def test_no_toc_in_item(self):
        '''Test an OPF file that has no <item> reference to a TOC'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        opf = helper.get_file('no-toc-item.opf')
        document = self._create_document(filename)        
        document.explode()
        parsed_opf = util.xml_from_string(opf)
        items = [i for i in parsed_opf.iterdescendants(tag="{%s}item" % (NS['opf']))]
        try:
            document._get_toc(parsed_opf, items, 'OEBPS')
        except InvalidEpubException:
            err = str(sys.exc_info()[1])
            self.assertTrue('Could not find an item' in err)
            return
        self.assert_(False)

    def test_no_toc_attribute(self):
        '''Test an OPF file that has no @toc in the <spine>.

        Update: 1/2/09: this now should pass'''
        filename = 'no-toc-attribute-in-spine.epub'
        document = self._create_document(filename)        
        document.explode()
        self.assert_(document)

    def test_no_toc_attribute_incorrect_media_type(self):
        '''Test an OPF file that has no @toc in the <spine> and
        also has the wrong media type for NCX.'''

        filename = 'no-toc-attribute-in-spine-incorrect-media-type.epub'
        document = self._create_document(filename)        
        document.explode()
        self.assert_(document)


    def test_no_toc_findable(self):
        '''Test an OPF file that has an irrecovably-broken TOC declaration.'''

        filename = 'invalid-no-findable-toc.epub'
        document = self._create_document(filename)        
        self.assertRaises(InvalidEpubException, document.explode)


    def test_no_toc(self):
        '''Test an OPF file that has has a TOC reference to a nonexistent file'''
        filename = 'invalid-no-toc.epub'
        document = self._create_document(filename)        
        document.save()
        self.assertRaises(InvalidEpubException, document.explode)
        
    def test_first_item_in_toc(self):
        '''Check that the first_item method returns the correct item based on the rules
        defined in the OCF spec.'''
        toc = TOC(helper.get_file('top-level-toc.ncx'), 
                  helper.get_file('linear-no-missing-linear.opf'))
        first = toc.first_item()
        self.assert_(first)
        self.assertEquals('htmltoc', first.id)

        toc = TOC(helper.get_file('top-level-toc.ncx'), 
                  helper.get_file('linear-no.opf'))
        first = toc.first_item()
        self.assert_(first)
        self.assertEquals('htmltoc', first.id)

    def test_aux_toc(self):
        '''Support one or more lists of additional content'''
        toc = TOC(helper.get_file('auxilliary-lists.ncx'))

        aux1 = toc.lists[0]
        self.assert_(aux1)

        aux2 = toc.lists[1]
        self.assert_(aux2)
        
        self.assertEquals(2, len(toc.lists))
        self.assertEquals(2, len(aux1.tree))
        self.assertEquals(3, len(aux2.tree))
        self.assertEquals('recipe 2', aux2.tree[1].label)
        self.assertEquals('image1.html', aux1.tree[0].href())

    def test_count_deep_toc(self):
        '''Check a complex document with multiple nesting levels'''
        toc = TOC(helper.get_file('complex-ncx.ncx'))
        self.failUnless(toc)
        self.assert_(len(toc.find_points(3)) > len(toc.find_points(2)) > len(toc.find_points(1)))

    def tests_ordered_toc(self):
        '''TOC should preserve the playorder of the NCX'''
        toc = TOC(helper.get_file('complex-ncx.ncx'))
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

    def test_find_children(self):
        '''Get the children of a particular nested TOC node, by node'''
        toc = TOC(helper.get_file('complex-ncx.ncx'))
        self.failUnless(toc)

        # First item is the Copyright statement, which has no children
        copyright_section = toc.tree[0]
        children = toc.find_children(copyright_section)
        self.failIf(children)

        # Second item is the Preface, which has 8 children
        preface = toc.tree[1]
        children = toc.find_children(preface)
        self.assertEquals(8, len(children))

    def test_find_descendants(self):
        '''Get the deep children of a particular nested TOC'''
        toc = TOC(helper.get_file('complex-ncx.ncx'))
        chapter = toc.tree[11]
        ancestors = chapter.find_ancestors()
        self.assertNotEquals(0, len(ancestors))

        intro = toc.tree[10]
        self.assertEquals('pt01.html', intro.href())
        self.assertEquals(intro.id, ancestors[0].id)

        descendants = toc.find_descendants(chapter)
        self.assertEquals(30, len(descendants))

    def test_toc_href(self):
        '''Ensure that we are returning the correct href for an item'''
        toc = TOC(helper.get_file('complex-ncx.ncx'))
        preface = toc.tree[1]
        self.assertEquals("pr02.html", preface.href())

    def test_toc_top_level(self):
        '''We should use the <spine> to locate the top-level navigation items'''
        toc = TOC(helper.get_file('top-level-toc.ncx'), 
                  helper.get_file('top-level-toc.opf'))
        first_page_ncx = toc.tree[0]  
        first_page_spine = toc.items[0]
        self.assertNotEquals(first_page_ncx.label,
                             first_page_spine.label)

    def test_get_file_by_item(self):
        '''Make sure we can find any item by its idref'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        self.assert_(document.opf)
        toc = document.get_toc()
        self.assert_(toc)
        self.assert_(len(toc.items) > 0)
        item = toc.items[2]
        self.assertEquals(item.id, 'chapter-3')
        self.assertEquals(item.media_type, 'application/xhtml+xml')
        self.assertEquals(item.media_type, XHTML_MIMETYPE)
        f = get_file_by_item(item, document)
        self.assertEquals(f.filename, 'chapter-3.html')

    def test_toc_next_previous_item(self):
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        toc = document.get_toc()
        item = toc.items[2]
        self.assertEquals(item.id, 'chapter-3')
        item2 = toc.find_next_item(item)
        self.assertEquals(item2.id, 'chapter-4')        
        item3 = toc.find_previous_item(item2)
        self.assertEquals(item.id, item3.id)


    def test_metadata(self):
        '''All metadata should be returned using the public methods'''
        opf_file = 'all-metadata.opf'
        document = MockEpubArchive(name=opf_file)
        opf = helper.get_file(opf_file)

        self.assertEquals('en-US', document.get_metadata(DC_LANGUAGE_TAG, opf))
        self.assertEquals('Public Domain', document.get_metadata(DC_RIGHTS_TAG, opf))
        self.assertEquals('threepress.org', document.get_metadata(DC_PUBLISHER_TAG, opf))
        self.assertEquals(3, len(document.get_metadata(DC_SUBJECT_TAG, opf)))
        self.assertEquals('Subject 1', document.get_metadata(DC_SUBJECT_TAG, opf)[0])
        self.assertEquals('Subject 2', document.get_metadata(DC_SUBJECT_TAG, opf)[1])
        self.assertEquals('Subject 3', document.get_metadata(DC_SUBJECT_TAG, opf)[2])

        self.assertEquals('en-US', document.get_language())
        self.assertEquals('Public Domain', document.get_rights())
        self.assertEquals('threepress.org', document.get_publisher().all()[0].name)

        document.get_subjects()

        # Test new database methods
        self.assertEquals('en-US', document.language)
        self.assertEquals('Public Domain', document.rights)
        self.assertEquals('threepress.org', document.publishers.all()[0].name)
        self.assertEquals('Subject 1', document.subjects.get(name='Subject 1').name)
        self.assertEquals('Subject 2', document.subjects.get(name='Subject 2').name)
        self.assertEquals('Subject 3', document.subjects.get(name='Subject 3').name)

        # Test metadata without a hyphen -- was broken
        opf_file = 'single-lang-metadata.opf'
        opf = helper.get_file(opf_file)
        document = MockEpubArchive(name=opf_file)
        self.assertEquals('en', document.get_metadata(DC_LANGUAGE_TAG, opf))
        self.assertEquals('en', document.get_major_language())
        self.assertEquals('en', document.language)
    
    def test_publishers(self):
        name = 'Oxford University Press'
        p = EpubPublisher.objects.get_or_create(name=name)[0]
        p.save()
        p2 = EpubPublisher.objects.get(name=name)
        self.assertEquals(p2.name, name)

    def test_subjects(self):
        name = 'Health'
        s = Subject.objects.get_or_create(name=name)[0]
        s.save()
        s2 = Subject.objects.get(name=name)
        self.assertEquals(s2.name, name)


    def test_invalid_xhtml(self):
        '''Documents with non-XML content should be renderable'''
        document = self._create_document('invalid-xhtml.epub')
        document.explode()
        document.save()
        chapters = HTMLFile.objects.filter(archive=document)
        self.assert_(len(chapters) > 0)
        for c in chapters:
            c.render()

    def test_html_entities(self):
        '''Documents which are valid XML except for HTML entities should convert'''
        document = self._create_document('html-entities.epub')
        document.explode()
        document.save()
        chapters = HTMLFile.objects.filter(archive=document)
        self.assert_(len(chapters) > 0)
        for c in chapters:
            c.render()        

    def test_utf8_document(self):
        '''This document has both UTF-8 characters in it and UTF-8 filenames'''
        document = self._create_document(u'天.epub')
        document.explode()
        document.save()
        chapters = HTMLFile.objects.filter(archive=document)
        self.assert_(len(chapters) > 0)
        for c in chapters:
            c.render()        

    def test_remove_html_namespaces(self):
        filename = 'Cory_Doctorow_-_Little_Brother.epub'        
        document = self._create_document(filename)
        document.explode()
        document.save()
        chapters = HTMLFile.objects.filter(archive=document)
        self.assert_('html:br' not in chapters[0].render())

    def test_remove_body_tag(self):
        '''We should not be printing the original document's <body> tag'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        chapters = HTMLFile.objects.filter(archive=document)
        self.assert_(len(chapters) == 61)
        for c in chapters:
            self.assert_('<body' not in c.render())
            self.assert_('<div id="bw-book-content"' in c.render())


        
    def test_chapters(self):
        '''When switching to lxml, chapters in this book did not get captured'''
        filename = 'Cory_Doctorow_-_Little_Brother.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        chapters = HTMLFile.objects.filter(archive=document)
        self.assert_(chapters)
        
    def test_binary_image(self):
        '''Test the ImageBlob class directly'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        imagename = 'alice01a.gif'
        image = helper.get_file(imagename)

        [i.delete() for i in MockImageBlob.objects.filter(idref=imagename)]

        image_obj = MockImageFile.objects.create(idref=imagename,
                                                 archive=document)
        i = MockImageBlob.objects.create(archive=document,
                                         idref=imagename,
                                         image=image_obj,
                                         data=image,
                                         filename=imagename)

        i2 = MockImageBlob.objects.get(idref=imagename)
        self.assertTrue(i2.get_data() is not None)
        self.assertEquals(image, i2.get_data())
        i2.delete()

    def test_binary_storage_exists(self):
        '''Test that we correctly implement the required 'exists()' method for Django Storage'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        imagename = 'alice01a.gif'
        image = helper.get_file(imagename)
        [i.delete() for i in MockImageBlob.objects.filter(idref=imagename)]
        image_obj = MockImageFile.objects.create(idref=imagename,
                                                 archive=document)
        i = MockImageBlob.objects.create(archive=document,
                                         idref=imagename,
                                         image=image_obj,
                                         data=image,
                                         filename=imagename)

        i2 = MockImageBlob.objects.get(idref=imagename)
        assert i2.exists()

        os.remove(i2._get_file())

        # Now this should fail 
        assert not i2.exists()                  

    def test_binary_storage_size(self):
        '''Test that we correctly implement the required 'size()' method for Django Storage'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        imagename = 'alice01a.gif'
        image = helper.get_file(imagename)
        [i.delete() for i in MockImageBlob.objects.filter(idref=imagename)]
        image_obj = MockImageFile.objects.create(idref=imagename,
                                                 archive=document)
        i = MockImageBlob.objects.create(archive=document,
                                         idref=imagename,
                                         image=image_obj,
                                         data=image,
                                         filename=imagename)

        i2 = MockImageBlob.objects.get(idref=imagename)
        assert i2.size() == os.path.getsize(helper.get_filepath(imagename))

    def test_binary_storage_url(self):
        '''Test that we correctly implement the required 'url()' method for Django Storage'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        imagename = 'alice01a.gif'
        image = helper.get_file(imagename)
        [i.delete() for i in MockImageBlob.objects.filter(idref=imagename)]
        image_obj = MockImageFile.objects.create(idref=imagename,
                                                 archive=document)
        i = MockImageBlob.objects.create(archive=document,
                                         idref=imagename,
                                         image=image_obj,
                                         data=image,
                                         filename=imagename)

        i2 = MockImageBlob.objects.get(idref=imagename)
        assert image_obj.get_absolute_url() == i2.url()
        assert '/view/Pride+and+Prejudice/' in i2.url()
        assert 'alice01a.gif' in i2.url()

    def test_binary_storage_open(self):
        '''Test that we correctly implement the required 'open()' method for Django Storage'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        imagename = 'alice01a.gif'
        image = helper.get_file(imagename)
        [i.delete() for i in MockImageBlob.objects.filter(idref=imagename)]
        image_obj = MockImageFile.objects.create(idref=imagename,
                                                 archive=document)
        i = MockImageBlob.objects.create(archive=document,
                                         idref=imagename,
                                         image=image_obj,
                                         data=image,
                                         filename=imagename)

        i2 = MockImageBlob.objects.get(idref=imagename)
        assert i2.open().read() == helper.get_filehandle(imagename).read()

    def test_binary_image_autosave(self):
        '''Test that an ImageFile creates a blob and can retrieve it'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        imagename = 'alice01a.gif'

        for i in MockImageFile.objects.filter(idref=imagename):
            i.delete()
        for i in MockImageBlob.objects.filter(idref=imagename):
            i.delete()

        image = helper.get_file(imagename)
        image_obj = MockImageFile.objects.create(idref=imagename,
                                                 archive=document,
                                                 data=image)
        i = MockImageBlob.objects.create(archive=document,
                                         idref=imagename,
                                         image=image_obj,
                                         data=image,
                                         filename=imagename)
        i2 = MockImageBlob.objects.get(idref=imagename)
        self.assertTrue(i2.get_data() is not None)
        self.assertEquals(image, i2.get_data())
        i2.delete()
        
    def test_image_with_path_info(self):
        filename = 'alice-fromAdobe.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        
        i = MockImageFile.objects.filter(archive=document)[0]
        self.assertEquals(u'images', i.path)



    def test_binary_epub(self):
        '''Test the storage of an epub binary'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        epub = helper.get_file(filename)

        b2 = MockEpubBlob.objects.get(archive=document)

        self.assert_(b2.get_data())

        # Assert that we can read the file, and it's the same
        self.assertEquals(epub, b2.get_data())

        # Assert that it's physically in the storage directory
        storage = b2._get_file()
        self.assert_(os.path.exists(storage))        

        # Assert that once we've deleted it, it's gone
        b2.delete()
        self.assert_(not os.path.exists(storage))        

    def test_binary_deprecated(self):
        '''Force an old filesystem path and make sure it still works'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        epub = helper.get_file(filename)

        b2 = MockEpubBlob.objects.get(archive=document)

        self.assert_(b2.get_data())

        # Assert that we can read the file, and it's the same
        self.assertEquals(epub, b2.get_data())

        # Assert that it's physically in the storage directory
        storage = b2._get_file()
        self.assert_(os.path.exists(storage))        

        # Check that it's a new-style path
        assert '_' in storage 
        
        # Move the file out from under it to the old path
        paths = storage.split('/')
        assert '_' in paths[-3]

        new_storage = os.path.join('/'.join(paths[:-3]), paths[-2], paths[-1])
        os.makedirs(new_storage)
        
        b2._get_storage = lambda : new_storage

        shutil.move(storage, new_storage)
        # Now re-get the content and check that it's there
        self.assert_(b2.get_data())

        # Assert that we can read the file, and it's the same
        self.assertEquals(epub, b2.get_data())
        
                 

    def test_safe_deletion_when_epub_gone(self):
        '''If an epub binary is deleted, we should still allow deletion from the database'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        epub = helper.get_file(filename)

        b2 = MockEpubBlob.objects.filter(idref=filename)[0]        
        self.assert_(b2)
        b2.delete()
        try:
            document.delete()
        except InvalidBinaryException:
            pass
        
    def test_opf_file_in_subdir(self):
        '''A archive should be able to put its OPF file in a subdirectory and still locate the resources'''
        filename = 'opf-in-subdirectory.epub'
        document = self._create_document(filename)
        document.explode()
        document.save()
        self.assertEquals('OPF in subdir', document.title)

    def test_no_title_in_opf(self):
        '''Documents without titles should return a helpful error rather than crash'''
        filename = 'no-title.opf'
        document = MockEpubArchive(name=filename)
        opf = helper.get_file(filename)
        parsed_opf = util.xml_from_string(opf)
        try:
            document.get_title(parsed_opf)
        except InvalidEpubException:
            return
        raise Exception('Failed to get invalid epub exception for title')

    def test_blank_title_in_opf(self):
        '''Documents without titles should return a helpful error rather than crash'''
        filename = 'blank-title.opf'
        document = MockEpubArchive(name=filename)
        opf = helper.get_file(filename)
        parsed_opf = util.xml_from_string(opf)
        try:
            document.get_title(parsed_opf)
        except InvalidEpubException:
            return
        raise Exception('Failed to get invalid epub exception for title')

    def test_itemref_points_nowhere_opf(self):
        '''It should be ignored if an itemref points to a non-existent item'''
        filename = 'itemref-points-nowhere.opf'
        document = MockEpubArchive(name=filename)
        opf = helper.get_file(filename)
        parsed_opf = util.xml_from_string(opf)
        self.assertEquals('Test', document.get_title(parsed_opf))

    def test_read_chapter(self):
      
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.user = self.user
        document.explode()
        document.save()
        id = document.id

        chapter = HTMLFile.objects.filter(archive=document)[0]
        chapter.render(user=self.user)

        document = EpubArchive.objects.get(id__exact=id)
        self.assertEquals(chapter, document.get_last_chapter_read(self.user))

        # Try rendering, then check that the last one is up-to-date
        chapter2 = HTMLFile.objects.filter(archive=document)[1]
        chapter2.render(user=self.user)

        document = EpubArchive.objects.get(id__exact=id)        
        self.assertEquals(chapter2, document.get_last_chapter_read(self.user))

    def test_allow_no_playorder_in_toc(self):
        '''Assert that if we have no playOrder we can fall back to document order'''
        filename = 'no-playorder.ncx'
        f = helper.get_file(filename)
        toc = TOC(f)
        point = toc.find_points()[0]
        self.assertEquals(1, point.order())
        point = toc.find_points()[1]
        self.assertEquals(4, point.order())

    def test_rights_document(self):
        '''Assert that we correctly recognize a rights-managed epub'''
        filename = 'invalid-rights-managed.epub'
        document = self._create_document(filename)
        document.user = self.user
        self.assertRaises(DRMEpubException, document.explode)


        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)
        document.user = self.user
        document.explode()

    def test_identifier_type(self):
        '''Test that we return the correct identifier type'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename, identifier='urn:isbn:9780596528102')
        self.assertEquals(document.identifier_type(), IDENTIFIER_ISBN)

        document = self._create_document(filename, identifier='9780061734335')
        self.assertEquals(document.identifier_type(), IDENTIFIER_ISBN_MAYBE)

        document = self._create_document(filename, identifier='urn:uuid:e100da66-666a-11dd-b455-001cc05a7670')
        self.assertEquals(document.identifier_type(), IDENTIFIER_UUID)

        document = self._create_document(filename, identifier='xyzzy')
        self.assertEquals(document.identifier_type(), IDENTIFIER_UNKNOWN)

        document = self._create_document(filename, identifier='http://www.snee.com/epub/pg23598')
        self.assertEquals(document.identifier_type(), IDENTIFIER_URL)

    def test_nonce(self):
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self._create_document(filename)        

        # If the document hasn't been updated, the nonce should be the same
        self.assertEquals(document._get_nonce(),document._get_nonce())
        n = document._get_nonce()
        document.last_nonce = datetime.datetime.now()
        document.save()

        # If it has been updated, then they should be different
        self.assertNotEquals(n,document._get_nonce())

        # Test the validation routine
        self.assertTrue(document.is_nonce_valid(document._get_nonce()))        


    def test_allow_missing_image(self):
        '''Don't complain if an image is declared in the OPF 
        but not actually in the epub'''
        filename = 'missing-image.epub'
        document = self._create_document(filename)
        document.explode()

    def test_allow_body_as_classname(self):
        '''Was erroneously changing all CSS classnames '.body' to '.div'''
        css = 'foo.body { color: black; } body { color: white; }'
        epub = MockEpubArchive(name='css')
        out = epub.parse_stylesheet(css) 
        self.assertTrue('#bw-book-content foo.body' in out)
        self.assertTrue('#bw-book-content div' in out)
        self.assertTrue('#bw-book-content body' not in out)


    def test_allow_duplicate_itemref(self):
        '''Don't create duplicate resource files if the OPF file happens to declare them multiple times'''
        document = self._create_document('duplicate-itemref.epub')
        document.explode()
        self.assertEquals(HTMLFile.objects.filter(archive=document,
                                                  filename='chapter-1.html').count(), 1)


    def test_ignore_srcless_images(self):
        '''Don't complain if the source includes an image that's missing a @src (wtf)'''
        f = HTMLFile()
        f._clean_xhtml(etree.fromstring('<img src="foo.jpg" />'))
        f._clean_xhtml(etree.fromstring('<img alt="I have no src" />'))
        
    def test_dc_description(self):
        '''Retrieve dc description field'''
        document = self._create_document('dc-description.epub')
        document.explode()
        self.assertEquals(document.get_description(),
                          'This is a description')
        

    def test_invalid_no_spine(self):
        '''Return a proper exception if this OPF has no spine (checked in model)'''
        document = self._create_document('invalid-no-spine.epub')
        self.assertRaises(InvalidEpubException, document.explode)


    def test_unsafe_javascript(self):
        '''Test that Javascript links are not preserved'''
        document = self._create_document('unsafe-javascript-link.epub')
        document.explode()
        c = HTMLFile.objects.get(archive=document,
                                 filename='chapter-1.html')
        assert 'javascript:' not in c.render()
        assert '<a href="#">' in c.render()
        assert not '<script>' in c.render()

    def _create_document(self, document, identifier='', user=None):
        epub = MockEpubArchive.objects.create(name=document)
        if not user:
            user = self.user
        epub.identifier = identifier
        epub.save()
        UserArchive.objects.get_or_create(archive=epub, user=user)
        epub.set_content(helper.get_file(document))
        return epub


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
        '''Index should now be accessible'''
        try:
            self.client.logout()
        except:
            pass
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'public.html')
        self._login()

    def test_login(self):
        self._login()
        response = self.client.get('/')
        self.assertRedirects(response, '/library/')
        response = self.client.get('/library/')
        self.assertTemplateUsed(response, 'index.html')
        self.assertContains(response, 'testuser')

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


    def test_content_visible(self):
        response = self._upload('Cory_Doctorow_-_Little_Brother.epub')
        response = self.client.get('/view/Little-Brother/1/main5.xml')
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
        fh = helper.get_filehandle('Pride-and-Prejudice_Jane-Austen.epub')
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
        fh = helper.get_filehandle('Pride-and-Prejudice_Jane-Austen.epub')
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
        self.assertContains(response, 'date added to your library')
        self.assertContains(response, 'descending')

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
        self.assertContains(response, 'book title')
        self.assertContains(response, 'alphabetically')
        self.assertContains(response, 'ascending')

        response = self.client.get('/page/1/order/orderable_author/dir/asc')
        self.assertContains(response, 'Page 1 of 2')
        self.assertContains(response, 'first author')
        self.assertContains(response, 'alphabetically')
        self.assertContains(response, 'ascending')

        response = self.client.get('/page/1/order/created_time/dir/desc')
        self.assertContains(response, 'Page 1 of 2')
        self.assertContains(response, 'date added')
        self.assertContains(response, 'by date')
        self.assertContains(response, 'descending')

        # Test that the next page preserves this and generates the right link
        response = self.client.get('/page/2/order/created_time/dir/desc')
        self.assertContains(response, 'Page 2 of 2')
        self.assertContains(response, 'date added')
        self.assertContains(response, 'by date')
        self.assertContains(response, 'descending')
        
        self.assertContains(response, '<a href="/page/1/order/created_time/dir/desc">← previous </a>')

        # Test that the prev page preserves this and generates the right link
        response = self.client.get('/page/1/order/created_time/dir/desc')
        self.assertContains(response, 'Page 1 of 2')
        self.assertContains(response, 'date added')
        self.assertContains(response, 'by date')
        self.assertContains(response, 'descending')
        
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

    def test_register_standard(self):
        '''Register a new account using a standard Django account'''
        response = self.client.post('/account/signup/', { 'username':'registertest',
                                                          'email':'registertest@example.com',
                                                          'password1':'registertest',
                                                          'password2':'registertest'})
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/library/')
        self.assertTemplateUsed(response, 'index.html')
        self.assertContains(response, 'registertest', status_code=200)

    def test_change_email(self):
        '''Change the email address in a standard Django account'''
        self.test_register_standard()
        response = self.client.post('/account/email/', { 'password':'registertest',
                                                         'email':'registertest2@example.com'})
        self.assertRedirects(response, '/account/profile/?msg=Email+changed.', 
                             status_code=302, 
                             target_status_code=200)           
        
        response = self.client.get('/account/profile/')
        self.assertContains(response, 'registertest2@example.com', status_code=200)

    def test_change_password(self):
        '''Change a standard Django account password'''
        self.test_register_standard()
        response = self.client.post('/account/password/', { 'oldpw':'registertest',
                                                            'password1':'registertest2',
                                                            'password2':'registertest2'})
        
        self.assertRedirects(response, '/account/profile/?msg=Password+changed.', 
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/library/')
        self.assertContains(response, 'registertest', status_code=200)
        self.client.logout()
        self.assertTrue(self.client.login(username='registertest', password='registertest2'))        
        self.client.logout()
        self.assertFalse(self.client.login(username='registertest', password='registertest'))        

    def test_change_name(self):
        '''Change a standard Django account fullname'''
        # Regression from http://code.google.com/p/threepress/issues/detail?id=132
        self.test_register_standard()
        response = self.client.post('/account/profile/', { 'fullname':'my new name' })
        self.assertNotContains(response, 'font_size')
        response = self.client.get('/library/')
        response = self.client.get('/account/profile/')
        self.assertContains(response, 'my new name', status_code=200)

    def test_delete_account(self):
        self.test_register_standard()
        response = self.client.post('/account/delete/', { 'password':'registertest',
                                                          'confirm':'checked'})
        
        self.assertRedirects(response, '/?msg=Your+account+has+been+deleted.',
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/account/profile/')
        self.assertRedirects(response, '/account/signin/?next=/account/profile/', 
                             status_code=302, 
                             target_status_code=200)   
        self.assertFalse(self.client.login(username='registertest', password='registertest'))                

    def test_uprofile_safes_language(self):
        uprofile = UserPref.objects.get(user=self.user)
        self.assertEqual(uprofile.language,'en')
        uprofile.open_to_last_chapter = True
        uprofile.language = 'en'
        self.assertEqual(uprofile.language,'en')
        uprofile.save()

        uprofile_ = UserPref.objects.get(user=self.user)
        self.assertEqual(uprofile_.language,'en')

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
        
    def test_search_form(self):
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)
        index.index()
        res = self.client.get('/search/', { 'q' : 'lizzy' })

        self.assertTemplateUsed(res, 'results.html')
        self.assertContains(res, 'Jane')
        res = self.client.get('/search/', { 'q' : 'lizzy',
                                            'page': '2'})
        self.assertTemplateUsed(res, 'results.html')
        self.assertContains(res, 'dearest')        

        # Test searching DTbook content
        name = 'hauy.epub'
        self._upload(name)
        index.index()
        res = self.client.get('/search/', { 'q' : 'modification'})
        self.assertTemplateUsed(res, 'results.html')
        self.assertContains(res, 'original')

    
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

    def test_download_size(self):
        '''Ensure that files are being downloaded that are larger than zero-byte'''
        self._upload(u'halála.epub')
        response = self.client.get('/download/epub/halála/1/')        
        self.assertEquals(response.status_code, 200)
        assert len(response.content) > 0

    def test_invalid_file_with_utf8(self):
        '''Exception was being thrown from error handling on non-ASCII data'''
        response = self._upload(u'invalid_天.epub')
        self.assertContains(response, 'problems')

    def test_invalid_iso88591(self):
        '''Exception was being thrown when Django attempted to encode this document as UTF8'''
        response = self._upload(u'invalid-iso88591.epub')
        self.assertContains(response, 'There was a problem related to the encoding of one of the documents in your ePub')

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


    def test_translation_de(self):
        '''Ensure that we're getting German content appropriately'''
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)
        response = self.client.get('/library/')        
        self.assertContains(response, 'Signed in')

        response = self.client.post('/i18n/setlang/',
                                    { 'language':'de'})
        response = self.client.get('/library/')        
        self.assertContains(response, 'Angemeldet als')        

        response = self.client.post('/i18n/setlang/',
                                    { 'language':'en'})       

    def disabled_test_translation_da(self):
        '''Ensure that we're getting Danish content appropriately'''
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)
        response = self.client.get('/library/')        
        self.assertContains(response, 'Signed in')

        response = self.client.post('/i18n/setlang/',
                                    { 'language':'da'})
        response = self.client.get('/library/')        
        self.assertContains(response, 'Onlinelæsning af ePub-ebøger')        

        response = self.client.post('/i18n/setlang/',
                                    { 'language':'en'})       


    def test_view_with_multiple_dates(self):
        '''Was returning 'Unknown' rather than displaying a date.  Ultimately should
        be able to handle all dates and provide appropriate opf:event information.'''
        name = 'multiple-dc-dates.epub'
        self._upload(name)
        response = self.client.get('/metadata/test/1/')        
        self.assertNotContains(response, 'Unknown')
        self.assertContains(response, '01') # should be January but Python inanely doesn't handle <1900 dates
        self.assertContains(response, '1888')
        
    def test_switch_reading_mode(self):
        '''Allow users to toggle between simple and default reading modes'''
        name = 'Pride-and-Prejudice_Jane-Austen.epub'
        self._upload(name)
        response = self.client.get('/library/')
        self.assertEquals(False, self.user.get_profile().simple_reading_mode)

        response = self.client.post('/account/profile/toggle-reading-mode/')
        self.assertRedirects(response, '/library/')

        self.assertEquals(True, UserPref.objects.get(user=self.user).simple_reading_mode)        

        # Look for the appropriate css
        response = self.client.get('/view/test/1/')
        self.assertContains(response, 'simple.css')

        response = self.client.post('/account/profile/toggle-reading-mode/')
        self.assertRedirects(response, '/library/')
        self.assertEquals(False, UserPref.objects.get(user=self.user).simple_reading_mode)        

        # Now the CSS should be gone
        response = self.client.get('/view/test/1/')
        self.assertNotContains(response, 'simple.css')

        # Nothing should happen if we used GET
        response = self.client.get('/account/profile/toggle-reading-mode/')
        self.assertRedirects(response, '/library/')
        self.assertEquals(False, UserPref.objects.get(user=self.user).simple_reading_mode)        

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

    def test_style_in_subdir(self):
        '''Relative paths should be allowed when comparing CSS references in XHTML files and declarations in the OPF'''
        name ='css-in-subdir.epub'
        self._upload(name)
        assert StylesheetFile.objects.count() == 1

        response = self.client.get('/view/a/1/')

        # The style file should be present
        assert 'stylesheet.css' in response.content
        
        # Now we should have some
        assert HTMLFile.objects.filter(filename='text/chapter-1.html')[0].stylesheets.count() == 1


    def test_style_media_type(self):
        '''CSS files with media types explicitly set as non-screen should be ignored'''
        name ='non-screen-css.epub'
        self._upload(name)

        response = self.client.get('/view/a/1/')
        assert 'It is a truth' in response.content
        
        # The style file should be present
        assert 'book-screen.css' in response.content
        assert not 'book-print.css' in response.content
        assert 'book-no-media.css' in response.content
        assert StylesheetFile.objects.count() == 3 # All stylesheets are in the DB
        assert HTMLFile.objects.get(id=1).stylesheets.all().count() == 2 # But only two are associated with this doc

    def test_link_not_style(self):
        '''Don't display <link>s that aren't actually CSS files (@rel="stylesheet")'''
        name ='non-screen-css.epub'
        self._upload(name)

        response = self.client.get('/view/a/1/')

        # The style file should be present
        assert 'book-screen.css' in response.content
        # The random link shouldn't be
        assert not 'somewhere' in response.content


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
        '''Test trying to acquire an ePub by URL'''
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
        '''Test that we get a list of Feedbooks books from the main page'''
        self._login()
        response = self.client.get('/library/')
        assert 'feedbooks.com/book' in response.content
 
    def test_limit_css_files(self):
        '''The site should display no more than settings.MAX_CSS_FILES in a book'''
        self._login()
        self._upload('too-many-styles.epub')
        response = self.client.get('/view/test/1/')
        assert 'style1.css' in response.content
        assert 'style2.css' in response.content
        assert not 'style11.css' in response.content
        assert not 'style20.css' in response.content

    def test_space_in_filenames(self):
        '''The site should allow epub files whose internal resources have spaces in their filenames'''
        self._login()
        self._upload('space-in-filenames.epub')
        response = self.client.get('/view/test/1/')
        assert response.status_code == 200
        assert 'wife' in response.content

    def test_deploy_static_files(self):
        '''Static files should be deployed using the MEDIA_URL variable rather than a hardcoded path -- this test will fail if not using test_settings.py'''

        # test_settings.py uses the test-static variable to ensure we're getting the real thing.
        response = self.client.get('/test-static/about.css')
        assert response.status_code == 200

        response = self.client.get('/test-static/bookworm.js')
        assert response.status_code == 200

        response = self.client.get('/static/about.css')
        assert response.status_code != 200

        # Django will actually try to redirect here
        response = self.client.get('/static/about.css/')
        assert response.status_code == 404


    def test_flash_video(self):
        '''Flash video should be supported'''
        self._login()
        self._upload('flash-video.epub')
        response = self.client.get('/view/test/1/')
        assert response.status_code == 200
        assert 'object' in response.content
        response = self.client.get('/view/test/1/Creative_Commons_-_Get_Creative.swf')
        assert response.status_code == 200


    def test_html5_video(self):
        '''HTML5 video should be supported with the proper fallback'''
        self._login()
        self._upload('video.epub')
        response = self.client.get('/view/test/1/video.html')
        assert response.status_code == 200
        assert '<video' in response.content
        response = self.client.get('/view/test/1/20143.mp4')
        assert response.status_code == 200

        response = self.client.get('/view/test/1/20143.ogv')
        assert response.status_code == 200

    def test_zero_length_images(self):
        '''Images that are zero-length should be gracefully handled with 404 rather than 500 errors'''
        name ='zero-length-images.epub'
        self._upload(name)

        response = self.client.get('/view/a/1/test.jpg')
        assert response.status_code != 500
        assert response.status_code == 302 # Should be 404 but will auto-redirect

    def test_duplicate_css_in_opf(self):
        '''Declaring the same CSS multiple times in the OPF file should result in only one item'''
        name = 'duplicate-css-in-opf.epub'
        self._upload(name)        
        response = self.client.get('/view/a/1/')
        assert response.status_code == 200

        response = self.client.get('/css/a/1/stylesheet.css')
        assert 'sans-serif' in response.content
        
    def _login(self):
        self.assertTrue(self.client.login(username='testuser', password='testuser'))
        
    def _upload(self, f):
        self._login()
        fh = helper.get_filehandle(f)
        response = self.client.post('/upload/', {'epub':fh})
        return response


class TestTwill(DjangoTestCase):
    def setUp(self):
        os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
        
        from django.core.servers.basehttp import AdminMediaHandler
        from django.core.handlers.wsgi import WSGIHandler

        app = AdminMediaHandler(WSGIHandler())
        add_wsgi_intercept("127.0.0.1", 9876, lambda: app)
        self.b = get_browser()
        self.url = 'http://127.0.0.1:9876'

    def test_home(self):
        go(self.url)
        url('/')
        find('Bookworm')

    def test_library(self):
        go(self.url)
        url('/')
        self._register()
        find('Library')
        go('/account/signout/')

    def test_upload(self):
        self._register()
        go(self.url)
        formfile("upload", "epub", helper.get_filepath('Pride-and-Prejudice_Jane-Austen.epub'))
        submit("submit-upload")
        find('Pride and Prejudice')
        go('/account/signout/')


    def test_slash_in_title(self):
        '''Books with slashes in the title should not cause an error (must be done in twill)'''
        self._register()
        go(self.url)
        formfile("upload", "epub", helper.get_filepath('slash-in-title.epub'))
        submit("submit-upload")
        follow('Slash/In/Title')
        code(200)

    def _login(self):
        go('/account/signin/')
        fv("fauth", "username", "twilltest")
        fv("fauth", "password", "twill")
        submit()


    def _register(self):
        go(self.url)
        follow('register')

        url('signup')
        fv("2", "username", "twilltest")
        fv("2", "email", "twilltest@example.com")
        fv("2", "password1", "twill")
        fv("2", "password2", "twill")
        submit("register_local")
        url("/")
        find("twilltest")
        
    def tearDown(self):
        pass


if __name__ == '__main__':
    logging.error('Invoke this using "manage.py test"')
