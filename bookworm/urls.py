from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^$', 'library.views.index'),                        
                       
                       (r'^upload/$', 'library.views.upload'),
                       (r'^chapter/(?P<title>.+)/(?P<author>.+)/(?P<chapter_id>.+)/$', 'library.views.view_chapter_frame'),                       
                       (r'^view/(?P<title>.+)/(?P<author>.+)/(?P<chapter_id>.+)/$', 'library.views.view_chapter'),                       
                       (r'^view/(?P<title>.+)/(?P<author>[^/]+)/$', 'library.views.view'),
                       (r'^css/(?P<title>.+)/(?P<author>.+)/(?P<stylesheet_id>.+)/$', 'library.views.view_stylesheet'),                       
                       (r'^delete/(?P<title>.+)/(?P<author>[^/]+)/$', 'library.views.delete'),

                       )

