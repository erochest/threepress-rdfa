from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound, HttpResponseForbidden

class APIException(Exception):
    pass

class BookwormAPIResponse(HttpResponse):
    def __init__(self, content):
        '''Wrap the content message in XHTML'''
        content = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Bookworm API response</title><body><div>%s</div></body></html>''' % content
        HttpResponse.__init__(self, content)

class BookwormHttpResponseNotFound(BookwormAPIResponse, HttpResponseNotFound):
    def __init__(self):
        BookwormAPIResponse.__init__(self, 'Not found')

class BookwormHttpResponseNotAllowed(BookwormAPIResponse, HttpResponseNotAllowed):
    pass

class BookwormHttpResponseForbidden(BookwormAPIResponse, HttpResponseForbidden):
    pass

class BookwormHttpResponseNotAcceptable(HttpResponse):
    # Don't wrap this one in an API response; we'll be getting a complete web page from Bookworm
    status_code = 406

class HttpResponseCreated(HttpResponse):
    '''Return an HTTP 201 Created response. The parameter for the Content-Location field is required;
      this should be the URL to the created resource.'''
    status_code = 201

    def __init__(self, location):
        HttpResponse.__init__(self)
        self['Content-Location'] = location

