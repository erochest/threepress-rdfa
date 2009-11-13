import os
import logging, logging.handlers

# Live site settings (others should override in local.py)
ROOT_PATH = os.path.dirname(__file__)

DEBUG = False
TEMPLATE_DEBUG = DEBUG
TESTING = False # Override this in test_settings.py

DATABASE_ENGINE = 'mysql' 
DATABASE_NAME = 'bookworm'
DATABASE_USER = 'threepress'   
DATABASE_PASSWORD = '3press'   
DATABASE_HOST = ''             
DATABASE_PORT = ''             

SITE_ID = 1

# base url: leave '' if deployed at webserver root. don't forget the trailing slash
# Example: 
# BASE_URL = 'apps/bookworm/'
BASE_URL = ''

# Django settings for bookworm project.

ADMINS = (
    ('Bookworm', 'bookworm@oreilly.com'),
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

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(ROOT_PATH, 'library', 'storage')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
MEDIA_URL = '/static/'
ORM_MEDIA_URL = '/orm-media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

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
    "bookworm.library.context_processors.mobile",
    "bookworm.library.context_processors.local_settings",
    "bookworm.library.context_processors.profile",
    "bookworm.search.context_processors.search"
) 


MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'bookworm.middleware.Language',    
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django_authopenid.middleware.OpenIDMiddleware',
    'django.middleware.http.SetRemoteAddrFromForwardedFor',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'bookworm.minidetector.Middleware',
    'bookworm.middleware.Mobile',
    'bookworm.api.middleware.SSLRedirect',
    'bookworm.api.middleware.APIKeyCheck',

)

ugettext = lambda s: s

# Only allow the list of languages for which we have translations
LANGUAGES = (
  ('de', ugettext('German')),
  ('en', ugettext('English')),
  ('da', ugettext('Danish')),
  ('fi', ugettext('Finnish')),
  ('it', ugettext('Italian')),
  ('es', ugettext('Spanish')),
#  ('zh-tw', ugettext('Simplified Chinese')),
#  ('he', ugettext('Hebrew')),
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    '%s/library/templates/auth' % ROOT_PATH,    
    '%s/library/templates/host' % ROOT_PATH,
    '%s/library/templates' % ROOT_PATH,
    '%s/library/templates/includes' % ROOT_PATH,    
    '%s/search/templates' % ROOT_PATH,    
    '%s/librarything/templates' % ROOT_PATH,    
    '%s/orm/templates' % ROOT_PATH,    
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
    'bookworm.minidetector',
    'bookworm.library',
    'bookworm.search',
    'bookworm.librarything',
    'bookworm.mobile',
    'bookworm.api',
    )

AUTH_PROFILE_MODULE = "library.userpref"

ugettext = lambda s: s
LOGIN_URL = '/%s%s%s' %  (BASE_URL, ugettext('account/'), ugettext('signin/'))
SITE_ID = 2

DEFAULT_NUM_RESULTS = 20
DEFAULT_START_PAGE = 1
DEFAULT_ORDER_FIELD = 'created_time'
DEFAULT_ORDER_DIRECTION = 'desc'
VALID_ORDER_DIRECTIONS = ('asc', 'desc')
VALID_ORDER_FIELDS = ('created_time', 'title', 'orderable_author')

# Search database info
SEARCH_ROOT = os.path.join(ROOT_PATH, 'search')

# Are we running with mobile settings on?
MOBILE = False
FORCE_SCRIPT_NAME = ''

# Domain which to redirect requests that are coming from a mobile device
MOBILE_HOST = 'http://m.bookworm.oreilly.com/'

# Hosting credit
HOSTING_CREDIT = "O'Reilly Media"
HOSTING_CREDIT_URL = 'http://oreilly.com/'

# Email reply-to address
REPLYTO_EMAIL = 'donotreply@oreilly.com'
DEFAULT_FROM_EMAIL = REPLYTO_EMAIL

# The admin address that's displayed on the site in help pages
DISPLAY_ADMIN_EMAIL = 'bookworm@oreilly.com'
ADMIN_EMAIL = DISPLAY_ADMIN_EMAIL

# Set up logging
LOG_DIR = '%s/log/' % ROOT_PATH
LOG_NAME = 'bookworm.log'

TEST_DATABASE_CHARSET = 'utf8'
TEST_DATABASE_COLLATION='utf8_unicode_ci'

SEARCH_ROOT = os.path.join(ROOT_PATH, 'search', 'dbs')

CACHE_BACKEND = 'file:///tmp/bookworm/django_cache'
CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True
CACHE_TEMPLATE_TIMEOUT = 60 * 60 * 1

DATE_FORMAT = "l, N j Y"
LIBRARYTHING_KEY = ''

# Access time, filename/function#line-number message
log_formatter = logging.Formatter("[%(asctime)s %(filename)s/%(funcName)s#%(lineno)d] %(message)s")

# This should roll logs over at midnight and date-stamp them appropriately
handler = logging.handlers.TimedRotatingFileHandler(filename="%s/%s" % (LOG_DIR, LOG_NAME),
                                                        when='midnight')
handler.setFormatter(log_formatter)
log = logging.getLogger('')
log.setLevel(logging.INFO)
log.addHandler(handler)

# If set, the templates will load jQuery locally instead of from Google
OFFLINE = False

# Google Analytics key
ANALYTICS_KEY = 'UA-162955-4'

# The email addresses of the users who should receive an error email 
# (should be a list)
ERROR_EMAIL_RECIPIENTS = (ADMINS[0][1], )

# The URL for the epubcheck webservice
EPUBCHECK_WEBSERVICE = 'http://threepress.org/epubcheck-service/' 

# Apps to test
TEST_APPS = ('library',)

TESTING = False

# Feedbooks OPDS feed
FEEDBOOKS_OPDS_FEED = 'http://feedbooks.com/books/top.atom'

# Always upload files to the filesystem
FILE_UPLOAD_HANDLERS = ("django.core.files.uploadhandler.TemporaryFileUploadHandler",)

# Maximum number of CSS files to attempt to display at once
MAX_CSS_FILES = 10

# API key field name
API_FIELD_NAME = 'api_key'

# Hostname (no trailing slash)
HOSTNAME = 'http://bookworm.oreilly.com'

# Secure hostname (no trailing slash)
SECURE_HOSTNAME = 'https://bookworm.oreilly.com'

XSLT_DIR = os.path.join(ROOT_PATH, 'library', 'xsl')
DTBOOK2XHTML = os.path.join(XSLT_DIR, 'dtbook2xhtml.xsl')

# Don't ever try to call epubcheck -- useful in testing offline
SKIP_EPUBCHECK = False

CUSTOMER_SERVICE_URL = 'http://getsatisfaction.com/oreilly'
CUSTOMER_SERVICE_NAME = 'Get Satisfaction'
  
try:
    from local import *
except ImportError:
    pass
 
