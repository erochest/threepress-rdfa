import logging
from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from bookworm.library.models import UserPref

log = logging.getLogger('middleware')

class Mobile(object):
    @staticmethod
    def process_request(request):
        pass
#        if 'HTTP_HOST' in request.META and 'http://' + request.META['HTTP_HOST'] + '/' != settings.MOBILE_HOST and request.mobile == True:#
#            log.info("Redirecting to %s because hostname was %s" %  (settings.MOBILE_HOST, request.META['HTTP_HOST']))
#            return HttpResponsePermanentRedirect(settings.MOBILE_HOST)


class Language(object):
    @staticmethod
    def process_request(request):
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

