# -*- coding: utf-8 -*-
# Copyright (c) 2007, 2008, Benoît Chesneau
# Copyright (c) 2007 Simon Willison, original work on django-openid
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
#      * Redistributions of source code must retain the above copyright
#      * notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#      * notice, this list of conditions and the following disclaimer in the
#      * documentation and/or other materials provided with the
#      * distribution.  Neither the name of the <ORGANIZATION> nor the names
#      * of its contributors may be used to endorse or promote products
#      * derived from this software without specific prior written
#      * permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import logging

from django.http import HttpResponseRedirect, get_host
from django.shortcuts import render_to_response as render
from django.template import RequestContext, loader, Context
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.contrib.sites.models import Site
from django.utils.http import urlquote_plus
from django.core.mail import send_mail
from django.views.decorators.cache import cache_page, cache_control, never_cache

from bookworm.library.models import UserPref

from openid.consumer.consumer import Consumer, \
    SUCCESS, CANCEL, FAILURE, SETUP_NEEDED
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import sreg
# needed for some linux distributions like debian
try:
    from openid.yadis import xri
except ImportError:
    from yadis import xri

import re
import urllib


from util import OpenID, DjangoOpenIDStore, from_openid_response
from models import UserAssociation, UserPasswordQueue
from forms import OpenidSigninForm, OpenidAuthForm, OpenidRegisterForm, \
        OpenidVerifyForm, RegistrationForm, ChangepwForm, ChangeemailForm, \
        ChangeopenidForm, DeleteForm, EmailPasswordForm

def get_url_host(request):
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    host = escape(get_host(request))
    return '%s://%s' % (protocol, host)

def get_full_url(request):
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    host = escape(request.META['HTTP_HOST'])
    return get_url_host(request) + request.get_full_path()

next_url_re = re.compile('^/[-\w/]+$')

def is_valid_next_url(next):
    # When we allow this:
    #   /openid/?next=/welcome/
    # For security reasons we want to restrict the next= bit 
    # to being a local path, not a complete URL.
    return bool(next_url_re.match(next))

def ask_openid(request, openid_url, redirect_to, on_failure=None,
        sreg_request=None):
    """ basic function to ask openid and return response """

    on_failure = on_failure or signin_failure
    
    trust_root = getattr(
        settings, 'OPENID_TRUST_ROOT', get_url_host(request) + '/'
    )
    if xri.identifierScheme(openid_url) == 'XRI' and getattr(
            settings, 'OPENID_DISALLOW_INAMES', False
    ):
        msg = _("i-names are not supported")
        return on_failure(request, msg)
    consumer = Consumer(request.session, DjangoOpenIDStore())
    try:
        auth_request = consumer.begin(openid_url)
    except DiscoveryFailure:
        msg = _("The password or OpenID was invalid")
        return on_failure(request, msg)

    if sreg_request:
        auth_request.addExtension(sreg_request)
    redirect_url = auth_request.redirectURL(trust_root, redirect_to)
    return HttpResponseRedirect(redirect_url)

def complete(request, on_success=None, on_failure=None, return_to=None):
    """ complete openid signin """
    on_success = on_success or default_on_success
    on_failure = on_failure or default_on_failure
    
    consumer = Consumer(request.session, DjangoOpenIDStore())
    openid_response = consumer.complete(dict(request.GET.items()),
            return_to)

    try:
        rel = UserAssociation.objects.get(openid_url__exact = openid_response.identity_url)  
        try:
            rel.user
        except User.DoesNotExist:
            rel.delete()
            return register(request)
    except UserAssociation.DoesNotExist:
        pass

    if openid_response.status == SUCCESS:
        return on_success(request, openid_response.identity_url,
                openid_response)
    elif openid_response.status == CANCEL:
        return on_failure(request, 'The request was cancelled')
    elif openid_response.status == FAILURE:
        return on_failure(request, openid_response.message)
    elif openid_response.status == SETUP_NEEDED:
        return on_failure(request, 'Setup needed')
    else:
        assert False, "Bad openid status: %s" % openid_response.status

