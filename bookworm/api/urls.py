from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('bookworm.api.views',
                       url(r'^documents/$', 'main', {'SSL':True}, name="main"),
                       url(r'^documents/(?P<epub_id>\d+)/$', 'api_download', {'SSL':True}, name="api_download"),
)

urlpatterns += patterns('django.views.generic.simple',
                        url(r'^public/help/$', 'direct_to_template', {'template': 'api_help.html'}, name='api_help'),
                        )
