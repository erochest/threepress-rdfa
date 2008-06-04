from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^$', 'library.views.index'),                        
                       
                       (r'^upload/$', 'library.views.upload'),
                       (r'^view/(?P<title>.+)/(?P<author>.+)/(?P<chapter_id>.+)/$', 'library.views.view_chapter'),                       
                       (r'^view/(?P<title>.+)/(?P<author>[^/]+)/$', 'library.views.view'),
                       (r'^delete/(?P<title>.+)/(?P<author>[^/]+)/$', 'library.views.delete'),
                       )

