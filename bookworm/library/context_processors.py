import logging
from django.conf import settings

from bookworm.library.forms import EpubValidateForm
from bookworm.library.models import SystemInfo, UserPref

log = logging.getLogger('context_processors')

stanza_browsers = ('iphone', )

def local_settings(request):
    if hasattr(request.session, 'django_language') and request.session.django_language:
        current_language = request.session.django_language
    else:
        current_language = settings.LANGUAGE_CODE 
    return {
        'MEDIA_URL': settings.MEDIA_URL,
        'ORM_MEDIA_URL': settings.ORM_MEDIA_URL,
        'CACHE_TEMPLATE_TIMEOUT' : settings.CACHE_TEMPLATE_TIMEOUT,
        'OFFLINE':settings.OFFLINE,
        'ANALYTICS_KEY':settings.ANALYTICS_KEY,
        'MOBILE_HOST':settings.MOBILE_HOST,
        'HOSTING_CREDIT':settings.HOSTING_CREDIT,
        'HOSTING_CREDIT_URL':settings.HOSTING_CREDIT_URL,
        'ADMIN_EMAIL':settings.DISPLAY_ADMIN_EMAIL,
        'HOSTNAME':settings.HOSTNAME,
        'SECURE_HOSTNAME':settings.SECURE_HOSTNAME,
        'CUSTOMER_SERVICE_URL':settings.CUSTOMER_SERVICE_URL,
        'CUSTOMER_SERVICE_NAME':settings.CUSTOMER_SERVICE_NAME,
        'current_language':current_language
    }
  
def nav(request):
    form = EpubValidateForm()
    return {'upload_form': form }

def mobile(request):
    stanza_compatible = False
    if not hasattr(request, 'stanza_compatible') and request.META.has_key('HTTP_USER_AGENT'):
        log.debug('Checking %s for Stanza-compatibility' % request.META['HTTP_USER_AGENT']) 
        for b in stanza_browsers:
            if b in request.META["HTTP_USER_AGENT"].lower():
                log.debug('Setting true for stanza-compatible browser')
                stanza_compatible = True
    
    if settings.DEBUG and settings.MOBILE:
        log.debug("Forcing stanza compatibility")
        stanza_compatible = True

    if request.META.has_key('HTTP_USER_AGENT'):
        is_iphone = 'iphone' in request.META["HTTP_USER_AGENT"].lower()
    else:
        is_iphone = False

    return { 'mobile': settings.MOBILE,
             'iphone': is_iphone,
             'stanza_compatible': stanza_compatible}

def profile(request):
    '''Get (or create) a user preferences object for a given user.'''
    userprefs = None
    try:
        userprefs = request.user.get_profile()
        if not settings.LANGUAGE_COOKIE_NAME in request.session:
            request.session[settings.LANGUAGE_COOKIE_NAME] = userprefs.language

    except AttributeError:
        # Occurs when this is called on an anonymous user; ignore
        pass
    except UserPref.DoesNotExist:
        log.debug('Creating a userprefs object for %s' % request.user.username)
        # Create a preference object for this user
        userprefs = UserPref(user=request.user)
        userprefs.save()

    return { 'profile': userprefs }
