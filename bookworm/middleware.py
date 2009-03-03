import logging
from django.conf import settings
from django.http import HttpResponsePermanentRedirect

log = logging.getLogger('middleware')

class Mobile(object):
    @staticmethod
    def process_request(request):
        pass
#        if 'HTTP_HOST' in request.META and 'http://' + request.META['HTTP_HOST'] + '/' != settings.MOBILE_HOST and request.mobile == True:#
#            log.info("Redirecting to %s because hostname was %s" %  (settings.MOBILE_HOST, request.META['HTTP_HOST']))
#            return HttpResponsePermanentRedirect(settings.MOBILE_HOST)
