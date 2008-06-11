# -*- coding: utf-8 -*-
from google.appengine.ext import db

from xml.etree import ElementTree
from zipfile import ZipFile
from StringIO import StringIO
import logging, datetime, sys
from urllib import quote_plus, unquote_plus

from django.utils.encoding import iri_to_uri
from django.utils.http import urlquote, urlquote_plus

from epub import constants, InvalidEpubException
logging.basicConfig(level=logging.DEBUG)

# Functions
def safe_name(name):
    #quote = quote_plus(name.encode('utf-8'))
    quote = urlquote_plus(name.encode('utf-8'))
    return quote

def unsafe_name(name):
    unquote = unquote_plus(name.encode('utf8'))
    return unicode(unquote, 'utf-8')

class BookwormModel(db.Model):
    created_time = db.DateTimeProperty(default=datetime.datetime.now())

class EpubArchive(BookwormModel):
    '''Represents an entire epub container'''

    _CONTAINER = constants.CONTAINER     

    _content_path = constants.CONTENT_PATH 
    _archive = None

    name = db.StringProperty(required=True)
    title = db.StringProperty()
    author = db.StringProperty()
    content = db.BlobProperty()
    toc = db.TextProperty()
    opf = db.TextProperty()
    container = db.TextProperty()
    owner = db.UserProperty()
    has_stylesheets = db.BooleanProperty(default=False)
    has_svg = db.BooleanProperty(default=False)


    def explode(self):
        '''Explodes an epub archive'''
        e = StringIO(self.content)
        z = ZipFile(e)

        logging.info(z.namelist())
        self._archive = z

        try:
            self.container = z.read(self._CONTAINER)
        except KeyError:
            raise InvalidEpubException()

        self.opf = unicode(z.read(self._get_opf()), 'utf-8')

        parsed_opf = ElementTree.fromstring(self.opf.encode('utf-8'))

        items = parsed_opf.getiterator("{%s}item" % (constants.NAMESPACES['opf']))

        self.toc = unicode(z.read(self._get_toc(items)), 'utf-8')

        parsed_toc = ElementTree.fromstring(self.toc.encode('utf-8'))

        self.author = self._get_author(parsed_opf)
        self.title = self._get_title(parsed_opf)

        self._get_content(parsed_opf, parsed_toc, items)
        self._get_stylesheets(items)
        self._get_images(items)

    def _get_opf(self):
        '''Parse the container to get the name of the opf file'''
        xml = ElementTree.fromstring(self.container)
        opf_filename = xml.find('.//{%s}rootfile' % constants.NAMESPACES['container']).get('full-path')
        paths = opf_filename.split('/')
        if len(paths) == 1:
            # We have no extra path info; this document's content is at the root
            self._content_path = ''
        else:
            self._content_path = paths[0] + '/'

        logging.info('Got content path as %s' % self._content_path)
        logging.info("Got opf filename as %s" % opf_filename)
        return opf_filename
 
    def _get_toc(self, items):
        '''Parse the opf file to get the name of the TOC'''
        for item in items:
            if item.get('id') == 'ncx':
                toc_filename = item.get('href').strip()
                logging.debug('Got toc filename as %s' % toc_filename)
                return "%s%s" % (self._content_path, toc_filename)
        raise Exception("Could not find toc filename")

    def _get_author(self, xml):
        author = xml.findtext('.//{%s}creator' % constants.NAMESPACES['dc']).strip()
        logging.info('Got author as %s with type %s' % (author, type(author)))
        return author

    def _get_title(self, xml):
        title = xml.findtext('.//{%s}title' % constants.NAMESPACES['dc']).strip()
        logging.info('Got title as %s with type %s' % (title, type(title) ))
        return title

    def _get_images(self, items):
        '''Images might be in a variety of formats, from JPEG to SVG.'''
        images = []
        for item in items:
            if 'image' in item.get('media-type'):
                
                content = self._archive.read("%s%s" % (self._content_path, item.get('href')))
                data = {}
                data['data'] = None
                data['file'] = None

                if item.get('media-type') == 'image/svg+xml':
                    logging.info('Adding image as SVG text type')
                    data['file'] = unicode(content, 'utf-8')
                    self.has_svg = True

                else:
                    # This is a binary file, like a jpeg
                    logging.info('Adding image as binary type')
                    data['data'] = content

                data['idref'] = item.get('href')
                data['content_type'] = item.get('media-type')

                images.append(data)

                logging.info('adding image %s ' % item.get('href'))

        db.run_in_transaction(self._create_images, images)                

    def _create_images(self, images):
        for i in images:
            image = ImageFile(parent=self,
                              idref=i['idref'],
                              data=i['data'],
                              file=i['file'],
                              content_type=i['content_type'],
                              archive=self)
            image.put()            

    def _get_stylesheets(self, items):
        stylesheets = []
        for item in items:
            if item.get('media-type') == constants.STYLESHEET_MIMETYPE:
                content = self._archive.read("%s%s" % (self._content_path, item.get('href')))
                stylesheets.append({'idref':item.get('href'),
                                    'file':unicode(content, 'utf-8')})


                logging.debug('adding stylesheet %s ' % item.get('href'))
                self.has_stylesheets = True
        db.run_in_transaction(self._create_stylesheets, stylesheets)


    def _create_stylesheets(self, stylesheets):
        for s in stylesheets:
            css = StylesheetFile(parent=self,
                                 idref=s['idref'],
                                 file=s['file'],
                                 archive=self)
            css.put()            
    def _get_content(self, opf, toc, items):
        # Get all the item references from the <spine>
        refs = opf.getiterator('{%s}itemref' % (constants.NAMESPACES['opf']) )
        navs = [n for n in toc.getiterator('{%s}navPoint' % (constants.NAMESPACES['ncx']))]
        navs2 = [n for n in toc.getiterator('{%s}navTarget' % (constants.NAMESPACES['ncx']))]
        navs = navs + navs2

        nav_map = {}
        item_map = {}
        
        depth = 1

        metas = toc.getiterator('{%s}meta' % (constants.NAMESPACES['ncx']))
      
        for m in metas:
            if m.get('name') == 'db:depth':
                depth = int(m.get('content'))
                logging.debug('Book has depth of %d' % depth)
        
        for item in items:
            item_map[item.get('id')] = item.get('href')
             
        for nav in navs:
            href = nav.find('.//{%s}content' % (constants.NAMESPACES['ncx'])).get('src')
            filename = href.split('#')[0]
            
            if nav_map.has_key(filename):
                pass
                # Skip this item so we don't overwrite with a new navpoint
            else:
                logging.info('adding filename %s to navmap' % filename)
                order = int(nav.get('playOrder')) 
                title = nav.findtext('.//{%s}text' % (constants.NAMESPACES['ncx'])).strip()
                nav_map[filename] = NavPoint(title, href, order, depth=depth)
        pages = []

        for ref in refs:
            idref = ref.get('idref')
            if item_map.has_key(idref):
                href = item_map[idref]
                logging.info("checking href %s" % href)
                if nav_map.has_key(href):
                    logging.info('Adding navmap item %s' % nav_map[href])
                    filename = '%s%s' % (self._content_path, href)
                    content = self._archive.read(filename)
                    
                    # We store the raw XHTML and will process it for display on request
                    # later
                    page = {'title': nav_map[href].title,
                            'idref':idref,
                            'file':unicode(content, 'utf-8'),
                            'archive':self,
                            'order':nav_map[href].order}
                    pages.append(page)
                    
        db.run_in_transaction(self._create_pages, pages)


    def _create_pages(self, pages):
        for p in pages:
            self._create_page(p['title'], p['idref'], p['file'], p['archive'], p['order'])

    def _create_page(self, title, idref, filename, archive, order):
        html = HTMLFile(parent=self, 
                        title=title.encode('utf-8'), 
                        idref=idref,
                        file=filename,
                        archive=archive,
                        order=order)
        html.put()

                  
    def safe_title(self):
        return safe_name(self.title)  
    def safe_author(self):
        return safe_name(self.author)


