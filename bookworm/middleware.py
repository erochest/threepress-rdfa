import logging
from django.conf import settings
from django.http import HttpResponsePermanentRedirect

log = logging.getLogger('middleware')

stanza_browsers = ('iphone', )

class Mobile(object):
    @staticmethod
    def process_request(request):
        if 'HTTP_HOST' in request.META and request.META['HTTP_HOST'] != settings.MOBILE_HOST and request.mobile == True:
            log.info("Redirecting to %s because hostname was %s" %  (settings.MOBILE_HOST, request.META['HTTP_HOST']))
            return HttpResponsePermanentRedirect(settings.MOBILE_HOST)
        for b in stanza_browsers:
            if b in request.META["HTTP_USER_AGENT"].lower():
                request.stanza_compatible = True
