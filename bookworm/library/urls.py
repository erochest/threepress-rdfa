from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('bookworm.library.views',

                       # Public, non-authenticated home
                       url(r'^$', 'index', name="index"),                        

                       # User's library page
                       url(r'^library/$', 'library', name="library"),                        

                       url(r'^page/(?P<page_number>\d+)$', 'library', name="library-paginate"),  
                       url(r'^page/(?P<page_number>\d+)/order/(?P<order>[^/]+)/dir/(?P<dir>.+)$', 
                           'library', name="library-reorder"),  
                       
                       url(r'^upload/$', 'upload', name="upload"),
                       url(r'^reload/(?P<title>[^/]+)/(?P<key>\d+)/$', 'upload', name="reload"),                       

                       # Images from within documents
                       url(r'^(view|chapter)/(?P<title>[^/]+)/(?P<key>\d+)/(first/|resume/)?(?P<image>.*((?i)jpg|gif|png|svg|jpeg|ogv|mpg|mp4|swf)+)$', 
                           'view_chapter_image', name="view_chapter_image"),                       
                       
                       # Document metadata
                       url(r'^metadata/(?P<title>[^/]+)/(?P<key>\d+)/$', 'view_document_metadata', name="view_document_metadata"), 

                       # Force reading the first page of a document
                       url(r'^view/first/(?P<title>[^/]+)/(?P<key>\d+)/$', 'view', {'first':True}, name="view_first"),

                       # Force resuming a document
                       url(r'^view/resume/(?P<title>[^/]+)/(?P<key>\d+)/$', 'view', {'resume':True}, name="view_resume"),

                       # View a chapter 
                       url(r'^view/(?P<title>[^/]+)/(?P<key>\d+)/(?P<chapter_id>.+)$', 'view_chapter', name="view_chapter"),                       

                       # Main entry point for a document
                       url(r'^view/(?P<title>[^/]+)/(?P<key>\d+)/$', 'view', name="view"),

                       # CSS file for within a document 
                       url(r'^css/(?P<title>[^/]+)/(?P<key>\d+)/(?P<stylesheet_id>.+)$', 'view_stylesheet', name="view_stylesheet"),

                       # Delete a book
                       url(r'^delete/', 'delete', name='delete'),
                       
                       # Download a source epub file
                       url(r'^download/epub/(?P<title>.+)/(?P<key>\d+)/$', 'download_epub', name='download_epub'),
                       url(r'^download/epub/(?P<title>.+)/(?P<key>\d+)/public/(?P<nonce>[^/]+)?/?$', 'download_epub', name='download_epub_public'),

                       # User profile
                       url(r'^account/profile/$', 'profile', name='profile'),
                       url(r'^account/profile/delete/$', 'profile_delete', name='profile_delete'),
                       url(r'^account/profile/toggle-reading-mode/$', 'profile_toggle_reading_mode', name='profile_toggle_reading_mode'),
                       url(r'^account/profile/change-font-size/(?P<size>.+)/$', 'profile_change_font_size', name='profile_change_font_size'),
                       url(r'^account/profile/change-font-family/(?P<font>.+)/$', 'profile_change_font_family', name='profile_change_font_family'),

                       # Add-by-URL
                       url('^add/', 'add_by_url', name='add')

)

urlpatterns += patterns('django.views.generic.simple',
                        url(r'^about/$', 'direct_to_template',
                            {'template': 'about.html'}, name='about'),
                        url(r'^about/tour/$', 'direct_to_template',
                            {'template': 'tour.html'}, name='tour'),
                        url(r'^publishers/epub/$', 'direct_to_template',
                            {'template': 'epub.html'}, name='epub'),
                        url(r'^publishers/ebook-testing/$', 'direct_to_template',
                            {'template': 'ebooktesting.html'}, name='ebooktesting'),
                        url(r'^help/$', 'direct_to_template',
                            {'template': 'help.html'}, name='help'),
                        url(r'^about/openid/$', 'direct_to_template',
                            {'template': 'openid.html'}, name='openid'),
                        url(r'^about/reading-mode/$', 'direct_to_template',
                            {'template': 'reading-mode.html'}, name='reading_mode'),
                        url(r'^account/profile/language/$', 'direct_to_template',
                           { 'template': 'auth/language.html'},
                           name='profile_language'),
                        )
