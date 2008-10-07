from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('threepress.epub.views',
                       url(r'/logos$', 'direct_to_template',
                           {'template': 'logos.html'}, name='logos'),
                       )
