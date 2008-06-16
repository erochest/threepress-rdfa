from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^$', 'library.views.index'),                        
                       
                       (r'^upload/$', 'library.views.upload'),

                       # View a chapter in frame mode
                       (r'^chapter/(?P<title>.+)/(?P<key>.+)/(?P<chapter_id>.+)$', 'library.views.view_chapter_frame'),                       

                       # Images from within documents
                       (r'^(view|chapter)/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<chapter_id>[^/]+)/(?P<image>.*\..*)$', 
                        'library.views.view_chapter_image'),                       

                       # View a chapter in non-frame mode
                       (r'^view/(?P<title>.+)/(?P<key>.+)/(?P<chapter_id>.+)$', 'library.views.view_chapter'),                       

                       # Main entry point for a document
                       (r'^view/(?P<title>.+)/(?P<key>[^/]+)/$', 'library.views.view'),

                       # CSS file for within a document (frame-mode)
                       (r'^css/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<stylesheet_id>.+)$', 'library.views.view_stylesheet'),                       

                       # DEPRECATED; should be POST
                       (r'^delete/', 'library.views.delete'),
                       
                       # Download a source epub file
                       (r'^download/epub/(?P<title>.+)/(?P<key>[^/]+)/$', 'library.views.download_epub'),

                       # User profile
                       (r'^profile/$', 'library.views.profile'),
                       
                       (r'^profile/delete/$', 'library.views.profile_delete'),

                       # Static pages
                       (r'^about/$', 'library.views.about'),

                       # Admin pages
                       (r'^admin/search/$', 'library.admin.search'),
                       )