def default_on_success(request, identity_url, openid_response):
    """ default action on openid signin success """
    request.session['openid'] = from_openid_response(openid_response)
    
    next = request.GET.get('next', '').strip()
    if not next or not is_valid_next_url(next):
        next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))
    
    return HttpResponseRedirect(next)

def default_on_failure(request, message):
    """ default failure action on signin """
    return render('openid_failure.html', {
        'message': message
    })


def not_authenticated(func):
    """ decorator that redirect user to next page if
    he is already logged."""
    def decorated(request, **kwargs):
        if request.user.is_authenticated():
            next = request.GET.get("next", reverse('library'))
            return HttpResponseRedirect(next)
        return func(request, **kwargs)
    return decorated

@not_authenticated
@never_cache
def signin(request):
    """
    signin page. It manage the legacy authentification (user/password) 
    and authentification with openid.

    url: /signin/
    
    template : authopenid/signin.htm
    """

    on_failure = signin_failure
    next = ''


    if request.GET.get('next') and is_valid_next_url(request.GET['next']):
        next = request.GET.get('next', '').strip()
    if not next or not is_valid_next_url(next):
        next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))

    form_signin = OpenidSigninForm(initial={'next':next})
    form_auth = OpenidAuthForm(initial={'next':next})

    if request.POST:   
        if 'bsignin' in request.POST.keys():
            form_signin = OpenidSigninForm(request.POST)
            if form_signin.is_valid():
                next = form_signin.cleaned_data['next']
                if not next:
                    next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))

                sreg_req = sreg.SRegRequest(optional=['nickname', 'email', 'language', 'country', 'timezone', 'fullname'])
                redirect_to = "%s%s?%s" % (
                        get_url_host(request),
                        reverse('user_complete_signin'), 
                        urllib.urlencode({'next':next})
                )

                return ask_openid(request, 
                        form_signin.cleaned_data['openid_url'], 
                        redirect_to, 
                        on_failure=signin_failure, 
                        sreg_request=sreg_req)

        elif 'blogin' in request.POST.keys():
            # perform normal django authentification
            form_auth = OpenidAuthForm(request.POST)
            if form_auth.is_valid():
                user_ = form_auth.get_user()
                login(request, user_)

                next = form_auth.cleaned_data['next']
                if not next:
                    next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))
                return HttpResponseRedirect(next)


    return render('authopenid/signin.html', {
        'form1': form_auth,
        'form2': form_signin,
        'action': request.path,
        'msg':  request.GET.get('msg',''),
        'signin_page': True,
        'sendpw_url': reverse('user_sendpw'),
    }, context_instance=RequestContext(request))

def complete_signin(request):
    """ in case of complete signin with openid """
    return complete(request, signin_success, signin_failure,
            get_url_host(request) + reverse('user_complete_signin'))


def signin_success(request, identity_url, openid_response):
    """
    openid signin success.

    If the openid is already registered, the user is redirected to 
    url set par next or in settings with OPENID_REDIRECT_NEXT variable.
    If none of these urls are set user is redirectd to /.

    if openid isn't registered user is redirected to register page.
    """

    openid_ = from_openid_response(openid_response)
    request.session['openid'] = openid_

    try:
        rel = UserAssociation.objects.get(openid_url__exact = str(openid_))
    except:
        # try to register this new user
        return register(request)
    
    user_ = rel.user

    if user_.is_active:
        user_.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user_)

    next = request.GET.get('next', '').strip()
    if not next or not is_valid_next_url(next):
        next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))
    
    return HttpResponseRedirect(next)

def is_association_exist(openid_url):
    """ test if an openid is already in database """
    is_exist = True
    try:
        uassoc = UserAssociation.objects.get(openid_url__exact = openid_url)
    except:
        is_exist = False
    return is_exist

