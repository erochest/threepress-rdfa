# -*- coding: utf-8 -*-
from lxml import etree as ET
import lxml.html
from zipfile import ZipFile
from StringIO import StringIO
import logging, datetime, sys
from urllib import unquote_plus
import os, os.path
from xml.parsers.expat import ExpatError
import cssutils

from django.utils.http import urlquote_plus
from django.db import models
from django.db.models import permalink
from django.contrib.auth.models import User
from django.utils.encoding import smart_str

from epub import constants, InvalidEpubException
from epub.constants import ENC, BW_BOOK_CLASS, STYLESHEET_MIMETYPE, XHTML_MIMETYPE
from epub.constants import NAMESPACES as NS
from epub.toc import NavPoint, TOC
import epub.util as util


# Functions
def safe_name(name):
    '''Return a name that can be used safely in a URL'''
    quote = urlquote_plus(name.encode(ENC))
    return quote
 
def unsafe_name(name):
    '''Convert from a URL-formatted name to something that will match
    in the database'''
    unquote = unquote_plus(name.encode(ENC))
    return unicode(unquote, ENC)

def get_file_by_item(item, document) :
    '''Accepts an Item and uses that to find the related file in the database'''
    if item.media_type == XHTML_MIMETYPE or 'text' in item.media_type:
        # Allow semi-broken documents with media-type of 'text/html' or any text type
        # to be treated as html
        html = HTMLFile.objects.filter(idref=item.id, archive=document)
        if html is not None and len(html) > 0:
            return html[0]
    if item.media_type == STYLESHEET_MIMETYPE:
        css = StylesheetFile.objects.filter(idref=item.id, archive=document)
        if css is not None and len(css) > 0:
            return css[0]
    if 'image' in item.media_type:
        image = ImageFile.objects.filter(idref=item.id, archive=document)
        if image is not None and len(image) > 0:
            return image[0]
    return None
    
class BookwormModel(models.Model):
    '''Base class for all models'''
    created_time = models.DateTimeField('date created', default=datetime.datetime.now())

    def key(self):
        '''Backwards compatibility with templates'''
        return self.id

    class Meta:
        abstract = True

