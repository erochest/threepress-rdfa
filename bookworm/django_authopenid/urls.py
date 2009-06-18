# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('django_authopenid.views',
                       # manage account registration
                       url(r'^%s$' % ('signin/'), 'signin', name='user_signin'),
                       url(r'^%s$' % ('signout/'), 'signout', name='user_signout'),
                       url(r'^%s%s$' % ('signin/', 'complete/'), 'complete_signin', name='user_complete_signin'),
                       url(r'^%s$' % ('register/'), 'register', name='user_register'),
                       url(r'^%s$' % ('signup/'), 'signup', name='user_signup'),
                       url(r'^%s$' % 'sendpw/', 'sendpw', name='user_sendpw'),
                       url(r'^%s%s$' % ('password/', 'confirm/'), 'confirmchangepw', 
                           name='user_confirmchangepw'),

                       # manage account settings
                       url(r'^%s$' % 'password/', 'changepw', name='user_changepw'),
                       url(r'^%s$' % 'email/', 'changeemail', name='user_changeemail'),
                       url(r'^%s$' % 'openid/', 'changeopenid', name='user_changeopenid'),
                       url(r'^%s$' % 'delete/', 'delete', name='user_delete'),
)

urlpatterns += patterns('bookworm.library.views',
                        url(r'^$', 'profile', name='profile'),
)
