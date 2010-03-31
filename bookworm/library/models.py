# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import DjangoUnicodeDecodeError

from lxml import etree
import _mysql_exceptions, MySQLdb
from zipfile import ZipFile
from cStringIO import StringIO
import logging, datetime, os, os.path, hashlib, cssutils, uuid, lxml, lxml.html, shutil
from urllib import unquote_plus
from xml.parsers.expat import ExpatError

from django.utils.http import urlquote_plus
from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import smart_str
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.files.storage import Storage

from bookworm.library.epub import constants, InvalidEpubException
from bookworm.library.epub.constants import ENC, BW_BOOK_CLASS, STYLESHEET_MIMETYPE, XHTML_MIMETYPE, DTBOOK_MIMETYPE
from bookworm.library.epub.constants import NAMESPACES as NS
from bookworm.library.epub.toc import NavPoint, TOC
from bookworm.search import epubindexer
import bookworm.library.epub.toc as util

log = logging.getLogger('library.models')

# Functions
def safe_name(name):
    '''Return a name that can be used safely in a URL'''
    quote = urlquote_plus(name.encode(ENC).replace('/','_'))
    return quote
 
def get_file_by_item(item, document) :
    '''Accepts an Item and uses that to find the related file in the database'''
    if item.media_type == XHTML_MIMETYPE or item.media_type == DTBOOK_MIMETYPE or 'text' in item.media_type:
        # Allow semi-broken documents with media-type of 'text/html' or any text type
        # to be treated as html
        html = HTMLFile.objects.filter(idref=item.id, archive=document)
        if html is not None and len(html) > 0:
            return html[0]
    if item.media_type == STYLESHEET_MIMETYPE:
        css = StylesheetFile.objects.filter(idref=item.id, archive=document)
        if css is not None and len(css) > 0:
            return css[0]
    if 'image' in item.media_type or 'video' in item.media_type or 'flash' in item.media_type:
        image = ImageFile.objects.filter(idref=item.id, archive=document)
        if image is not None and len(image) > 0:
            return image[0]
    return None
    
class BookwormModel(models.Model):
    '''Base class for all models'''
    created_time = models.DateTimeField('date created', auto_now_add=True)
    last_modified_time = models.DateTimeField('last-modified', auto_now=True, default=datetime.datetime.now())

    class Meta:
        abstract = True

    def key(self):
        '''Backwards compatibility with templates'''
        return self.id

