from google.appengine.ext import db

from xml.etree import ElementTree
from zipfile import ZipFile
from StringIO import StringIO
import logging, datetime
from urllib import quote_plus, unquote_plus

from epub import constants


# Functions
def safe_name(name):
    return quote_plus(name)

def unsafe_name(name):
    return unquote_plus(name)

class BookwormModel(db.Model):
    created_time = db.DateTimeProperty(default=datetime.datetime.now())

class EpubArchive(BookwormModel):
    '''Represents an entire epub container'''

    _CONTAINER = constants.CONTAINER     
    _NSMAP = constants.NAMESPACES

    _content_path = constants.CONTENT_PATH 
    _archive = ''

    name = db.StringProperty(required=True)
    title = db.StringProperty()
    author = db.StringProperty()
    content = db.BlobProperty()
    toc = db.TextProperty()
    opf = db.TextProperty()
    container = db.TextProperty()
    owner = db.UserProperty()
    has_stylesheets = db.BooleanProperty(default=False)



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
        self._get_stylesheets(parsed_opf)

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

    def _get_stylesheets(self, opf):
        for item in opf.getiterator("{%s}item" % (self._NSMAP['opf'])):
            if item.get('media-type') == constants.STYLESHEET_MIMETYPE:
                content = self._archive.read("%s/%s" % (self._content_path, item.get('href')))
                css = StylesheetFile(idref=item.get('id'),
                                     file=unicode(content, 'utf-8'),
                                     archive=self)
                css.put()
                logging.info('adding stylesheet %s ' % item.get('href'))
                self.has_stylesheets = True
                
    def _get_content(self, opf, toc):
        # Get all the item references from the <spine>
        refs = opf.findall('.//{%s}spine/{%s}itemref' % (self._NSMAP['opf'], self._NSMAP['opf']) )
        navs = toc.findall('.//{%s}navPoint' % (self._NSMAP['ncx']))
        nav_map = {}
        item_map = {}
        
        depth = 1

        metas = toc.findall('.//{%s}meta' % (self._NSMAP['ncx']))
        for m in metas:
            if m.get('name') == 'db:depth':
                depth = int(m.get('content'))
                logging.info('Book has depth of %d' % depth)
        
        items = opf.findall(".//{%s}item" % (self._NSMAP['opf']))
        for item in items:
            item_map[item.get('id')] = item.get('href')


        for nav in navs:

            order = int(nav.get('playOrder')) 
            title = nav.findtext('.//{%s}text' % (self._NSMAP['ncx']))
            href = nav.find('.//{%s}content' % (self._NSMAP['ncx'])).get('src')
            filename = href.split('#')[0]
            logging.info('adding filename %s to navmap' % filename)
            if nav_map.has_key(filename):
                pass
                # Skip this item so we don't overwrite with a new navpoint
            else:
                nav_map[filename] = NavPoint(title, href, order, depth=depth)
        
        for ref in refs:
            idref = ref.get('idref')
            if item_map.has_key(idref):
                href = item_map[idref]
                logging.info("checking href %s" % href)
                if nav_map.has_key(href):
                    logging.info('Adding navmap item %s' % nav_map[href])
                    filename = '%s/%s' % (self._content_path, href)
                    content = self._archive.read(filename)

                    # Parse the content as XML to pull out just the body
                    xhtml = ElementTree.fromstring(content)
                    body = xhtml.find('.//{%s}body' % self._NSMAP['html'])
                    body = self._clean_xhtml(body)
                    body_content = ElementTree.tostring(body, 'utf-8')
                    html = HTMLFile(title=nav_map[href].title,
                                    idref=idref,
                                    file=unicode(body_content, 'utf-8'),
                                    archive=self,
                                    order=nav_map[href].order)
                    html.put()

    def _clean_xhtml(self, xhtml):
        for element in xhtml.getiterator():
            element.tag = element.tag.replace('{%s}' % self._NSMAP['html'], '')
        return xhtml
            
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

class StylesheetFile(BookwormFile):
    '''A CSS stylesheet associated with a given book'''
    pass


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