@not_authenticated
@never_cache
def register(request):
    """
    register an openid.

    If user is already a member he can associate its openid with 
    its account.

    A new account could also be created and automaticaly associated
    to the openid.

    url : /complete/

    template : authopenid/complete.html
    """

    is_redirect = False
    next = request.GET.get('next', '').strip()
    if not next or not is_valid_next_url(next):
        next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))


    openid_ = request.session.get('openid', None)
    if not openid_:
        return HttpResponseRedirect(reverse('user_signin') + next)

    nickname = openid_.sreg.get('nickname', '')
    email = openid_.sreg.get('email', '')
    
    form1 = OpenidRegisterForm(initial={
        'next': next,
        'username': nickname,
        'email': email,
    }) 
    form2 = OpenidVerifyForm(initial={
        'next': next,
        'username': nickname,
    })
    
    if request.POST:
        just_completed = False
        if 'bnewaccount' in request.POST.keys():
            form1 = OpenidRegisterForm(request.POST)
            if form1.is_valid():
                next = form1.cleaned_data['next']
                if not next:
                    next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))
                is_redirect = True
                tmp_pwd = User.objects.make_random_password()
                user_ = User.objects.create_user(form1.cleaned_data['username'],
                         form1.cleaned_data['email'], tmp_pwd)

                # Save a profile for them
                profile = UserPref(user=user_)
                profile.save()

                # make association with openid
                uassoc = UserAssociation(openid_url=str(openid_),
                        user_id=user_.id)
                uassoc.save()
                    
                # login 
                user_.backend = "django.contrib.auth.backends.ModelBackend"
                login(request, user_)
        elif 'bverify' in request.POST.keys():
            form2 = OpenidVerifyForm(request.POST)
            if form2.is_valid():
                is_redirect = True
                next = form2.cleaned_data['next']
                if not next:
                    next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))
                user_ = form2.get_user()

                uassoc = UserAssociation(openid_url=str(openid_),
                        user_id=user_.id)
                uassoc.save()
                login(request, user_)
        
        # redirect, can redirect only if forms are valid.
        if is_redirect:
            return HttpResponseRedirect(next) 
    
    return render('authopenid/complete.html', {
        'form1': form1,
        'form2': form2,
        'action': reverse('user_register'),
        'nickname': nickname,
        'email': email
    }, context_instance=RequestContext(request))

def signin_failure(request, message):
    """
    falure with openid signin. Go back to signin page.

    template : "authopenid/signin.html"
    """
    next = request.REQUEST.get('next', '')

    form_signin = OpenidSigninForm(initial={'next': next})
    form_auth = OpenidAuthForm(initial={'next': next})

    return render('authopenid/signin.html', {
        'msg': message,
        'form1': form_auth,
        'form2': form_signin,
    }, context_instance=RequestContext(request))

@not_authenticated
@never_cache
def signup(request):
    """
    signup page. Create a legacy account

    url : /signup/"

    templates: authopenid/signup.html, authopenid/confirm_email.txt
    """
    action_signin = reverse('user_signin')

    next = request.GET.get('next', '')
    if not next or not is_valid_next_url(next):
        next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))

    form = RegistrationForm(initial={'next':next})
    form_signin = OpenidSigninForm(initial={'next':next})
    
    if request.POST:
        form = RegistrationForm(request.POST)
        if form.is_valid():

            next = form.cleaned_data.get('next', '')
            if not next or not is_valid_next_url(next):
                next = getattr(settings, 'OPENID_REDIRECT_NEXT', reverse('library'))

            user_ = User.objects.create_user( form.cleaned_data['username'],
                    form.cleaned_data['email'], form.cleaned_data['password1'])
           
            user_.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user_)
            
            # send email
            current_domain = Site.objects.get_current().domain
            subject = _("Welcome")
            message_template = loader.get_template(
                    'authopenid/confirm_email.txt'
            )
            message_context = Context({ 
                'site_url': 'http://%s/' % current_domain,
                'username': form.cleaned_data['username'],
                'password': form.cleaned_data['password1'] 
            })
            message = message_template.render(message_context)
            if not settings.DEBUG:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, 
                          [user_.email])
            
            return HttpResponseRedirect(next)
    
    return render('authopenid/signup.html', {
        'form': form,
        'form2': form_signin,
        'action': request.path,
        'action_signin': action_signin,
        }, context_instance=RequestContext(request))