class EpubArchive(BookwormModel):
    '''Represents an entire epub container'''

    name = models.CharField(max_length=2000)
    owner = models.ForeignKey(User)
    authors = models.ManyToManyField('BookAuthor')
    orderable_author = models.CharField(max_length=1000, default='')

    title = models.CharField(max_length=5000, default='Untitled')
    opf = models.TextField()
    toc = models.TextField()
    has_stylesheets = models.BooleanField(default=False)
    last_chapter_read = models.ForeignKey('HTMLFile', null=True)

    _CONTAINER = constants.CONTAINER     
    _parsed_metadata = None
    _parsed_toc = None

    def __init__(self, *args, **kwargs):
        # If the filename itself has a path (this happens with Twill), just get its basename value
        if 'name' in kwargs:
            kwargs['name'] = os.path.basename(kwargs['name'])
        super(EpubArchive, self).__init__(*args, **kwargs)

    def safe_title(self):
        '''Return a URL-safe title'''
        t = safe_name(self.title)  
        # Make sure this returns something, if even untitled
        if not t:
            t = 'Untitled'
        return t

    def safe_author(self):
        '''We only use the first author name for our unique identifier, which should be
        good enough for all but the oddest cases (revisions?)'''
        return self.author()

    def get_content(self):
        blob = self._blob_class()
        epub = blob.objects.get(archive=self)
        return epub.get_data()

    def delete(self):
        blob = self._blob_class()
        try:
            epub = blob.objects.get(archive=self)
            epub.delete()
            super(EpubArchive, self).delete()
        except blob.DoesNotExist:
            logging.error('Could not find associated epubblob, maybe deleted from file system?')
            


    def set_content(self, c):
        if not self.id:
            raise InvalidEpubException('save() must be called before setting content')
        epub = self._blob_class()(archive=self,
                                 filename=self.name,
                                 data=c,
                                 idref=self.name)
        epub.save()

    def author(self):
        '''This method returns the author, if only one, or the first author in
        the list with ellipses for additional authors.'''

        if not self.authors:
            return None
        a = self.authors.all()
        if len(a) == 0:
            return ''
        if len(a) == 1:
            return a[0].name
        return a[0].name + '...'

    def _get_metadata(self, metadata_tag, opf):
        '''Returns a metdata item's text content by tag name, or a list if mulitple names match'''
        if self._parsed_metadata is None:
            self._parsed_metadata = util.xml_from_string(opf)
        text = []
        for t in self._parsed_metadata.findall('.//{%s}%s' % (NS['dc'], metadata_tag)):
            text.append(t.text)
        if len(text) == 1:
            return text[0]
        return text

    def get_subjects(self):
        return self._get_metadata(constants.DC_SUBJECT_TAG, self.opf)
    
    def get_rights(self):
        return self._get_metadata(constants.DC_RIGHTS_TAG, self.opf)

    def get_language(self):
        '''@todo expand into full form '''
        return self._get_metadata(constants.DC_LANGUAGE_TAG, self.opf)        

    def get_publisher(self):
        return self._get_metadata(constants.DC_PUBLISHER_TAG, self.opf)

    def get_top_level_toc(self):
        t = self.get_toc()
        p = t.find_points()
        if len(p) == 1:
            # If we only got one item try expanding the tree and dropping the first item
            p = t.find_points(maxdepth=2)
            if len(p) > 1:
                p = p[1:]
        return p
    
    def get_toc_items(self):
        t = self.get_toc()
        return t.items

    def get_toc(self):
        if not self._parsed_toc:
            self._parsed_toc = TOC(self.toc, self.opf)
        return self._parsed_toc
        
          
    def explode(self):
        '''Explodes an epub archive'''
        e = StringIO(self.get_content())
        z = ZipFile(e)

        try:
            container = z.read(self._CONTAINER)
        except KeyError:
            raise InvalidEpubException('Was not able to locate container file %s' % self._CONTAINER, archive=self)

        parsed_container = util.xml_from_string(container)

        opf_filename = self._get_opf_filename(parsed_container)

        content_path = self._get_content_path(opf_filename)
        self.opf = z.read(opf_filename)
        parsed_opf = util.xml_from_string(self.opf)

        items = [i for i in parsed_opf.iterdescendants(tag="{%s}item" % (NS['opf']))]
        
        toc_filename = self._get_toc(parsed_opf, items, content_path)
        try:
            self.toc = z.read(toc_filename)
        except KeyError:
            raise InvalidEpubException('TOC file was referenced in OPF, but not found in archive: toc file %s' % toc_filename, archive=self)

        parsed_toc = util.xml_from_string(self.toc)

        self.authors = self._get_authors(parsed_opf)
        self.orderable_author = self.safe_author()

        self.title = self._get_title(parsed_opf) 

        self._get_content(z, parsed_opf, parsed_toc, items, content_path)
        self._get_stylesheets(z, items, content_path)
        self._get_images(z, items, content_path)
   
 
    def _get_opf_filename(self, container):
        '''Parse the container to get the name of the opf file'''
        return container.find('.//{%s}rootfile' % NS['container']).get('full-path')

    def _get_content_path(self, opf_filename):
        '''Return the content path, which may be a named subdirectory or could be at the root of
        the archive'''
        paths = opf_filename.split('/')
        if len(paths) == 1:
            # We have no extra path info; this document's content is at the root
            return ''
        else:
            return '/'.join(paths[:-1]) + '/'
 
    def _get_toc(self, opf, items, content_path):
        '''Parse the opf file to get the name of the TOC
        (From OPF spec: The spine element must include the toc attribute, 
        whose value is the the id attribute value of the required NCX document 
        declared in manifest)'''
        tocid = opf.find('.//{%s}spine' % NS['opf']).get('toc')
        if not tocid:
            raise InvalidEpubException('Could not find toc attribute in OFP <spine>', archive=self)
        for item in items:
            if item.get('id') == tocid:
                toc_filename = item.get('href').strip()
                return "%s%s" % (content_path, toc_filename)
        raise InvalidEpubException("Could not find an item matching %s in OPF <item> list" % (tocid), archive=self)

    def _get_authors(self, opf):
        '''Retrieves a list of authors from the opf file, tagged as dc:creator.  It is acceptable
        to have no author or even an empty dc:creator'''
        authors = [BookAuthor(name=a.text.strip()) for a in opf.findall('.//{%s}%s' % (NS['dc'], constants.DC_CREATOR_TAG)) if a is not None and a.text is not None]
        if len(authors) == 0:
            logging.warn('Got empty authors string for book %s' % self.name)
        for a in authors:
            a.save()
        return authors

    def _get_title(self, xml):
        '''Retrieves the title from dc:title in the OPF'''
        title = xml.findtext('.//{%s}%s' % (NS['dc'], constants.DC_TITLE_TAG))
        if title is None:
            raise InvalidEpubException('This ePub document does not have a title.  According to the ePub specification, all documents must have a title.', archive=self)
        
        return title.strip()

    def _get_images(self, archive, items, content_path):
        '''Images might be in a variety of formats, from JPEG to SVG.  If they are
        SVG they need to be specially handled as a text type.'''
        images = []
        for item in items:
            if 'image' in item.get('media-type'):
                
                content = archive.read("%s%s" % (content_path, item.get('href')))
                data = {}
                data['data'] = None
                data['file'] = None
 
                if item.get('media-type') == constants.SVG_MIMETYPE:
                    data['file'] = unicode(content, ENC)

                else:
                    # This is a binary file, like a jpeg
                    data['data'] = content

                data['filename'] = item.get('href')
                data['idref'] = item.get('id')
                data['content_type'] = item.get('media-type')

                images.append(data)

        self._create_images(images)                

    def _create_images(self, images):
        for i in images:
            f = i['file']
            if f == None:
                f = ''
            image = self._image_class()(
                idref=i['idref'],
                file=f,
                filename=i['filename'],
                data=i['data'],
                content_type=i['content_type'],
                archive=self)
            image.save()  
    def _image_class(self):
        return ImageFile

    def _get_stylesheets(self, archive, items, content_path):
        stylesheets = []
        for item in items:
            if item.get('media-type') == constants.STYLESHEET_MIMETYPE:
                content = archive.read("%s%s" % (content_path, item.get('href')))
                parsed_content = self._parse_stylesheet(content)
                stylesheets.append({'idref':item.get('id'),
                                    'filename':item.get('href'),
                                    'file':unicode(parsed_content, ENC)})


                self.has_stylesheets = True
        self._create_stylesheets(stylesheets)

    def _parse_stylesheet(self, stylesheet):
        css = cssutils.parseString(stylesheet)
        for rule in css.cssRules:
            try:
                for selector in rule._selectorList:
                    if 'body' in selector.selectorText:
                        # Replace the body tag with a generic div, so the rules
                        # apply even though we've stripped out <body>
                        selector.selectorText = selector.selectorText.replace('body', 'div')
                    selector.selectorText = BW_BOOK_CLASS + ' ' + selector.selectorText 
                    
            except AttributeError:
                pass # (was not a CSSStyleRule)
        return css.cssText

    def _create_stylesheets(self, stylesheets):
        for s in stylesheets:
            css = StylesheetFile(
                                 idref=s['idref'],
                                 filename=s['filename'],
                                 file=s['file'],
                                 archive=self)
            css.save()            

 
    def _get_content(self, archive, opf, toc, items, content_path):
        # Get all the item references from the <spine>
        refs = opf.getiterator('{%s}itemref' % (NS['opf']) )
        navs = [n for n in toc.getiterator('{%s}navPoint' % (NS['ncx']))]
        navs2 = [n for n in toc.getiterator('{%s}navTarget' % (NS['ncx']))]
        navs = navs + navs2

        nav_map = {}
        item_map = {}
        metas = toc.getiterator('{%s}meta' % (NS['ncx']))
      
        for m in metas:
            if m.get('name') == 'db:depth':
                depth = int(m.get('content'))

        for item in items:
            item_map[item.get('id')] = item.get('href')
             
        for nav in navs:
            n = NavPoint(nav, doc_title=self.title)
            href = n.href()
            filename = href.split('#')[0]
            if nav_map.has_key(filename):
                pass
                # Skip this item so we don't overwrite with a new navpoint
            else:
                nav_map[filename] = n

        pages = []

        for ref in refs:
            idref = ref.get('idref')
            if item_map.has_key(idref):
                href = item_map[idref]
                filename = '%s%s' % (content_path, href)
                try:
                    content = archive.read(filename)
                except:
                    raise InvalidEpubException('Could not find file %s in archive even though it was listed in the OPF file' % filename,
                                               archive=self)
                    
                # We store the raw XHTML and will process it for display on request
                # later

                # If this item is in the navmap then we have a handy title
                if href in nav_map:
                    title = nav_map[href].title()
                    order = nav_map[href].order()
                else:
                    title = ""
                    order = 0

                page = {'title': title,
                        'idref':idref,
                        'filename':href,
                        'file':content,
                        'archive':self,
                        'order':order}
                pages.append(page)
                    
        self._create_pages(pages)


    def _create_pages(self, pages):
        for p in pages:
            self._create_page(p['title'], p['idref'], p['filename'], p['file'], p['archive'], p['order'])

    def _create_page(self, title, idref, filename, f, archive, order):
        '''Create an HTML page and associate it with the archive'''
        html = HTMLFile(
                        title=title, 
                        idref=idref,
                        filename=filename,
                        file=f,
                        archive=archive,
                        order=order)
        html.save()
        

    def _blob_class(self):
        return EpubBlob

    class Meta:
        ordering = ('-created_time', 'title')

    def __unicode__(self):
        return u'%s by %s (%s)' % (self.title, self.author(), self.name)


