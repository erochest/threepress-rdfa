from settings import *
import settings
import os.path

TEMPLATE_DIRS_BASE = TEMPLATE_DIRS

TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'mobile', 'templates', 'auth'),
    os.path.join(ROOT_PATH, 'mobile', 'templates')
)

TEMPLATE_DIRS += TEMPLATE_DIRS_BASE

MOBILE = True
CACHE_BACKEND = 'file:///tmp/bookworm/django_cache_mobile'
DATE_FORMAT = "M j y"
SESSION_COOKIE_NAME = 'bookworm_mobile'
