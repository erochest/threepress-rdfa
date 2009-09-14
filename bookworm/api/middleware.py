# The following license information applies to the SSL Redirect class.  All other code
# is licensed under the Bookworm license

__license__ = "Python"
__copyright__ = "Copyright (C) 2007, Stephen Zabel"
__author__ = "Stephen Zabel - sjzabel@gmail.com"
__contributors__ = "Jay Parlar - parlar@gmail.com"
import logging

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect, get_host
from django.contrib.auth import login, authenticate
from bookworm.api import APIException, BookwormHttpResponseForbidden, BookwormHttpResponseNotFound
from bookworm.api.models import APIKey

log = logging.getLogger(__name__)

class APIKeyCheck(object):

    def process_view(self, request, view_func, view_args, view_kwargs):
        if '/api/' in request.path and not '/public/' in request.path: 
            if 'epub_id' in view_kwargs:
                # This is a request for a particular document and so should not
                # be considered a published endpoint; return a 404 in case of failure
                return self.check_key(request, response_type='not found')
            
            # This is a published endpoint; return Forbidden on failure cases
            return self.check_key(request, response_type='forbidden')
        return None

    def process_exception(self, request, exception):
        if isinstance(exception, APIException):
            return BookwormHttpResponseForbidden(exception.message)

    def check_key(self, request, response_type='forbidden'):
        '''Checks the api_key value in the request. If response_type == 'forbidden',
           return an HTTP 403 response; otherwise an HTTP 404.'''
        if settings.API_FIELD_NAME in request.GET:
            apikey = request.GET[settings.API_FIELD_NAME]
        elif settings.API_FIELD_NAME in request.POST:
            apikey = request.POST[settings.API_FIELD_NAME]
        else:
            if response_type == 'forbidden':
                return BookwormHttpResponseForbidden("api_key was not found in request parameters")
            else:
                return BookwormHttpResponseNotFound()
        try:
            user = APIKey.objects.user_for_key(apikey)
        except APIException, e:
            if response_type == 'forbidden':
                return BookwormHttpResponseForbidden(e.message)                
            else:
                return BookwormHttpResponseNotFound()
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        return None

        
class SSLRedirect(object):
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        '''Redirect the view to SSL if the SSL parameter is true AND if we are neither in 
        debug mode (using the Django development server) nor running tests (via test_settings.py)'''
        if '/api/' in request.path and not '/public/' in request.path and not (settings.TESTING or settings.DEBUG):
            if not self._is_secure(request):
                return self._redirect(request)
            
    def _is_secure(self, request):
        if request.is_secure():
	    return True
        if 'HTTP_X_FORWARDED_SSL' in request.META:
            return request.META['HTTP_X_FORWARDED_SSL'] == 'on'
        return False

    def _redirect(self, request):
        protocol = "https"
        newurl = "%s://%s%s" % (protocol,get_host(request),request.get_full_path())
        if settings.DEBUG and request.method == 'POST':
            raise RuntimeError, \
        """Django can't perform a SSL redirect while maintaining POST data.
           Please structure your views so that redirects only occur during GETs."""

        return HttpResponsePermanentRedirect(newurl)