class BookAuthor(BookwormModel):
    '''Authors are not normalized as there is no way to guarantee uniqueness across names'''
    name = models.CharField(max_length=2000)
    def __unicode__(self):
        return self.name

class BookwormFile(BookwormModel):
    '''Abstract class that represents a file in the database'''
    idref = models.CharField(max_length=1000)
    file = models.TextField(default='')    
    filename = models.CharField(max_length=1000)
    archive = models.ForeignKey(EpubArchive)

    def render(self):
        return self.file
    class Meta:
        abstract = True
    def __unicode__(self):
        return u"%s [%s]" % (self.filename, self.archive.title)

class HTMLFile(BookwormFile):
    '''Usually an individual page in the ebook'''
    title = models.CharField(max_length=5000)
    order = models.PositiveSmallIntegerField(default=1)
    processed_content = models.TextField()
    content_type = models.CharField(max_length=100, default="application/xhtml")
    is_read = models.BooleanField(default=False)

    def render(self):
        '''If we don't have any processed content, process it and cache the
        results in the database.'''

        # Mark this chapter as last-read
        self.read()

        if self.processed_content:
            return self.processed_content
        
        f = smart_str(self.file, encoding=ENC)

        try:
            xhtml = ET.XML(f, ET.XMLParser())
            body = xhtml.find('{%s}body' % NS['html'])
        except ET.XMLSyntaxError:
            # Use the HTML parser
            xhtml = ET.parse(StringIO(f), ET.HTMLParser())
            body = xhtml.find('body')
        except ExpatError:
            logging.error('Was not valid XHTML; treating as uncleaned string')
            self.processed_content = f
            return f 


        body = self._clean_xhtml(body)
        div = ET.Element('div')
        div.attrib['id'] = 'bw-book-content'
        children = body.getchildren()
        for c in children:
            div.append(c)
        body_content = lxml.html.tostring(div, encoding=ENC, method="html")

        try:
            self.processed_content = body_content
            self.save()            
        except: 
            logging.error("Could not cache processed document, error was: " + sys.exc_value)

        # Mark this chapter as last-read


        return body_content

    def read(self):
        '''Mark this page as read by updated the related book object'''
        self.archive.last_chapter_read = self
        self.archive.save()
        self.is_read = True
        self.save()

    def _clean_xhtml(self, xhtml):
        '''This is only run the first time the user requests the HTML file; the processed HTML is then cached'''
        ns = u'{%s}' % NS['html']
        nsl = len(ns)
        for element in xhtml.getiterator():
            
            if type(element.tag) == str and element.tag.startswith(ns):
                element.tag = element.tag[nsl:]
 
            # if we have SVG, then we need to re-write the image links that contain svg in order to
            # make them work in most browsers
            if element.tag == 'img' and 'svg' in element.get('src'):
                p = element.getparent()         
                e = ET.fromstring("""<a class="svg" href="%s">[ View linked image in SVG format ]</a>""" % element.get('src'))
                p.remove(element)
                p.append(e)

        return xhtml



    class Meta:
        ordering = ['order']

