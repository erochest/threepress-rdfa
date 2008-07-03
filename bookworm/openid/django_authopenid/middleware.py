# -*- coding: utf-8 -*-

__all__ = ["OpenIDMiddleware"]

class OpenIDMiddleware(object):
    """
    Populate request.openid. This comes either from cookie or from
    session, depending on the presence of OPENID_USE_SESSIONS.
    """
    def process_request(self, request):
        request.openid = request.session.get('openid', None)
