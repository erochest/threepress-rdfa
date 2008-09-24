'''Helpers or defaults for epub processing'''
ENC = 'utf-8'

MIMETYPE='application/epub+zip'
STYLESHEET_MIMETYPE='text/css'
XHTML_MIMETYPE='application/xhtml+xml'
SVG_MIMETYPE='image/svg+xml'

NAMESPACES = { 'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
               'opf': 'http://www.idpf.org/2007/opf',
               'dc':'http://purl.org/dc/elements/1.1/',
               'ncx':'http://www.daisy.org/z3986/2005/ncx/',
               'html':'http://www.w3.org/1999/xhtml'}

CONTENT_PATH = 'OEBPS' # Default, may be overridden by container.xml
CONTAINER = 'META-INF/container.xml'

DC_TITLE_TAG = 'title'
DC_CREATOR_TAG = 'creator'
DC_LANGUAGE_TAG = 'language'
DC_RIGHTS_TAG = 'rights'
DC_SUBJECT_TAG = 'subject'
DC_PUBLISHER_TAG = 'publisher'
DC_IDENTIFIER_TAG = 'identifier'

BW_BOOK_CLASS = '#bw-book-content'
  
