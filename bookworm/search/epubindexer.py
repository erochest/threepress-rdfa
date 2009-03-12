from lxml.html.soupparser import fromstring
import logging
from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)
 
import bookworm.search.constants as constants

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('search.epubindexer')

   

def get_searchable_content(content):
    '''Returns the content of a chapter as a searchable field'''
    try:
        html = fromstring(content)
    except TypeError: # soupparser.py bug
        return None
    ns = get_namespace(content)
    headers = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
    if ns is not None:
        temp_para = [ p.xpath('.//text()') for p in html.iter(tag='{%s}p' % ns)]
        for h in headers:
            temp_para += [ p.xpath('.//text()') for p in html.iter(tag='{%s}%s' % (ns, h))]
    else:
        temp_para = [ p.xpath('.//text()') for p in html.iter(tag='p')]
        for h in headers:
            temp_para += [ p.xpath('.//text()') for p in html.iter(tag='%s' % h)]
    paragraphs = []
    for p in temp_para:
        if p is not None:
            paragraphs.append(' '.join([i.strip().replace('\n',' ') for i in p]))


    return '\n'.join(paragraphs)

def get_namespace(content):
    '''Determines whether this content has a namespace or not'''
    html = fromstring(content)
    if html.find('{%s}p' % constants.XHTML_NS) is not None:
        return constants.XHTML_NS
    return None
    
