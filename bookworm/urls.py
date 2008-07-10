
from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib.sitemaps import FlatPageSitemap
from django.contrib.auth.views import login, logout

sitemaps = {
    'flatpages' : FlatPageSitemap,
}

urlpatterns = patterns('',

                       # Uncomment this for admin:
                       (r'^admin/', include('django.contrib.admin.urls')),

                       # Sitemaps
                       (r'^sitemap.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
                       
                       # Auth
                       (r'^account/', include('django_authopenid.urls')),                       
                       
                       # Bookworm
                       (r'^$', 'library.views.index'),                        
                       
                       (r'^upload/$', 'library.views.upload'),

                       # Images from within documents
                       (r'^(view|chapter)/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<image>.*(jpg|gif|png|svg)+)$', 
                        'library.views.view_chapter_image'),                       
                       
                       # Document metadata
                       (r'^metadata/(?P<title>.+)/(?P<key>.+)/$', 'library.views.view_document_metadata'),                       

                       # View a chapter in frame mode
                       (r'^chapter/(?P<title>.+)/(?P<key>.+)/(?P<chapter_id>.+)$', 'library.views.view_chapter_frame'),                       

                       # View a chapter in non-frame mode
                       (r'^view/(?P<title>.+)/(?P<key>.+)/(?P<chapter_id>.+)$', 'library.views.view_chapter'),                       
                       
                       # Main entry point for a document
                       (r'^view/(?P<title>.+)/(?P<key>[^/]+)/$', 'library.views.view'),

                       # CSS file for within a document (frame-mode)
                       (r'^css/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<stylesheet_id>.+)$', 'library.views.view_stylesheet'),                       

                       (r'^delete/', 'library.views.delete'),
                       
                       # Download a source epub file
                       (r'^download/epub/(?P<title>.+)/(?P<key>[^/]+)/$', 'library.views.download_epub'),

                       # User profile
                       (r'^account/profile/$', 'library.views.profile'),
                       (r'^account/profile/delete/$', 'library.views.profile_delete'),

                       # Static pages
                       (r'^about/$', 'library.views.about'),

                       # Admin pages
                       (r'^admin/search/$', 'library.admin.search'),

                       )


if settings.DEBUG:
    urlpatterns += patterns('',
                            (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/library/templates/static'}),
                            )
    
