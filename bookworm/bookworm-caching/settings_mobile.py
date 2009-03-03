from settings import *
import settings

TEMPLATE_DIRS_BASE = TEMPLATE_DIRS

TEMPLATE_DIRS = (
    '%s/library/templates/mobile/auth' % ROOT_PATH,    
    '%s/library/templates/mobile' % ROOT_PATH,    
)

TEMPLATE_DIRS += TEMPLATE_DIRS_BASE

MOBILE = True
CACHE_BACKEND = 'file:///tmp/bookworm/django_cache_mobile'
DATE_FORMAT = "M j y"
SESSION_COOKIE_NAME = 'bookworm_mobile'
