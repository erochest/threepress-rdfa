import logging
from datetime import datetime

from django import template
log = logging.getLogger('library.templatetags')

register = template.Library()

@register.inclusion_tag('render.html', takes_context=True)    
def render(context, chapter):
    '''Render the content of the current chapter, passing the current user.'''
    return {'content': chapter.render(user=context['user']) }

@register.inclusion_tag('last-read.html', takes_context=True)    
def last_chapter_read(context, document):
    '''Return a name and link to the last-read chapter for the current document 
    and user.'''
    chapter = document.get_last_chapter_read(user=context['user'])
    return { 'last_chapter_read':chapter,
             'document':document}


@register.inclusion_tag('reload.html', takes_context=True)
def show_reload(context, document, user):
    '''Is the user in the list of owners of this book?'''
    if user in document.get_owners():
        return { 'document':document }
    return {'document':None}

@register.simple_tag
def date_metadata(document, field):
    '''Try some common date formats to get display in a Bookworm-style date,
    otherwise give up.'''
    metadata = document._get_metadata(field, document.opf, as_list=True) 
    if not metadata:
        return 'Unknown'
    metadata = metadata[0]
    try:
        try:
            t = datetime.strptime(metadata, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                t = datetime.strptime(metadata, "%Y-%m-%d")            
            except ValueError, e:
                log.debug(e)
                return metadata
        try:
            return datetime.strftime(t, "%A, %B %d %Y")
        except ValueError, e:
            log.debug(e)
            return metadata
    except Exception, e:
        log.error(e)
        return "Unknown"

@register.simple_tag
def extra_metadata(document, field):
    '''Return any extra metadata with this field name.'''
    try:
        metadata = document._get_metadata(field, document.opf) 
        return metadata
    except:
        return ""

