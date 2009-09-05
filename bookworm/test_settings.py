from settings import *
from local import *

# You will get the best testing performance out of sqlite3/in-memory, but not all tests
# will pass.  This is normal.
# Comment out to use MySQL for testing (Django will create a separate test database)
DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sql$
DATABASE_NAME = ':memory:'             # Or path to database file if using sqlite3.

MEDIA_ROOT = os.path.join(ROOT_PATH, 'library', 'test-data', 'storage')

DEBUG=False
log.setLevel(logging.ERROR)
SITE_ID = 1
TESTING = True
MEDIA_URL = '/test-static/'
