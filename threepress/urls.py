from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib.sitemaps import FlatPageSitemap
from threepress.search.threepress_sitemap import ThreepressSitemap

sitemaps = {
    'flatpages' : FlatPageSitemap,
    'documents': ThreepressSitemap,
}



urlpatterns = patterns('',

                       # Example:
                       # (r'^threepress/', include('threepress.foo.urls')),
                       
                       # Uncomment this for admin:
                       (r'^admin/', include('django.contrib.admin.urls')),

                       # Sitemaps
                       (r'^sitemap.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),

                       # -----------Threepress

                       # View an epubx document (expanded epub)
                       (r'^document/(?P<document_id>[^\.]+)\.epubx$', 'threepress.search.views.document_epubx'),

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
)

if settings.DEBUG:
    urlpatterns += patterns('',
                            (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/liza/threepress/threepress/search/templates/static'}),
                            )
    
