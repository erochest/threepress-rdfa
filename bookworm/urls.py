from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^$', 'library.views.index'),                        
                       
                       (r'^upload/$', 'library.views.upload'),
                       
                       (r'^view/(?P<title>.+)/(?P<author>.+)/$', 'library.views.view'),

                       )

