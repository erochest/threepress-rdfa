import logging

logging.basicConfig(level=logging.INFO)

# Local settings; should be overriden for each checkout
DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASE_ENGINE = 'mysql' 
DATABASE_NAME = 'bookworm2'
DATABASE_USER = 'threepress'   # Not used with sqlite3.
DATABASE_PASSWORD = '3press'   # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
