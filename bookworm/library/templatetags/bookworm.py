import logging

from django import template

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

