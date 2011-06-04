from django.conf.urls.defaults import *
from django.contrib import admin

from django.conf import settings
from django.contrib.sitemaps import FlatPageSitemap

admin.autodiscover()

sitemaps = {
    'flatpages' : FlatPageSitemap,
}

urlpatterns = patterns('',

                       (r'^%sadmin/(.*)' % settings.BASE_URL, admin.site.urls),
                       (r'^%sr/' % settings.BASE_URL, include('django.conf.urls.shortcut')),

                       # Sitemaps
                       (r'^%ssitemap.xml$' % settings.BASE_URL, 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),

                       # Language setting
                       (r'^%si18n/' % settings.BASE_URL, include('django.conf.urls.i18n')),

                       # Auth
                       (r'^%saccount/' % settings.BASE_URL, include('django_authopenid.urls')),

                       # Library
                       (r'^%s' % settings.BASE_URL, include('bookworm.library.urls')),

                       # Search
                       (r'^%ssearch/' % settings.BASE_URL, include('bookworm.search.urls')),

                       # API
                       (r'^api/', include('bookworm.api.urls')),
)

if settings.DEBUG or settings.TESTING:
    urlpatterns += patterns('django.contrib.staticfiles.views',
            url('^%s(?P<path>.*)$' % (settings.MEDIA_URL[1:],), 'serve'),
            url('^orm-media/(?P<path>.*)$', 'serve'),
            url('(?P<path>sitedown.html)$', 'serve'),
            )

