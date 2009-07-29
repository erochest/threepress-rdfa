import logging
import urllib2
from datetime import datetime
import gdata.client
from django import template
from django.conf import settings
  
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
        return { 'document':document,
                 'context': context }
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

@register.inclusion_tag('feedbooks.html', takes_context=True)
def feedbooks(context):
    # User's current lang
    lang = context['LANGUAGE_CODE'] or 'en'

    # Check with raw urllib2 if we'll get a response from this
    try:
        resp = urllib2.urlopen(settings.FEEDBOOKS_OPDS_FEED, None, 5)
    except urllib2.URLError:
        resp = None
    if resp:
        client = gdata.client.GDClient()
        fb = client.get_feed(uri='%s?lang=%s' % (settings.FEEDBOOKS_OPDS_FEED, lang))
        books = []
        for f in fb.entry:
            b = {}
            b['title'] = f.title.text
            b['author'] = f.author[0].name.text
            for l in f.link:
                if l.type == 'application/epub+zip':
                    b['link'] = l.href
            books.append(b)
    else:
        log.warn("Feedbooks timed out")
        books = None
    return { 'books': books }
    
