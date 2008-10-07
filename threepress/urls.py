from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib.sitemaps import FlatPageSitemap
from threepress.search.threepress_sitemap import ThreepressSitemap
from django_restapi.resource import Resource
from threepress.search.epubcheck import validate
from django.http import HttpResponse

from django.contrib import admin

import sys

admin.autodiscover()


sitemaps = {
    'flatpages' : FlatPageSitemap,
    'documents': ThreepressSitemap,
}

urlpatterns = patterns('',

                       # Example:
                       # (r'^threepress/', include('threepress.foo.urls')),
                       
                       # Uncomment this for admin:
                       (r'^admin/(.*)',  admin.site.root),

                       # Sitemaps
                       (r'^sitemap.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),

                       # -----------Threepress
                       
                       (r'^document/epub-validate', 'threepress.search.views.epub_validate'),

                       # View an epub document (expanded epub)
                       (r'^epub/(?P<document_id>[^/]+)/$', 'threepress.search.views.document_epub'),

                       # View an epub document by ID + chapter
                       (r'^epub/(?P<document_id>.+)/(?P<chapter_id>.+)/$', 'threepress.search.views.document_chapter_epub'),

                       # View a document by ID only
                       (r'^document/(?P<document_id>[^/]+)/$', 'threepress.search.views.document_view'),

                       # View a document by ID + chapter
                       (r'^document/(?P<document_id>.+)/(?P<chapter_id>.+)/$', 'threepress.search.views.document_chapter_view'),

                       # Search within a document
                       (r'^search/(?P<document_id>.+)$', 'threepress.search.views.search'),

                       # Search across all documents
                       (r'^search/', 'threepress.search.views.search'),

                       # Index.html
                       (r'^$', 'threepress.search.views.index'), 

                       # ePub application
                       (r'^epub', include('threepress.epub.urls')),
)



# REST API for Epubcheck service
class Epubcheck(Resource):
    
    def create(self, request, *args, **kwargs):
        try:
            epub = request.raw_post_data
            validator = validate('temp.epub', epub)
            if validator.is_valid():
                msg = "<is-valid>True</is-valid>"
                errors = ""
            else:
                msg = "<is-valid>False</is-valid>"
                errors = "<errors>%s</errors>" % validator.xml_errors()
                
            xml = """<?xml version="1.0" encoding="utf-8" ?>
<rsp stat="ok">%s%s</rsp>
""" % (msg, errors)
        except:
            xml = """<?xml version="1.0" encoding="utf-8" ?>
<rsp stat="fail">
   <err code="500" msg="%s" />
</rsp>""" % sys.exc_info
        response = HttpResponse(content=xml, content_type='application/xml')
        return response

urlpatterns += patterns('',
                        url(r'^epubcheck-service/$', Epubcheck(permitted_methods=['POST'])),
)

if settings.DEBUG:
    urlpatterns += patterns('',
                            (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/liza/threepress/threepress/search/templates/static'}),
                            )
    
