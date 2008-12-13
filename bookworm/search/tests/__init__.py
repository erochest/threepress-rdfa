import logging

from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)
from django.test.utils import setup_test_environment
from django.db import connection

log = logging.getLogger('search.tests.init')

def setup():
    setup_test_environment()
    connection.creation.create_test_db(verbosity=1, autoclobber=True)

def teardown():
    connection.creation.destroy_test_db('bookworm')
    #teardown_test_environment()