@login_required
def signout(request, msg=None):
    """
    signout from the website. Remove openid from session and kill it.

    url : /signout/"
    """
    try:
        del request.session['openid']
    except KeyError:
        pass
    next = request.GET.get('next', reverse('index'))
    if not is_valid_next_url(next):
        next = '/'
    if msg:
        next = next + '?msg=' + urlquote_plus(msg)
    logout(request)
    
    return HttpResponseRedirect(next)

@login_required
@never_cache
def account_settings(request):
    """
    index pages to changes some basic account settings :
     - change password
     - change email
     - associate a new openid
     - delete account

    url : /

    template : authopenid/settings.html
    """
    msg = request.GET.get('msg', '')
    is_openid = True

    try:
        uassoc = UserAssociation.objects.get(
                user__username__exact=request.user.username
        )
    except:
        is_openid = False


    return render('authopenid/settings.html', {
        'msg': msg, 
        'settings_path': request.path, 
        'is_openid': is_openid
        }, context_instance=RequestContext(request))

@login_required
@never_cache
def changepw(request):
    """
    change password view.

    url : /changepw/
    template: authopenid/changepw.html
    """
    
    user_ = request.user
    
    if request.POST:
        form = ChangepwForm(request.POST, user=user_)
        if form.is_valid():
            user_.set_password(form.cleaned_data['password1'])
            user_.save()
            msg = _("Password changed.") 
            redirect = "%s?msg=%s" % (
                    reverse('bookworm.library.views.profile'),
                    urlquote_plus(msg))
            return HttpResponseRedirect(redirect)
    else:
        form = ChangepwForm(user=user_)

    return render('authopenid/changepw.html', {'form': form },
                                context_instance=RequestContext(request))

@login_required
@never_cache
def changeemail(request):
    """ 
    changeemail view. It require password or openid to allow change.

    url: /changeemail/

    template : authopenid/changeemail.html
    """
    msg = request.GET.get('msg', '')
    extension_args = {}
    user_ = request.user
    
    redirect_to = get_url_host(request) + reverse('user_changeemail')

    if request.POST:
        form = ChangeemailForm(request.POST, user=user_)
        if form.is_valid():
            if user_.check_password(form.cleaned_data['password']):
                user_.email = form.cleaned_data['email']
                user_.save()
                msg = _("Email changed.") 
                redirect = "%s?msg=%s" % (reverse('bookworm.library.views.profile'),
                                      urlquote_plus(msg))
                return HttpResponseRedirect(redirect)
            else:
                return ask_openid(request, form.cleaned_data['password'], 
                                  redirect_to, on_failure=emailopenid_failure)    

    elif not request.POST and 'openid.mode' in request.GET:
        return complete(request, emailopenid_success, 
                emailopenid_failure, redirect_to) 
    else:
        form = ChangeemailForm(initial={'email': user_.email},
                user=user_)
    
    return render('authopenid/changeemail.html', {
        'form': form,
        'msg': msg 
        }, context_instance=RequestContext(request))


def emailopenid_success(request, identity_url, openid_response):
    openid_ = from_openid_response(openid_response)

    user_ = request.user
    try:
        uassoc = UserAssociation.objects.get(
                openid_url__exact=identity_url
        )
    except:
        return emailopenid_failure(request, 
                _("No OpenID was found in our database"))

    if uassoc.user.username != request.user.username:
        return emailopenid_failure(request, 
                _("This OpenID isn't associated with the current logged-in user" % 
                    identity_url))
    
    new_email = request.session.get('new_email', '')
    if new_email:
        user_.email = new_email
        user_.save()
        del request.session['new_email']
    msg = _("Email changed.")

    redirect = "%s?msg=%s" % (reverse('user_account_settings'),
            urlquote_plus(msg))
    return HttpResponseRedirect(redirect)
    

