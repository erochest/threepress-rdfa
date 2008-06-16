import logging
from django.shortcuts import render_to_response

from models import EpubArchive

from views import _common

def search(request):
    common = _common(request, load_prefs=True)

    if request.GET.has_key('author') or request.GET.has_key('title'):
        d = EpubArchive.all()
        logging.debug('Performing search')
        if request.GET.has_key('author') and request.GET['author']:
            logging.info('including author %s' % request.GET['author'])
            d.filter('author = ', request.GET['author'])
        if request.GET.has_key('title') and request.GET['title']:
            logging.info('including title %s' % request.GET['title'])
            d.filter('title = ', request.GET['title'])
        return render_to_response('admin/search.html', { 'documents':d,
                                                         'show_owner':True,
                                                         'common':common })
    
    return render_to_response('admin/search.html', {'common':common })                               

            
