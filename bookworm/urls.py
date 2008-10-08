
from django.conf.urls.defaults import *
from django.contrib import admin

from django.conf import settings
from django.contrib.sitemaps import FlatPageSitemap
from library.views import *

admin.autodiscover()

sitemaps = {
    'flatpages' : FlatPageSitemap,
}

urlpatterns = patterns('',

                       (r'^admin/(.*)',  admin.site.root),

                       # Sitemaps
                       (r'^sitemap.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
                       
                       # Auth
                       (r'^account/', include('django_authopenid.urls')),                       
                       
                       # Bookworm
                       url(r'^$', index, name="index"),                        
                       url(r'^page/(?P<page_number>\d+)$', index, name="index-paginate"),  
                       url(r'^page/(?P<page_number>\d+)/order/(?P<order>[^/]+)/dir/(?P<dir>.+)$', 
                           index, name="index-reorder"),  
                       
                       url(r'^upload/$', upload, name="upload"),

                       # Images from within documents
                       url(r'^(view|chapter)/(?P<title>[^/]+)/(?P<key>[^/]+)/(first/|resume/)?(?P<image>.*(jpg|gif|png|svg)+)$', 
                           view_chapter_image, name="view_chapter_image"),                       
                       
                       # Document metadata
                       url(r'^metadata/(?P<title>[^/]+)/(?P<key>.+)/$', view_document_metadata, name="view_document_metadata"),                       

                       # Force reading the first page of a document
                       url(r'^view/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<first>first)/$', view, name="view_first"),

                       # Force resuming a document
                       url(r'^view/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<resume>resume)/$', view, name="view_resume"),

                       # View a chapter 
                       url(r'^view/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<chapter_id>.+)$', view_chapter, name="view_chapter"),                       

                       # Main entry point for a document
                       url(r'^view/(?P<title>[^/]+)/(?P<key>[^/]+)/$', view, name="view"),

                       # CSS file for within a document (frame-mode)
                       url(r'^css/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<stylesheet_id>.+)$', view_stylesheet, name="view_stylesheet"),

                       # Delete a book
                       url(r'^delete/', delete, name='delete'),
                       
                       # Download a source epub file
                       url(r'^download/epub/(?P<title>.+)/(?P<key>[^/]+)/$', download_epub, name='download_epub'),

                       # User profile
                       url(r'^account/profile/$', profile, name='profile'),
                       url(r'^account/profile/delete/$', profile_delete, name='profile_delete'),

                       # About page
                       url(r'^about/$', about, name='about'),

                       )


urlpatterns += patterns('django.views.generic.simple',
                       url(r'^about/tour$', 'direct_to_template',
                           {'template': 'tour.html'}, name='tour'),
                       url(r'^publishers/epub$', 'direct_to_template',
                           {'template': 'epub.html'}, name='epub'),
                       url(r'^publishers/ebook-testing$', 'direct_to_template',
                           {'template': 'ebooktesting.html'}, name='ebooktesting'),
                       url(r'^help$', 'direct_to_template',
                           {'template': 'help.html'}, name='help'),
                       url(r'^about/openid$', 'direct_to_template',
                           {'template': 'openid.html'}, name='openid'),
                        )

if settings.DEBUG:
    urlpatterns += patterns('',
                            (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/library/templates/static'}),
                            (r'(?P<path>sitedown.html)$', 'django.views.static.serve', 
                             {'document_root': settings.ROOT_PATH + '/library/templates/'}),
                            )
    