class EpubArchive(BookwormModel):
    '''Represents an entire epub container'''

    name = models.CharField(max_length=2000)
    authors = models.ManyToManyField('BookAuthor')
    orderable_author = models.CharField(max_length=1000, default='')

    title = models.CharField(max_length=5000, default='Untitled')
    opf = models.TextField()
    toc = models.TextField()
    has_stylesheets = models.BooleanField(default=False)

    # Deprecated
    last_chapter_read = models.ForeignKey('HTMLFile', null=True)
    owner = models.ForeignKey(User, null=True)

    # Is this book publicly-viewable?
    is_public = models.BooleanField(default=False)

    # Is this available in the public library?
    is_viewable = models.BooleanField(default=False)

    # Last time a nonce was generated
    last_nonce = models.DateTimeField('last-nonce', default=datetime.datetime.now())

    # Metadata fields
    language = models.CharField(max_length=255, default='', db_index=True)
    rights = models.CharField(max_length=300, default='', db_index=False)
    identifier = models.CharField(max_length=255, default='', db_index=True)

    # MTM fields
    subjects = models.ManyToManyField('Subject', default=None, null=True, blank=True)
    publishers = models.ManyToManyField('EpubPublisher', default=None, null=True, blank=True)

    _CONTAINER = constants.CONTAINER     
    _parsed_metadata = None
    _parsed_toc = None

    def __init__(self, *args, **kwargs):
        # If the filename itself has a path (this happens with Twill), just get its basename value
        if 'name' in kwargs:
            kwargs['name'] = os.path.basename(kwargs['name'])
        super(EpubArchive, self).__init__(*args, **kwargs)

    @property
    def publisher(self):
        '''Returns a displayable list of the publishers'''
        pubs = []
        for p in self.publishers.all():
            pubs.append(p.name)
        return ', '.join(pubs)

    def safe_title(self):
        '''Return a URL-safe title'''
        t = safe_name(self.title)  
        # Make sure this returns something, if even untitled
        if not t:
            t = _('Untitled')
        return t

    def safe_author(self):
        '''We only use the first author name for our unique identifier, which should be
        good enough for all but the oddest cases (revisions?)'''
        return self.author

    def get_content(self):
        '''Returns the data as a filehandle which must be read()'''
        blob = self._blob_class()
        epub = blob.objects.get(archive=self)
        return epub.get_data_handler()
  
    def delete(self):
        self.delete_from_filesystem()
        return super(EpubArchive, self).delete()

    def delete_from_filesystem(self):
        blob = self._blob_class()
        try:
            epub = blob.objects.get(archive=self)
            epub.delete()
        except blob.DoesNotExist:
            log.error('Could not find associated epubblob, maybe deleted from file system?')


    def set_content(self, c):
        if not self.id:
            raise InvalidEpubException('save() must be called before setting content')
        epub = self._blob_class()(archive=self,
                                 filename=self.name,
                                 data=c,
                                 idref=self.name)
        epub.save()

    @property
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

    def get_subjects(self):
        if self.subjects.count() > 0:
            return self.subjects
        added_subjects = False
        value = self._get_metadata(constants.DC_SUBJECT_TAG, self.opf, plural=True)
        if not value:
            return None
        for s in value:        
            is_lcsh = False
            if 'lcsh' or 'lcss' in s:
                s = s.replace('lcsh:', '').replace('lcsh', '').replace('lcc', '')
                is_lcsh=True
            subject = Subject.objects.get_or_create(name=s)[0]
            subject.is_lcsh=is_lcsh
            subject.save()
            self.subjects.add(subject)
            added_subjects = True
        if added_subjects:
            self.save()
            return self.subjects

    def get_rights(self):
        if self.rights != u'':
            return self.rights
        rights = self._get_metadata(constants.DC_RIGHTS_TAG, self.opf, as_string=True)
        if rights != u'':
            log.debug("Setting rights to %s" % rights)
            self.rights = rights
            self.save()
            return self.rights

    def get_language(self):
        if self.language != u'':
            return self.language
        self.language = self._get_metadata(constants.DC_LANGUAGE_TAG, self.opf, as_string=True)        
        if self.language != u'':
            log.debug("Setting language to %s" % self.language)
            self.save()
            return self.language


    def get_major_language(self):
        lang = self.get_language()
        if not lang:
            return None
        if '-' in lang or '_' in lang:
            for div in ('-', '_'):
                if div in lang:
                    return lang.split(div)[0]
        return lang

    def get_description(self):
        '''Return dc:description'''
        return self._get_metadata(constants.DC_DESCRIPTION_TAG, self.opf, as_string=True)        

    def get_publisher(self):
        if self.publishers.count() > 0:
            return self.publishers
        value = self._get_metadata(constants.DC_PUBLISHER_TAG, self.opf, plural=True)
        if not value:
            return None
        for s in value:
            publisher = EpubPublisher.objects.get_or_create(name=s)[0]
            publisher.save()
            self.publishers.add(publisher)
        log.debug("Setting publishers to %s" % value)
        self.save()
        return self.publishers

    def get_identifier(self):
        if self.identifier != u'':
            return self.identifier
        identifier = self._get_metadata(constants.DC_IDENTIFIER_TAG, self.opf, as_list=True)
        # There could be multiple identifiers.  We prefer IBSN or UUID,
        # but failing that, we'll use what's marked as the unique identifier
        if len(identifier) == 0:
            log.debug("No identifier present; generating one")
            self.identifier = 'urn:uuid:' + str(uuid.uuid4())

        elif len(identifier) > 1:
            # If we have multiple ones, try to ID them
            unique_identifier_tagname = self._parsed_metadata.xpath('//opf:package/@unique-identifier', namespaces={'opf':NS['opf']})[0]
            log.debug("Got unique identifier tagname as %s" % unique_identifier_tagname)
            for i in identifier:
                id_type = self._identifier_type(i)
                log.debug("Got ID type as %s for %s" % (id_type, i))
                if id_type == constants.IDENTIFIER_ISBN or id_type == constants.IDENTIFIER_ISBN_MAYBE:
                    # Append the URN bit if absent
                    try:
                        int(i)
                        i = 'urn:isbn:' + i
                    except ValueError:
                        pass
                    self.identifier = i
                elif id_type == constants.IDENTIFIER_UUID:
                    if not i.startswith('urn:uuid'):
                        i = 'urn:uuid' + i
                    self.identifier = i

            if not self.identifier and unique_identifier_tagname:
                self.identifier = self._parsed_metadata.xpath('//dc:identifier[@id="%s"]' % unique_identifier_tagname,
                                                              namespaces={'dc':NS['dc']})[0]
            if not self.identifier:                
                # If we failed at getting the matching ID, just pick the first one
                self.identifier = identifier[0]
        else:
            self.identifier = identifier[0]

        log.debug("Saving identifier as %s" % self.identifier)
        self.save()
        return self.identifier

    def _identifier_type(self, identifier):
        if 'isbn' in identifier.lower():
            return constants.IDENTIFIER_ISBN
        if 'uuid' in identifier.lower():
            return constants.IDENTIFIER_UUID
        if 'http' in identifier.lower():
            return constants.IDENTIFIER_URL
        if len(identifier) == 10 or len(identifier) == 13:
            try:
                int(identifier)
                return constants.IDENTIFIER_ISBN_MAYBE
            except ValueError:
                return constants.IDENTIFIER_UNKNOWN
        return constants.IDENTIFIER_UNKNOWN            

    def identifier_type(self):
        return self._identifier_type(self.identifier)


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

    @models.permalink
    def get_absolute_url(self):
        return ('view', (), { 'title':self.safe_title(), 'key': self.id } )
 
    @property
    def nonce_url(self):
        url =  reverse('download_epub_public', kwargs={
                'title': self.safe_title(),
                'key': self.id,
                'nonce': self._get_nonce()})
        return url

    def is_nonce_valid(self, nonce):
        valid = False
        if nonce is None:
            log.debug("Nonce is empty")
            return False
        valid = nonce == self._get_nonce()
        log.debug("new=%s, old=%s, Nonce is %s" % (nonce, self._get_nonce(), valid))
        # Update our timestamp
        self.last_nonce = datetime.datetime.now()
        self.save()
        return valid

    def is_owner(self, user):
        '''Is this user an owner of the book?'''
        return self.user_archive.filter(user=user,owner=True)

    def get_owners(self):
        '''Get a list of all owners of this book (usually just one)'''
        owners = {}
        for ua in self.user_archive.filter(owner=True):
            owners[ua.user.id] = ua.user
        return owners.values()
            

    def set_owner(self, user):
        '''Sets the ownership of ths book to a particular user'''
        for ua in self.user_archive.all():
            ua.user = user
            ua.owner = True
            ua.save()
        self.save()

    def get_last_chapter_read(self, user):
        '''Get the last chapter read by this user.'''
        ua = self.user_archive.filter(user=user, last_chapter_read__isnull=False).order_by('-id')
        if len(ua) > 0:
            return ua[0].last_chapter_read

    def explode(self):
        '''Explodes an epub archive'''
        z = ZipFile(self.get_content()) # Returns a filehandle
        try:
            container = z.read(self._CONTAINER)
        except KeyError:
            # Is this DOS-format?  If so, handle this as a special error
            try:
                container = z.read(self._CONTAINER.replace('/', '\\'))
                raise InvalidEpubException("This ePub file was created with DOS/Windows path separators, which is not legal according to the PKZIP specification.")
            except KeyError:
                raise InvalidEpubException('Was not able to locate container file %s' % self._CONTAINER, archive=self)
        
        try:
            z.read(constants.RIGHTS)
            raise DRMEpubException()
        except KeyError:
            pass

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


   
    def _get_nonce(self):
        m = hashlib.sha1()
        m.update(str(self.last_nonce) + settings.SECRET_KEY)
        return m.hexdigest()

 
    def _get_opf_filename(self, container):
        '''Parse the container to get the name of the opf file'''
        try:
            return container.find('.//{%s}rootfile' % NS['container']).get('full-path')
        except AttributeError:
            # We couldn't find the OPF, probably due to a malformed container file
            raise InvalidEpubException("Bookworm was unable to open this ePub. Check that your META-INF/container.xml file is correct, including XML namespaces")

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
        spine = opf.find('.//{%s}spine' % NS['opf'])
        if spine is None:
            raise InvalidEpubException("Could not find an opf:spine element in this document")
        tocid = spine.get('toc')

        if tocid:
            try:
                toc_filename = opf.xpath('//opf:item[@id="%s"]' % (tocid),
                                         namespaces={'opf':NS['opf']})[0].get('href')
            except IndexError:
                raise InvalidEpubException("Could not find an item matching %s in OPF <item> list" % (tocid), archive=self)
        else:
            # Find by media type
            log.warn("Did not have toc attribute on OPF spine; going to media-type")
            try:
                toc_filename = opf.xpath('//opf:item[@media-type="application/x-dtbncx+xml"]',
                                         namespaces={'opf': NS['opf']})[0].get('href')
            except IndexError:
                # Last ditch effort, find an href with the .ncx extension
                try:
                    toc_filename = opf.xpath('//opf:item[contains(@href, ".ncx")]',
                                             namespaces={'opf':NS['opf']})[0].get('href')
                except IndexError:
                    raise InvalidEpubException('Could not find any NCX file. EpubCheck 1.0.3 may erroneously report this as valid.', archive=self)
        return "%s%s" % (content_path, toc_filename)

    def _get_authors(self, opf):
        '''Retrieves a list of authors from the opf file, tagged as dc:creator.  It is acceptable
        to have no author or even an empty dc:creator'''
        authors = [BookAuthor.objects.create(name=a.text.strip()) for a in opf.findall('.//{%s}%s' % (NS['dc'], constants.DC_CREATOR_TAG)) if a is not None and a.text is not None]
        if len(authors) == 0:
            log.warn('Got empty authors string for book %s' % self.name)
        for a in authors:
            a.save()
        return authors

    def _get_title(self, xml):
        '''Retrieves the title from dc:title in the OPF'''
        title = xml.xpath('/opf:package/opf:metadata//dc:title/text()', namespaces={ 'opf': NS['opf'],
                                                                                    'dc': NS['dc']})
        if len(title) == 0:
            raise InvalidEpubException('This ePub document does not have a title.  According to the ePub specification, all documents must have a title.', archive=self)
        
        return title[0].strip()

    def _get_images(self, archive, items, content_path):
        '''Images might be in a variety of formats, from JPEG to SVG.  It may also be a video type, though hopefully the content creator included the required fallback.
        If they are SVG they need to be specially handled as a text type.'''
        images = []
        for item in items:
            if 'image' in item.get('media-type') or 'video' in item.get('media-type') or 'flash' in item.get('media-type'):

                href = unquote_plus(item.get('href'))
                
                try:
                    content = archive.read("%s%s" % (content_path, href))
                except KeyError:
                    log.warn("Missing image %s; skipping" % href)
                    continue
                data = {}
                data['data'] = None
                data['file'] = None
 
                if item.get('media-type') == constants.SVG_MIMETYPE:
                    data['file'] = unicode(content, ENC)

                else:
                    # This is a binary file, like a jpeg
                    data['data'] = content

                (data['path'], data['filename']) = os.path.split(href)
                log.debug('Got path=%s, filename=%s' % (data['path'], data['filename']))
                data['idref'] = item.get('id')
                data['content_type'] = item.get('media-type')

                images.append(data)

        self._create_images(images)                

    def _create_images(self, images):
        for i in images:
            f = i['file']
            if f == None:
                f = ''
            if self._image_class().objects.filter(filename=i['filename'],
                                                archive=self).count() > 0:
                log.warn("Already had an image for archive %s with filename %s; skipping" % (self.name, i['filename']))
                return
            image = self._image_class()(
                idref=i['idref'],
                file=f,
                filename=i['filename'],
                data=i['data'],
                path=i['path'],
                content_type=i['content_type'],
                archive=self)
            image.save() 
 
    def _image_class(self):
        return ImageFile

    def _get_stylesheets(self, archive, items, content_path):
        stylesheets = []
        stylesheet_count = 0
        for item in items:
            if stylesheet_count > settings.MAX_CSS_FILES:
                break
            if item.get('media-type') == constants.STYLESHEET_MIMETYPE:
                try:
                    content = archive.read("%s%s" % (content_path, item.get('href')))
                except KeyError:
                    log.warn("Could not find stylesheet %s; skipping " % item.get('href'))
                    continue
                parsed_content = self._parse_stylesheet(content)
                stylesheets.append({'idref':item.get('id'),
                                    'filename':item.get('href'),
                                    'file':unicode(parsed_content, ENC)})


                self.has_stylesheets = True
                stylesheet_count += 1
        self._create_stylesheets(stylesheets)

    def _parse_stylesheet(self, stylesheet):
        css = cssutils.parseString(stylesheet)
        for rule in css.cssRules:
            try:
                for selector in rule._selectorList:
                    # Change body rules but not if someone has specified it as a classname (there's
                    # probably a cleaner way to do this)
                    if 'body' in selector.selectorText and not '.body' in selector.selectorText:
                        # Replace the body tag with a generic div, so the rules
                        # apply even though we've stripped out <body>
                        selector.selectorText = selector.selectorText.replace('body', 'div')
                    selector.selectorText = BW_BOOK_CLASS + ' ' + selector.selectorText 
                    
            except AttributeError:
                pass # (was not a CSSStyleRule)
        return css.cssText

    def _create_stylesheets(self, stylesheets):
        for s in stylesheets:

            (css, created) = StylesheetFile.objects.get_or_create(
                filename=s['filename'],
                file=s['file'],
                archive=self)
            if created:
                css.idref = idref=s['idref']
                css.save()            

 
    def _get_content(self, archive, opf, toc, items, content_path):
        # Get all the item references from the <spine>
        refs = opf.getiterator('{%s}itemref' % (NS['opf']) )
        navs = [n for n in toc.getiterator('{%s}navPoint' % (NS['ncx']))]
        navs2 = [n for n in toc.getiterator('{%s}navTarget' % (NS['ncx']))]
        navs = navs + navs2

        nav_map = {}
        item_map = {}
      
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

        idrefs_already_processed = set()

        for ref in refs:
            idref = ref.get('idref')
            if idref in idrefs_already_processed:
                continue

            idrefs_already_processed.add(idref)
                
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
                        'path': os.path.split(title)[0],
                        'idref':idref,
                        'filename':href,
                        'file':content,
                        'archive':self,
                        'order':order}
                pages.append(page)

        self._create_pages(pages)


    def _create_pages(self, pages):
        for p in pages:
            #log.debug(p['filename'])
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
        try:
            html.save()
        except DjangoUnicodeDecodeError:
            raise InvalidEpubException(_("There was a problem related to the encoding of one of the documents in your ePub. All ePub documents must be in UTF-8."))
        except _mysql_exceptions.Warning:
            raise InvalidEpubException(_("There was a problem related to the encoding of one of the documents in your ePub. All ePub documents must be in UTF-8."))
        except MySQLdb.OperationalError, e:
            if 'Incorrect string value' in str(e):
                raise InvalidEpubException(_("There was a problem related to the encoding of one of the documents in your ePub. All ePub documents must be in UTF-8."))
            else:
                raise e

    def _get_metadata(self, metadata_tag, opf, plural=False, as_string=False, as_list=False):
        '''Returns a metdata item's text content by tag name, or a list if mulitple names match.
        If as_string is set to True, then always return a comma-delimited string.'''
        if self._parsed_metadata is None:
            try:
                self._parsed_metadata = util.xml_from_string(opf)
            except InvalidEpubException:
                return None
        text = []
        alltext = self._parsed_metadata.findall('.//{%s}%s' % (NS['dc'], metadata_tag))
        if as_list:
            return [t.text.strip() for t in alltext if t.text]
        if as_string:
            return ', '.join([t.text.strip() for t in alltext if t.text])
        for t in alltext:
            if t.text is not None:
                text.append(t.text)
        if len(text) == 1:
            t = (text[0], ) if plural else text[0]
            return t
        return text


    def _blob_class(self):
        return EpubBlob

    class Meta:
        ordering = ('-created_time', 'title')
        verbose_name_plural = 'ePub Archives'

    def __unicode__(self):
        return u'%s by %s (%s)' % (self.title, self.author, self.name)

