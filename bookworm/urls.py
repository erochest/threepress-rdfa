from django.conf.urls.defaults import *
from django.contrib import admin

from django.conf import settings
from django.contrib.sitemaps import FlatPageSitemap

admin.autodiscover()

sitemaps = {
    'flatpages' : FlatPageSitemap,
}

urlpatterns = patterns('',

                       (r'^admin/(.*)',  admin.site.root),
                       ( r'^r/', include('django.conf.urls.shortcut')),
                       # Sitemaps
                       (r'^sitemap.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),

                       # Language setting
                       (r'^i18n/', include('django.conf.urls.i18n')),

                       # Auth
                       (r'^account/', include('django_authopenid.urls')),                       
                       
                       # Library
                       (r'^', include('bookworm.library.urls')),
                       
                       # Search 
                       (r'^search/', include('bookworm.search.urls')),


if settings.DEBUG:
    urlpatterns += patterns('',
                            (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/library/templates/static'}),
                            (r'(?P<path>sitedown.html)$', 'django.views.static.serve', 
                             {'document_root': settings.ROOT_PATH + '/library/templates/'}),
                            )
    
