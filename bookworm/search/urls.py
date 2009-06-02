from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('search.views',
                       url(r'^$', 'search', name="search"),                        
)

urlpatterns += patterns('django.views.generic.simple',
                        url(r'^help/$', 'direct_to_template',
                            {'template': 'search_help.html'}, name='search_help'),
                        url(r'^language/$', 'direct_to_template',
                            {'template': 'languages.html'}, name='search_language'),
                        )
