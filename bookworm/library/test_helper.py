import os.path

from django.conf import settings

from bookworm.library.testmodels import MockEpubArchive
from bookworm.library import models as library_models

# Data for public epub documents
DATA_DIR = unicode(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test-data/data'))

STORAGE_DIR = settings.MEDIA_ROOT

# Local documents should be added here and will be included in tests,
# but not in the svn repository
PRIVATE_DATA_DIR = u'%s/private' % DATA_DIR


def get_file(f):
    '''Get a file from either the public or private data directories'''
    return get_filehandle(f).read()

def get_filehandle(f):
    '''Get a file from either the public or private data directories'''
    path = get_filepath(f)
    return open(path)

def get_filepath(f):
    data_dir = u'%s/%s' % (DATA_DIR, f)
    if os.path.exists(data_dir):
        return data_dir

    data_dir = u'%s/%s' % (PRIVATE_DATA_DIR, f)
    if os.path.exists(data_dir):
        return data_dir    
    raise OSError('Could not find file %s in either data dir' % f)


