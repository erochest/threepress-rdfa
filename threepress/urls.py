from django.conf.urls.defaults import *
from django.conf import settings
urlpatterns = patterns('',

                       # Example:
                       # (r'^threepress/', include('threepress.foo.urls')),
                       
                       # Uncomment this for admin:
                       (r'^admin/', include('django.contrib.admin.urls')),
                       (r'^document/(?P<id>.+)/(?P<chapter_id>.+)/$', 'threepress.search.views.document_view'),
                       (r'^document/(?P<id>.+)/$', 'threepress.search.views.document_view'),
                       #(r'^page/(?P<page>.+)/$', 'threepress.search.views.page_view'),
                       (r'^search/(?P<doc_id>.+)$', 'threepress.search.views.search'),
                       (r'^search/', 'threepress.search.views.search'),
                       (r'^$', 'threepress.search.views.index'), 
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/liza/threepress/threepress/search/templates/static'}),
    )
