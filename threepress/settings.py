# Django settings for threepress project.

from local import *


ADMINS = (
     ('Liza Daly', 'liza@threepress.org')
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

SITE_ID = 1

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
SECRET_KEY = '-w0ducdj)&#lpsdfsdf8nb($ncs10ibnc(asdasdsdk;lokolyv(#&1299s8iw2g=9l_$v'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware'
)

ROOT_URLCONF = 'threepress.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    '%s/threepress/search/templates' % DIR_ROOT
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.flatpages',
    'django.contrib.sitemaps',
    'threepress.search',
    'threepress.epub'
    
)

DB_DIR = '%s/data/db' % DIR_ROOT
RESULTS_PAGESIZE = 20

# Xapian settings (values)
SEARCH_CHAPTER_ID = 0
SEARCH_ORDINAL = 1
SEARCH_DOCUMENT_TITLE = 2
SEARCH_DOCUMENT_ID = 3

SORT_RELEVANCE = 0
SORT_ORDINAL = 1

TEI = 'http://www.tei-c.org/ns/1.0'

EPUB_VALIDATOR_TEMP_DIR = "%s/data/epub-validator-temp" % DIR_ROOT

JAVA = '/usr/bin/java'
JAVA_JAR_ARG = '-jar'
EPUBCHECK_DIR = "%s/data/epub/test" % DIR_ROOT
EPUBCHECK_JAR = "epubcheck-1.0.1.jar" 