class StylesheetFile(BookwormFile):
    '''A CSS stylesheet associated with a given book'''
    content_type = models.CharField(max_length=100, default="text/css")


class ImageFile(BookwormFile):
    '''An image file associated with a given book.  Mime-type will vary.'''
    content_type = models.CharField(max_length=100)
    data = None

    def __init__(self, *args, **kwargs):
        if kwargs.has_key('data'):
            self.data = kwargs['data']
            del kwargs['data']
        super(ImageFile, self).__init__(*args, **kwargs)

    def save(self):
        '''Overridden to also create a related binary image'''
        # Save first so we have an id
        super(ImageFile, self).save()
        if self.data:
            blob_class = self._blob_class()
            b = blob_class(archive=self.archive,
                           image=self,
                           data=self.data,
                           filename=self.idref)
            b.save()


    def get_data(self):
        b = self._blob()
        return b.get_data()

    def delete(self):
        b = self._blob()
        if b:
            b.delete()
        super(ImageFile, self).save()

    def _blob(self):
        '''Gets the blob related to this image'''
        try:
            b = self._blob_class().objects.filter(image=self)
            if len(b) == 0:
                return None
        except IndexError:
            # This error is odd; possibly in Django?
            return None
        return self._blob_class().objects.filter(image=self)[0]        

    def _blob_class(self):
        return ImageBlob


