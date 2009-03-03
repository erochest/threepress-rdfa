from lxml import etree
import os, sys, logging, subprocess, os.path
import xapian
from django.core.management import setup_environ
import settings
setup_environ(settings)


logging.basicConfig(level=logging.DEBUG)

indexer = xapian.TermGenerator()
stemmer = xapian.Stem("english")
indexer.set_stemmer(stemmer)

def create_user_database(username):
    '''Create a database that will hold all of the search content for an entire user'''
    if not os.path.exists(settings.SEARCH_ROOT):
        os.mkdir(settings.SEARCH_ROOT)
    return xapian.WritableDatabase(os.path.join(settings.SEARCH_ROOT, username), xapian.DB_CREATE_OR_OPEN)
