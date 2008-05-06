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

                       # Threepress
                       (r'^document/(?P<id>[^/]+)/$', 'threepress.search.views.document_view'),
                       (r'^document/(?P<id>.+)/(?P<chapter_id>.+)/$', 'threepress.search.views.document_chapter_view'),


                       (r'^search/(?P<doc_id>.+)$', 'threepress.search.views.search'),
                       (r'^search/', 'threepress.search.views.search'),
                       (r'^$', 'threepress.search.views.index'), 
)

if settings.DEBUG:
    urlpatterns += patterns('',
                            (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/liza/threepress/threepress/search/templates/static'}),
                            )
    