class UserArchive(BookwormModel):
    '''Through class for user-epub relationships'''
    archive = models.ForeignKey(EpubArchive, related_name='user_archive')
    user = models.ForeignKey(User, related_name='user_archive')
    owner = models.BooleanField(default=True, help_text='Is this the owner of the book?')
    last_chapter_read = models.ForeignKey('HTMLFile', null=True)

    def __unicode__(self):
        return u'%s for %s' % (self.archive.title, self.user.username)

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
    path = models.CharField(max_length=255, default='')

    def render(self, user=None):
        return self.file

    class Meta:
        abstract = True

    def __unicode__(self):
        return u"%s [%s]" % (self.filename, self.archive.title)

class Subject(BookwormModel):
    '''Represents a DC:Subject value'''
    name = models.CharField(max_length=255, unique=True, default='', db_index=True)
    is_lcsh = models.BooleanField(default=False)
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ('name',)
        
class EpubPublisher(BookwormModel):
    '''Represents a publisher'''
    name = models.CharField(max_length=255, default='', db_index=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

class HTMLFileMeta(BookwormModel):
    '''Extra metadata about an HTML file.'''
    htmlfile = models.ForeignKey('HTMLFile')
    head_extra = models.TextField(null=True,
                                  help_text='Extra information from the document <head> which should be injected into the Bookworm page at rendering time')

class HTMLFile(BookwormFile):
    '''Usually an individual page in the ebook.'''
    title = models.CharField(max_length=5000,
                             help_text='The named title of the chapter or file')

    order = models.PositiveSmallIntegerField(default=1,
                                             help_text='The play order as derived from the NCX')

    stylesheets = models.ManyToManyField('StylesheetFile', blank=True, null=True)

    # XHTML content that has been sanitized.  This isn't done until
    # the user requests to access the file or until the automated
    # process hits it, whichever occurs first
    processed_content = models.TextField(null=True)

    # Only the words in the document; this is used for full-text indexing
    words = models.TextField(null=True) 

    content_type = models.CharField(max_length=100, default="application/xhtml")

    @models.permalink
    def get_absolute_url(self):
        return ('view_chapter', (), { 'title':self.archive.safe_title(), 'key': self.archive.id,
                                      'chapter_id': self.filename} )

    def render(self, user=None):
        '''If we don't have any processed content, process it and cache the
        results in the database.'''

        # Mark this chapter as last-read if a user is passed
        # (indexing will not create a last-read entry this way)
        if user and not user.is_anonymous():
            self.read(user)

        if self.processed_content:
            return self.processed_content
        
        f = smart_str(self.file, encoding=ENC)
        try:
            xhtml = etree.XML(f, etree.XMLParser())
            body = xhtml.find('{%s}body' % NS['html'])
            head = xhtml.find('{%s}head' % NS['html'])
            if body is None:
                body = xhtml.find('{%s}book' % NS['dtbook'])
                head = xhtml.find('{%s}head' % NS['dtbook'])
                # This is DTBook; process it
                body = self._process_dtbook(xhtml)
                if body is None:
                    raise UnknownContentException()
        except (ExpatError, etree.XMLSyntaxError, UnknownContentException):
            log.warn('Was not valid XHTML; trying with BeautifulSoup')
            try:
                html = lxml.html.soupparser.fromstring(f)
                body = html.find('.//body')
                head = html.find('.//head')
                if body is None:
                    raise 
            except:
                # Give up
                log.error("Giving up on this content")
                raise UnknownContentException()

        # Find any <style> blocks in the document <head> and add them
        if head is not None:
            styles = []

            for style in head.findall('.//style'):
                styles.append(style)

            for style in head.findall('.//{%s}style' % NS['html']):
                styles.append(style)

            head_extra = None
            for style in styles:
                if not head_extra:
                    head_extra = ''
                if style.text is not None:
                    head_extra += '\n' + self.archive._parse_stylesheet(style.text)
            
            if head_extra:
                head_extra = '<style type="text/css">%s</style>' % head_extra
                (meta, created) = HTMLFileMeta.objects.get_or_create(htmlfile=self)
                meta.head_extra = head_extra
                meta.save()

            # Find any CSS references in the <head> and link them to the StylesheetFiles 
            # identified from the OPF (ensure they are really stylesheets)
            links = []

            for link in head.findall('.//link[@rel="stylesheet"]'):
                links.append(link)

            for link in head.findall('.//{%s}link[@rel="stylesheet"]' % NS['html']):
                links.append(link)

            for link in links:
                if link.get('media') is None or (link.get('media') and link.get('media') == 'screen'):
                    css_basename = os.path.basename(link.get('href'))
                    css = StylesheetFile.objects.filter(archive=self.archive,
                                                    filename__icontains=css_basename)
                    # If the OPF was sloppy there may be dupes; just pick the first 
                    # (FIXME this won't work exactly right if there are multiple CSS files at different
                    # path levels with the sam name, but that seems extremely rare.)
                    if len(css) > 0:
                        self.stylesheets.add(css[0])
                    else:
                        log.warn("CSS %s was declared in the HTML but no matching StylesheetFile was found" % link.get('href'))
        else:
            log.warn("No <head> found; this could be a malformed document")
        body = self._clean_xhtml(body)
        div = etree.Element('div')
        div.attrib['id'] = 'bw-book-content'
        children = body.getchildren()
        for c in children:
            div.append(c)
        body_content = lxml.html.tostring(div, encoding=ENC, method="html")

        try:
            self.processed_content = body_content
            self.save()            
        except Exception, e: 
            log.error("Could not cache processed error was: %s, content was %s" % (e, body_content))

        return body_content

    def read(self, user):
        '''Create a new userarchive instance tracking this read, but only if this
        is the user's actual book and not a public one (otherwise it's effectively
        added to their library).'''
        if UserArchive.objects.filter(archive=self.archive,
                                      user=user,
                                      owner=True).count() > 0:
            log.debug("Updating last-read to %s for archive %s, user %s" % (self, self.archive, user))
            UserArchive.objects.create(archive=self.archive,
                                       user=user,
                                       owner=True,
                                       last_chapter_read=self)
        else:
            log.debug("Skipping creation of UserArchive object for book not owned by %s" % user)

    def _process_dtbook(self, xhtml):
        '''Turn DTBook content into XHTML'''
        xslt = etree.parse(settings.DTBOOK2XHTML)
        transform = etree.XSLT(xslt)
        result = transform(xhtml)
        # If the DTBook transform failed, throw an exception
        # and return to the standard XHTML pipeline
        if result is not None:
            try:
                body = result.getroot().find('{%s}body' % NS['html'])        
                if body is not None:
                    return body
            except AttributeError:
                pass
        log.warn("Got None from dtbook transform")

    def _clean_xhtml(self, xhtml):
        '''This is only run the first time the user requests the HTML file; the processed HTML is then cached'''
        ns = u'{%s}' % NS['html']
        nsl = len(ns)
        for element in xhtml.getiterator():
            if type(element.tag) == str and element.tag.startswith(ns):
                element.tag = element.tag[nsl:]
 
            # if we have SVG, then we need to re-write the image links that contain svg in order to
            # make them work in most browsers
            if element.tag == 'img' and element.get('src') is not None and 'svg' in element.get('src'):
                    p = element.getparent()         
                    e = etree.fromstring("""<a class="svg" href="%s">[ View linked image in SVG format ]</a>""" % element.get('src'))
                    p.remove(element)
                    p.append(e)
           
            # Script tags are removed
            if element.tag == 'script':
                p = element.getparent()
                p.remove(element)
            # So are links which have javascript: in them
            if element.get('href') and 'javascript:' in element.get('href'):
                element.set('href', '#')

        return xhtml

    _head_extra = None

    def head_extra(self):
        if not self._head_extra:
            try:
                self._head_extra = HTMLFileMeta.objects.get(htmlfile=self).head_extra
            except HTMLFileMeta.DoesNotExist:
                self._head_extra = ''
        return self._head_extra
        

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'HTML Files'

class StylesheetFile(BookwormFile):
    '''A CSS stylesheet associated with a given book'''
    content_type = models.CharField(max_length=100, default="text/css")

    @models.permalink
    def get_absolute_url(self):
        return ('view_stylesheet', (self.archive.safe_title(), self.archive.id, self.idref))

    class Meta:
        verbose_name_plural = 'CSS'

class ImageFile(BookwormFile):
    '''An image file associated with a given book.  Mime-type will vary.'''
    content_type = models.CharField(max_length=100)
    data = None

    @models.permalink
    def get_absolute_url(self):
        return ('view_chapter_image', ('view', self.archive.safe_title(), self.archive.id, self.idref))

    def __init__(self, *args, **kwargs):
        if kwargs.has_key('data'):
            self.data = kwargs['data']
            del kwargs['data']
        super(ImageFile, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        '''Overridden to also create a related binary image'''
        # Save first so we have an id
        super(ImageFile, self).save(*args, **kwargs)
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
    simple_reading_mode = models.BooleanField(default=False)
    font_size = models.CharField(max_length=10, default='1')
    font_family = models.CharField(max_length=20, blank=True)

    @property
    def username(self):
        return self.user.username

    def __unicode__(self):
        return self.user.username
    
    def get_api_key(self):
        from bookworm.api.models import APIKey
        return smart_str(APIKey.objects.get_or_create(user=self.user)[0].key, 'utf8')

class SystemInfo():
    '''This can now be computed at runtime (and cached)'''
    # @todo create methods for these
    def __init__(self):
        self._total_books = None
        self._total_users = None

    def get_total_books(self):
        '''If there are enough books, round the total so users don't
        have the expectation of this value incrementing constantly.'''
        self._total_books = EpubArchive.objects.count()
        if self._total_books > 100: 
            return int(round(self._total_books, -2))
        return self._total_books

    def get_total_users(self):
        '''If there are enough users, round the total so users don't
        have the expectation of this value incrementing constantly.'''
        self._total_users = User.objects.count()
        if self._total_users > 100:
            return int(round(self._total_users, -2))
        return self._total_users

class BinaryBlob(BookwormFile, Storage):
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

    def save(self, *args, **kwargs):
        if not os.path.exists(self._get_storage_dir()):
            os.mkdir(self._get_storage_dir())
        if not self.data:
            raise InvalidBinaryException('No data to save but save() operation called', archive=self.archive)
        if not self.filename:
            raise InvalidBinaryException('No filename but save() operation called', archive=self.archive)

        storage = self._get_storage()
  
        if not os.path.exists(storage):
            os.makedirs(storage)
        f = self._get_file()
        if os.path.exists(f.encode('utf8')):
            log.warn('File %s with document %s already exists; saving anyway' % (self.filename, self.archive.name))

        else :
            path = self.filename.encode('utf8')
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
        f = open(f.encode('utf8'), 'wb+')

        # Is this a file-like object or a string of bytes?
        if hasattr(self.data, 'read'):
            shutil.copyfileobj(self.data, f)
        else:
            f.write(self.data)
            f.close()
        super(BinaryBlob, self).save(*args, **kwargs)

    def open(self):
        '''Part of Django Storage API'''
        return open(self._get_file(), 'rb+')

    def delete(self):
        '''Per Django Storage API, does not raise an exception if the file is missing (but will warn)'''
        storage = self._get_storage()
        f = self._get_file()
        try:
            os.remove(f.encode('utf8'))
        except OSError:
            log.warn(u'Tried to delete non-existent file %s in %s' % (self.filename, storage))                         
        super(BinaryBlob, self).delete()
    
    def exists(self):
        '''Part of Django Storage API'''
        return os.path.exists(self._get_file())

    def size(self):
        '''Part of Django Storage API'''
        return os.path.getsize(self._get_file())

    def url(self):
        '''Part of Django Storage API'''
        raise Exception("Should be implemented by subclasses")

    def get_data(self):
        '''Return the data for this file, as a string of bytes (output from read())'''
        f = self._get_file()
        if not os.path.exists(f.encode('utf8')):
            log.warn(u"Tried to open file %s but it wasn't there (storage dir %s)" % (f, self._get_storage()))
            return None
        return open(f.encode('utf8'), 'rb+').read()

    def get_data_handler(self):
        '''Return the data for this file, as a filehandle'''
        f = self._get_file()
        if not os.path.exists(f.encode('utf8')):
            log.warn(u"Tried to open file %s but it wasn't there (storage dir %s)" % (f, self._get_storage()))
            return None
        return open(f.encode('utf8'), 'rb+')

    def _get_storage_dir(self):
        return settings.MEDIA_ROOT


    def _get_file(self):
        storage = self._get_storage()
        if not os.path.exists(storage):
            storage = self._get_storage_deprecated()
        return os.path.join(storage, self.filename)

    def _get_storage(self):
        '''Storage should be storage/top-level-dir/archive-id, where top-level-dir is the archive-id divided by 1,000'''
        top_dir = int(int(self.archive.id) / 1000)
        return os.path.join(self._get_storage_dir(), "_" + unicode(top_dir), unicode(self.archive.id))

    def _get_storage_deprecated(self):
        '''Original method of file retrieval: storage/archive-id'''
        return os.path.join(self._get_storage_dir(), unicode(self.archive.id))

    class Meta:
        abstract = True

class EpubBlob(BinaryBlob):
    '''Storage mechanism for an epub archive'''
    pass

class ImageBlob(BinaryBlob):
    '''Storage mechanism for a binary image'''
    image = models.ForeignKey(ImageFile)    
    
    def url(self):
        '''Return the computed URL for this image'''
        return self.image.get_absolute_url()

class InvalidBinaryException(InvalidEpubException):
    pass

class DRMEpubException(Exception):
    pass

class UnknownContentException(InvalidEpubException):
    # We weren't sure how to parse the body content here
    pass

order_fields = { 'title': _('book title'),
                 'orderable_author': _('first author'),
                 'created_time' : _('date added to your library') }

