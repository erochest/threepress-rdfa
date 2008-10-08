import logging
from forms import EpubValidateForm
from models import SystemInfo, UserPref
from django.conf import settings

log = logging.getLogger('context_processors')
 
def nav(request):
    form = EpubValidateForm()
    return {'upload_form': form }

def mobile(request):
    return { 'mobile': settings.MOBILE }

def profile(request):
    '''Get (or create) a user preferences object for a given user.
    If created, the total number of users counter will be incremented and
    the memcache updated.'''
    userprefs = None
    try:
        userprefs = request.user.get_profile()
    except AttributeError:
        # Occurs when this is called on an anonymous user; ignore
        pass
    except UserPref.DoesNotExist:
        log.debug('Creating a userprefs object for %s' % request.user.username)
        # Create a preference object for this user
        userprefs = UserPref(user=request.user)
        userprefs.save()
    return { 'profile': userprefs }
