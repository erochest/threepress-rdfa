from lxml import etree
import logging, urllib2
 
from django import template
import librarything 

log = logging.getLogger('librarything.templatetags.librarything')

register = template.Library()

@register.inclusion_tag('works.html', takes_context=True)
def works(context, document):
    '''Returns a list of candidate ISBNs for other works in this series'''
    works = librarything.get_isbns(document)
    return { 'works' : works,
             'document':document,
             'librarything_link': librarything.LINK_API}