def emailopenid_failure(request, message):
    redirect_to = "%s?msg=%s" % (
            reverse('user_changeemail'), urlquote_plus(message))
    return HttpResponseRedirect(redirect_to)
 
@login_required
@never_cache
def changeopenid(request):
    """
    change openid view. Allow user to change openid 
    associated to its username.

    url : /changeopenid/

    template: authopenid/changeopenid.html
    """

    extension_args = {}
    openid_url = ''
    has_openid = True
    msg = request.GET.get('msg', '')
        
    user_ = request.user

    try:
        uopenid = UserAssociation.objects.get(user=user_)
        openid_url = uopenid.openid_url
    except:
        has_openid = False
    
    redirect_to = get_url_host(request) + reverse('user_changeopenid')
    if request.POST and has_openid:
        form = ChangeopenidForm(request.POST, user=user_)
        if form.is_valid():
            return ask_openid(request, form.cleaned_data['openid_url'],
                    redirect_to, on_failure=changeopenid_failure)
    elif not request.POST and has_openid:
        if 'openid.mode' in request.GET:
            return complete(request, changeopenid_success,
                    changeopenid_failure, redirect_to)    

    form = ChangeopenidForm(initial={'openid_url': openid_url }, user=user_)
    return render('authopenid/changeopenid.html', {
        'form': form,
        'has_openid': has_openid, 
        'msg': msg 
        }, context_instance=RequestContext(request))

def changeopenid_success(request, identity_url, openid_response):
    openid_ = from_openid_response(openid_response)
    is_exist = True
    try:
        uassoc = UserAssociation.objects.get(openid_url__exact=identity_url)
    except:
        is_exist = False
        
    if not is_exist:
        try:
            uassoc = UserAssociation.objects.get(
                    user__username__exact=request.user.username
            )
            uassoc.openid_url = identity_url
            uassoc.save()
        except:
            uassoc = UserAssociation(user=request.user, 
                    openid_url=identity_url)
            uassoc.save()
    elif uassoc.user.username != request.user.username:
        return changeopenid_failure(request, 
                _('This OpenID is already associated with another account.'))

    request.session['openids'] = []
    request.session['openids'].append(openid_)

    msg = _("This OpenID is now associated with your account.") 
    redirect = "%s?msg=%s" % (
            reverse('bookworm.library.views.profile'), 
            urlquote_plus(msg))
    return HttpResponseRedirect(redirect)
    

def changeopenid_failure(request, message):
    redirect_to = "%s?msg=%s" % (
            reverse('user_changeopenid'), 
            urlquote_plus(message))
    return HttpResponseRedirect(redirect_to)
  
@login_required
@never_cache
def delete(request):
    """
    delete view. Allow user to delete its account. Password/openid are required to 
    confirm it. He should also check the confirm checkbox.

    url : /delete

    template : authopenid/delete.html
    """
    extension_args = {}
    
    user_ = request.user
    form = None

    redirect_to = get_url_host(request) + reverse('user_delete') 
    if request.POST:
        form = DeleteForm(request.POST, user=user_)
        if form.is_valid():
            if 'password' in form.cleaned_data and form.cleaned_data['password']:
                if user_.check_password(form.cleaned_data['password']):
                    user_.delete()
                    return signout(request, msg='Your account has been deleted.')
                return ask_openid(request, form.cleaned_data['password'],
                                  redirect_to, on_failure=deleteopenid_failure)
            else:
                return ask_openid(request, form.cleaned_data['openid_url'],
                        redirect_to, on_failure=deleteopenid_failure)
    elif not request.POST and 'openid.mode' in request.GET:
        logging.info('calling complete with request %s' % request)
        return complete(request, deleteopenid_success, deleteopenid_failure,
                redirect_to) 
    
    if not form:
        form = DeleteForm(user=user_)

    msg = request.GET.get('msg','')
    return render('authopenid/delete.html', {
        'form': form, 
        'msg': msg, 
        }, context_instance=RequestContext(request))

