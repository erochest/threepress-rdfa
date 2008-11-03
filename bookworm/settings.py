import os
import logging, logging.handlers

# Live site settings (others should override in locals.py)

DEBUG = False
TEMPLATE_DEBUG = DEBUG
   
DATABASE_ENGINE = 'mysql' 
DATABASE_NAME = 'bookworm'
DATABASE_USER = 'threepress'   
DATABASE_PASSWORD = '3press'   
DATABASE_HOST = ''             
DATABASE_PORT = ''             

SITE_ID = 2

# Django settings for bookworm project.

ADMINS = (
    ('Liza Daly', 'liza@threepress.org'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 2

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'j5+j92)+lry!gm1=*xl9#i=*gc2=opvfvew%8q2&4zx!v#6&1z'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "bookworm.library.context_processors.nav",
    "bookworm.library.context_processors.profile",
    "bookworm.library.context_processors.mobile",
    "bookworm.search.context_processors.search"
) 

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django_authopenid.middleware.OpenIDMiddleware',
    'django.middleware.http.SetRemoteAddrFromForwardedFor',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
#    'django.contrib.csrf.middleware.CsrfMiddleware'
    
)
ugettext = lambda s: s

# Only allow the list of languages available in Xapian
LANGUAGES = ( ('da', ugettext('Danish')), 
              ('nl', ugettext('Dutch')),
              ('en', ugettext('English')),
              ('fi', ugettext('Finnish')),
              ('fr', ugettext('French')),
              ('de', ugettext('German')),
              ('hu', ugettext('Hungarian')),
              ('it', ugettext('Italian')),
              ('no', ugettext('Norwegian')),
              ('pt', ugettext('Portuguese')),
              ('ro', ugettext('Romanian')),
              ('ru', ugettext('Russian')),
              ('es', ugettext('Spanish')),
              ('sv', ugettext('Swedish')),
              ('tr', ugettext('Turkish')))

ROOT_URLCONF = 'urls'

ROOT_PATH = os.path.dirname(__file__)


TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    '%s/library/templates/auth' % ROOT_PATH,    
    '%s/library/templates' % ROOT_PATH,
    '%s/library/templates/includes' % ROOT_PATH,    
    '%s/search/templates' % ROOT_PATH,    
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.flatpages',
    'django.contrib.sitemaps',
    'django.contrib.humanize',
    'django_authopenid',
    'django_evolution',
    'library',
    'search',
    )

AUTH_PROFILE_MODULE = "library.userpref"

ugettext = lambda s: s
LOGIN_URL = '/%s%s' % (ugettext('account/'), ugettext('signin/'))

DEFAULT_NUM_RESULTS = 20
DEFAULT_START_PAGE = 1
DEFAULT_ORDER_FIELD = 'created_time'
DEFAULT_ORDER_DIRECTION = 'desc'
VALID_ORDER_DIRECTIONS = ('asc', 'desc')
VALID_ORDER_FIELDS = ('created_time', 'title', 'orderable_author')

# Search database info
SEARCH_ROOT = os.path.join(ROOT_PATH, 'search')

MOBILE_DEVICE_AGENTS = ('kindle', 'iphone')
MOBILE = False

# Set up logging
LOG_DIR = '%s/log/' % ROOT_PATH
LOG_NAME = 'bookworm.log'

TEST_DATABASE_CHARSET = 'utf8'

SEARCH_ROOT = os.path.join(ROOT_PATH, 'search', 'dbs')


CACHE_BACKEND = 'file:///tmp/bookworm/django_cache'

XSLT_DIR = os.path.join(ROOT_PATH, 'library', 'xsl')
DTBOOK2XHTML = os.path.join(XSLT_DIR, 'dtbook2xhtml.xsl')

# Access time, filename/function#line-number message
log_formatter = logging.Formatter("[%(asctime)s %(filename)s/%(funcName)s#%(lineno)d] %(message)s")

try:
    # This should roll logs over at midnight and date-stamp them appropriately
    handler = logging.handlers.TimedRotatingFileHandler(filename="%s/%s" % (LOG_DIR, LOG_NAME),
                                                        when='midnight')
    handler.setFormatter(log_formatter)
    log = logging.getLogger('')
    log.setLevel(logging.DEBUG)
    log.addHandler(handler)

except IOError:
    pass
try:
    from local import *
except:
    pass

