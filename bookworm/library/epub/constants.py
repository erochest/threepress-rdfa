'''Helpers or defaults for epub processing'''

MIMETYPE='application/epub+xml'
STYLESHEET_MIMETYPE='text/css'

NAMESPACES = { 'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
               'opf': 'http://www.idpf.org/2007/opf',
               'dc':'http://purl.org/dc/elements/1.1/',
               'ncx':'http://www.daisy.org/z3986/2005/ncx/',
               'html':'http://www.w3.org/1999/xhtml'}

CONTENT_PATH = 'OEBPS' # Default, may be overridden by container.xml
CONTAINER = 'META-INF/container.xml'
