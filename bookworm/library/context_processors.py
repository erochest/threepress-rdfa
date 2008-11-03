import logging
from django.conf import settings

from library.forms import EpubValidateForm
from library.models import SystemInfo, UserPref

log = logging.getLogger('context_processors')
 
def nav(request):
    form = EpubValidateForm()
    return {'upload_form': form }

def mobile(request):
    return { 'mobile': settings.MOBILE }


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
