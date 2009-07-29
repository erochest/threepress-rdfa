from settings_mobile import *
from local import *

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sql$
DATABASE_NAME = ':memory:'             # Or path to database file if using sqlite3.
#DATABASE_NAME = '/tmp/bookworm.db'             # Or path to database file if using sqlite3.

MEDIA_ROOT = os.path.join(ROOT_PATH, 'library', 'test-data', 'storage')

DEBUG=False
log.setLevel(logging.ERROR)
SITE_ID = 1





