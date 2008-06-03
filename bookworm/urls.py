from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^$', 'library.views.index'),                        
                       
                       (r'^upload/$', 'library.views.upload'),

                       # View an epub document (expanded epub)
                       #(r'^epub/(?P<document_id>[^/]+)/$', 'library.views.document_epub'),

                       # View an epub document by ID + chapter
                       #(r'^epub/(?P<document_id>.+)/(?P<chapter_id>.+)/$', 'library.views.document_chapter_epub'),

                       )