def deleteopenid_success(request, identity_url, openid_response):
    logging.info('openid response: %s' % openid_response)
    openid_ = from_openid_response(openid_response)
    
    user_ = request.user
    try:
        uassoc = UserAssociation.objects.get(
                openid_url__exact=identity_url
        )
    except:
        return deleteopenid_failure(request,
                _("This OpenID isn't associated in the system."))

    if uassoc.user.username == user_.username:
        user_.delete()
        return signout(request, msg='Your account has been deleted.')
    else:
        return deleteopenid_failure(request,
                _("This OpenID isn't associated with the current logged-in user"))
    
    msg = _("Account deleted.") 
    redirect = "/?msg=%s" % (urlquote_plus(msg))
    return HttpResponseRedirect(redirect)
    

def deleteopenid_failure(request, message):
    redirect_to = "%s?msg=%s" % (reverse('user_delete'), urlquote_plus(message))
    return HttpResponseRedirect(redirect_to)

@never_cache
def sendpw(request):
    """
    send a new password to the user. It return a mail with 
    a new pasword and a confirm link in. To activate the 
    new password, the user should click on confirm link.

    url : /sendpw/

    templates :  authopenid/sendpw_email.txt, authopenid/sendpw.html
    """

    msg = request.GET.get('msg','')
    if request.POST:
        form = EmailPasswordForm(request.POST)
        if form.is_valid():
            new_pw = User.objects.make_random_password()
            confirm_key = UserPasswordQueue.objects.get_new_confirm_key()
            try:
                uqueue = UserPasswordQueue.objects.get(
                        user=form.user_cache
                )
            except:
                uqueue = UserPasswordQueue(
                        user=form.user_cache
                )
            uqueue.new_password = new_pw
            uqueue.confirm_key = confirm_key
            uqueue.save()
            # send email 
            current_domain = Site.objects.get_current().domain
            subject = _("Request for a new password")
            message_template = loader.get_template(
                    'authopenid/sendpw_email.txt')
            message_context = Context({ 
                'site_url': 'http://%s' % current_domain,
                'confirm_key': confirm_key,
                'username': form.user_cache.username,
                'password': new_pw,
                'url_confirm': reverse('user_confirmchangepw'),
            })
            message = message_template.render(message_context)
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, 
                    [form.user_cache.email])
            msg = _("A new password has been sent to your email")
    else:
        form = EmailPasswordForm()
        
    return render('authopenid/sendpw.html', {
        'form': form,
        'msg': msg 
        }, context_instance=RequestContext(request))


def confirmchangepw(request):
    """
    view to set new password when the user click on confirm link
    in its mail. Basically it check if the confirm key exist, then
    replace old password with new password and remove confirm
    key from the queue. Then it redirect the user to signin
    page.

    url : /sendpw/confirm/?key

    """
    confirm_key = request.GET.get('key', '')
    if not confirm_key:
        return HttpResponseRedirect('/')

    try:
        uqueue = UserPasswordQueue.objects.get(
                confirm_key__exact=confirm_key
        )
    except:
        msg = _("Can not change password. Confirmation key '%s'\
                isn't registered." % confirm_key) 
        redirect = "%s?msg=%s" % (
                reverse('user_sendpw'), urlquote_plus(msg))
        return HttpResponseRedirect(redirect)

    try:
        user_ = User.objects.get(id=uqueue.user.id)
    except:
        msg = _("Cannot change password, as this user doesn't exist in the database.") 
        redirect = "%s?msg=%s" % (reverse('user_sendpw'), 
                urlquote_plus(msg))
        return HttpResponseRedirect(redirect)

    user_.set_password(uqueue.new_password)
    user_.save()
    uqueue.delete()
    msg = _("Password changed for %s. You could now sign in" % 
            user_.username) 
    redirect = "%s?msg=%s" % (reverse('user_signin'), 
                                        urlquote_plus(msg))

    return HttpResponseRedirect(redirect)