class NavPoint():
    '''Temporary storage object to hold an individual navpoint.  
    @todo Nest these
    '''
    def __init__(self, title, href, order, depth=1):
        self.title = title
        self.href = href
        self.order = order
        self.depth = depth
    def __repr__(self):
        return "%s (%s) %d" % (self.title, self.href, self.order)


class BookwormFile(BookwormModel):
    '''Abstract class that represents a file in the datastore'''
    idref = db.StringProperty()
    file = db.TextProperty()    
    archive = db.ReferenceProperty(EpubArchive)

    def render(self):
        return self.file

class HTMLFile(BookwormFile):
    '''Usually an individual page in the ebook'''
    title = db.StringProperty()
    order = db.IntegerProperty()
    processed_content = db.TextProperty()
    content_type = db.StringProperty(default="application/xhtml")

    def render(self):
        '''If we don't have any processed content, process it and cache the
        results in the datastore.'''
        #if self.processed_content:
        #    return self.processed_content

        logging.info('Parsing body content for first display')
        xhtml = ElementTree.fromstring(self.file.encode('utf-8'))
        body = xhtml.getiterator('{%s}body' % constants.NAMESPACES['html'])[0]
        body = self._clean_xhtml(body)
        body_content = ElementTree.tostring(body, 'utf-8')

        try:
            self.processed_content = unicode(body_content, 'utf-8')
            self.put()            
        except Exception:
            logging.error("Could not cache processed document, error was: " + sys.exc_info()[0])

        return body_content

    def _clean_xhtml(self, xhtml):
        '''This is only run the first time the user requests the HTML file; the processed HTML is then cached'''
        parent_map = dict((c, p) for p in xhtml.getiterator() for c in p)

        for element in xhtml.getiterator():
            element.tag = element.tag.replace('{%s}' % constants.NAMESPACES['html'], '')
            # if we have SVG, then we need to re-write the image links that contain svg in order to
            # make them work in most browsers
            if element.tag == 'img' and 'svg' in element.get('src'):
                logging.info('translating svg image %s' % element.get('src'))
                try:
                    p = parent_map[element]
                    logging.info("Got parent %s " % (p.tag)) 

                    e = ElementTree.fromstring("""
<a class="svg" href="%s">[ View linked image in SVG format ]</a>
""" % element.get('src'))
                    p.remove(element)
                    p.append(e)
                    logging.info("Added subelement %s to %s " % (e.tag, p.tag)) 
                except: 
                    logging.error("ERROR:" + sys.exc_info())[0]
        return xhtml

#<a href="img/butterfly_vector.svg">[<acronym>SVG</acronym> Image of a butterfly</a>] (Using the link to view the image requires a stand alone <acronym>SVG</acronym> viewer and your browser needs to be configured to use this player)
#</object>


            


class StylesheetFile(BookwormFile):
    '''A CSS stylesheet associated with a given book'''
    content_type = db.StringProperty(default="text/css")

class ImageFile(BookwormFile):
    '''An image file associated with a given book.  Mime-type will vary.'''
    content_type = db.StringProperty()
    data = db.BlobProperty()


class SystemInfo(BookwormModel):
    '''Random information about the status of the whole library'''
    total_books = db.IntegerProperty(default=0)
    total_users = db.IntegerProperty(default=0)

def get_system_info():
    '''There should only be one of these, so create it if it doesn't exists, 
    otherwise return get()'''
    instance = SystemInfo.all().get()
    if not instance:
        logging.info('Creating SystemInfo instance')
        instance = SystemInfo()
        instance.put()
    return instance

class UserPrefs(BookwormModel):
    '''Per-user preferences for this application'''
    user = db.UserProperty()
    use_iframe = db.BooleanProperty(default=False)
    show_iframe_note = db.BooleanProperty(default=True)
