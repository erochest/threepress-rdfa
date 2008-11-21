from django.conf import settings
from django.http import HttpResponsePermanentRedirect

class Mobile(object):
    @staticmethod
    def process_request(request):
        if 'HTTP_HOST' in request.META and request.META['HTTP_HOST'] != settings.MOBILE_HOST and request.mobile == True:
            return HttpResponsePermanentRedirect(settings.MOBILE_HOST)
