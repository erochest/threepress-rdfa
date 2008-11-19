import os, logging, os.path, shutil
import xapian
from django.core.management import setup_environ
import bookworm.settings
import bookworm.search.constants as constants
setup_environ(bookworm.settings)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('search.indexer')

def create_search_document(book_id, book_title, content, chapter_id, chapter_filename, chapter_title='Untitled chapter', ns='', author_name='', language='en'):
    doc = xapian.Document()
    if not content:
        log.warn("Skipping blank content with id %s" % chapter_id)
        return None
    doc.set_data(content)
    doc.add_value(constants.SEARCH_BOOK_ID, unicode(book_id))
    doc.add_value(constants.SEARCH_BOOK_TITLE, unicode(book_title))
    doc.add_value(constants.SEARCH_CHAPTER_ID, unicode(chapter_id))
    doc.add_value(constants.SEARCH_CHAPTER_FILENAME, unicode(chapter_filename))
    doc.add_value(constants.SEARCH_CHAPTER_TITLE, unicode(chapter_title))
    doc.add_value(constants.SEARCH_NAMESPACE, ns)
    doc.add_value(constants.SEARCH_AUTHOR_NAME, unicode(author_name))
    doc.add_value(constants.SEARCH_LANGUAGE_VALUE, unicode(language))
    return doc

def add_search_document(database, doc):
    # Create the document with a generated unique chapter id
    unique_id =  int(doc.get_value(constants.SEARCH_CHAPTER_ID))
    database.replace_document(unique_id, doc)


def index_search_document(doc, content, weight=1):
    '''Create a new index and stemmer from the given document, 
    run the index, and return the indexer'''
    indexer = xapian.TermGenerator()
    stemmer = get_stemmer(doc.get_value(constants.SEARCH_LANGUAGE_VALUE))
    #log.debug("Using stemmer %s" % stemmer.get_description())

    indexer.set_stemmer(stemmer)
    indexer.set_document(doc)
    indexer.index_text(content, weight)
    return indexer

def add_to_index(indexer, content, weight=1):
    '''Add one or more terms to an existing index.'''
    indexer.index_text(content, weight)
    return indexer

def get_stemmer(lang_value):
    '''Converts from a variety of language values into a
    supported stemmer'''
    if '-' in lang_value:
        # We only want the first part in a multi-value lang, e.g. 'en' in 
        # 'en-US'
        language = lang_value.split('-')[0]
    elif '_' in lang_value:
        language = lang_value.split('_')[0]
    else:
        language = lang_value
    try:
        stemmer = xapian.Stem(language)    
    except xapian.InvalidArgumentError:
        log.warn("Got unknown language value '%s'; going to default lang '%s'" % 
                 (lang_value, constants.DEFAULT_LANGUAGE_VALUE))
        stemmer = xapian.Stem(constants.DEFAULT_LANGUAGE_VALUE)
    return stemmer
    
def create_user_database(username):
    '''Create a database that will hold all of the search content for an entire user'''
    user_db = get_user_database_path(username)
    log.debug("Creating user database at '%s'" % user_db)
    return xapian.WritableDatabase(user_db, xapian.DB_CREATE_OR_OPEN)

def delete_user_database(username):
    user_db = get_user_database_path(username)
    log.warn("Deleting user database at '%s'" % user_db)
    try:
        shutil.rmtree(user_db)
    except OSError,e:
        raise IndexingError(e)

def create_database(username, book_id=None):
    if book_id:
        return create_book_database(username, book_id)
    return create_user_database(username)

def create_book_database(username, book_id):
    user_path = get_user_database_path(username)
    if not os.path.exists(user_path):
        os.mkdir(user_path)
    book_db = get_book_database_path(username, book_id)
    log.debug("Creating book database at '%s'" % book_db)
    try:
        return xapian.WritableDatabase(book_db, xapian.DB_CREATE_OR_OPEN)    
    except xapian.DatabaseLockError:
        log.warn("Database '%s' was already open and locked; ignoring." % book_db)

def delete_book_database(username, book_id):
    book_db = get_book_database_path(username, book_id)
    if os.path.exists(book_db):
        log.warn("Deleting book database at '%s'" % book_db)
        shutil.rmtree(book_db)    
    else:
        log.warn("Tried to delete non-existent book db at '%s'" % book_db)


def get_database(username, book_id=None, create_if_missing=True):
    if book_id:
        path = get_book_database_path(username, book_id)
    else:
        path = get_user_database_path(username)
    log.debug("Returning database at '%s'" % path)
    try:
        db = xapian.Database(path)
    except xapian.DatabaseOpeningError:
        # We should have a database, but we don't.  This will
        # end up with no results, but create one anyway
        # because that's better than an exception.
        # 
        # If create_if_missing is overridden to be false,
        # then ignore this (the db had never been created)
        if create_if_missing:
            log.warn("lost database from path %s" % path)
            db = create_database(username, book_id)
        else:
            return None
    return db

def get_user_database_path(username):
    if not os.path.exists(bookworm.settings.SEARCH_ROOT):
        log.debug("Creating search root path at '%s'" % bookworm.settings.SEARCH_ROOT)
        os.mkdir(bookworm.settings.SEARCH_ROOT)
    return os.path.join(bookworm.settings.SEARCH_ROOT, username)

def get_book_database_path(username, book_id):
    user_db = get_user_database_path(username)
    book_db = os.path.join(user_db, str(book_id))
    return book_db

class IndexingError(Exception):
    pass
