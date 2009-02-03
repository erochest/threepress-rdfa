import logging

from lxml import etree
from lxml.html import soupparser

from django import template
log = logging.getLogger('library.templatetags')

register = template.Library()

@register.inclusion_tag('includes/result.html', takes_context=True)    
def display_result(context, htmlfile, search_term):
    '''Render a result with the matching context.'''
    context = result_fragment(htmlfile.processed_content, search_term)
    return {'result': htmlfile,
            'context':context }


def result_fragment(content, search_term):
    '''Primitive result context handler'''
    try:
        parsed_content = soupparser.fromstring(content)
        for p in parsed_content.iter(tag='p'):
            words = [w for w in ' '.join((w.lower() for w in p.xpath('text()'))).split(' ')]
            if search_term.lower() in words:
                return etree.tostring(p)
    except Exception, e:
        log.error(e)