class UserPref(BookwormModel):
    '''Per-user preferences for this application'''
    user = models.ForeignKey(User, unique=True)
    fullname = models.CharField(max_length=1000, blank=True) # To ease OpenID integration
    country = models.CharField(max_length=100, blank=True) 
    language = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    nickname = models.CharField(max_length=500, blank=True)
    open_to_last_chapter = models.BooleanField(default=False)

    # Deprecated
    use_iframe = models.BooleanField(default=False)
    show_iframe_note = models.BooleanField(default=True)

class SystemInfo():
    '''This can now be computed at runtime (and cached)'''
    # @todo create methods for these
    def __init__(self):
        self._total_books = None
        self._total_users = None

    def get_total_books(self):
        self._total_books = EpubArchive.objects.count()
        return self._total_books

    def get_total_users(self):
        self._total_users = User.objects.count()
        return self._total_users

    def increment_total_books(self):
        t = self.get_total_books()
        self._total_books += 1

    def decrement_total_books(self):
        t = self.get_total_books()
        if t > 0:
            self._total_books += 1

    def increment_total_users(self):
        t = self.get_total_users()
        self._total_users += 1

    def decrement_total_users(self):
        t = self.get_total_users()
        if t > 0:
            self._total_users += 1


class BinaryBlob(BookwormFile):
    '''Django doesn't support this natively in the DB model (yet) and quite 
    probably we don't want to store this in the database anyway, for
    possible replacement with an S3-like storage system later.  For now
    this implementation is in the local filesystem.'''
    
    data = None

    def __init__(self, *args, **kwargs):
        if kwargs.has_key('data'):
            self.data = kwargs['data']
            del kwargs['data']

        super(BinaryBlob, self).__init__(*args, **kwargs)

    def save(self):
        if not os.path.exists(self._get_storage_dir()):
            os.mkdir(self._get_storage_dir())
        if not self.data:
            raise InvalidBinaryException('No data to save but save() operation called', archive=self.archive)
        if not self.filename:
            raise InvalidBinaryException('No filename but save() operation called', archive=self.archive)

        storage = self._get_storage()
  
        if not os.path.exists(storage):
            os.mkdir(storage)
        f = self._get_file()
        if os.path.exists(f):
            logging.warn('File %s with document %s already exists; saving anyway' % (self.filename, self.archive.name))

        else :
            path = self.filename
            pathinfo = []
            # This is ugly, but we want to create any depth of path,
            # and then save the file in the appropriate place
            while os.path.split(path)[1] != '':
                pathinfo.append(os.path.split(path)[1])
                path = os.path.split(path)[0]
            pathinfo.reverse()
            pathinfo = pathinfo[:-1]
            d = storage
            for p in pathinfo:
                d += '/' + p
                if not os.path.exists(d):
                    os.mkdir(d)
        f = open(f, 'w')
        f.write(self.data)
        f.close()
        super(BinaryBlob, self).save()

    def delete(self):
        storage = self._get_storage()
        f = self._get_file()
        if not os.path.exists(f):
            logging.warn('Tried to delete non-existent file %s in %s' % (self.filename, storage))         
        else:
            os.remove(f)
        super(BinaryBlob, self).delete()

    def get_data(self):
        '''Return the data for this file, as a string of bytes (output from read())'''
        f = self._get_file()
        if not os.path.exists(f):
            logging.warn("Tried to open file %s but it wasn't there (storage dir %s)" % (f, self._get_storage()))
            return None
        return open(f).read()

    def _get_pathname(self):
        return 'storage'

    def _get_storage_dir(self):
        return '%s/%s' % (os.path.dirname(__file__), self._get_pathname())   


    def _get_file(self):
        storage = self._get_storage()
        if not os.path.exists(storage):
            storage = self._get_storage_deprecated()
        return '%s/%s' % (storage, self.filename)

    def _get_storage(self):
        return '%s/%s' % (self._get_storage_dir(), self.archive.id)

    def _get_storage_deprecated(self):
        logging.warn('Using old method of file retrieval; this should be removed!')
        return '%s/%s' % (self._get_storage_dir(), self.archive.name)

    class Meta:
        abstract = True

class EpubBlob(BinaryBlob):
    '''Storage mechanism for an epub archive'''
    pass

class ImageBlob(BinaryBlob):
    '''Storage mechanism for a binary image'''
    image = models.ForeignKey(ImageFile)    
    
class InvalidBinaryException(InvalidEpubException):
    pass



order_fields = { 'title': 'book title',
                 'orderable_author': 'first author',
                 'created_time' : 'date added to your library' }
