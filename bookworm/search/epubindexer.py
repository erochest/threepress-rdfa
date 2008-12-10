import os.path
from lxml.html.soupparser import fromstring
import logging, xapian
from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)
 
import bookworm.search.indexer as indexer
import bookworm.library.models as models
import bookworm.search.constants as constants

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('search.epubindexer')


def delete_epub(epub):
    '''Delete all the information in the index about a given epub'''
    user_archives = epub.user_archive.all()
    for user_archive in user_archives:
        username = user_archive.user.username

        # Delete from the book's own database
        indexer.delete_book_database(username, epub.id)
        user_db_location = indexer.get_user_database_path(username)
        if not os.path.exists(user_db_location):
            return

        user_db = indexer.create_user_database(username)
        # Also delete from the user's database
        for c in models.HTMLFile.objects.filter(archive=epub):
            book_id = c.id
            try:
                user_db.delete_document(book_id)
            except xapian.DocNotFoundError:
                log.warn("Couldn't find doc %s in search index" % epub.name)

        user_db.flush()

def index_user_library(user):
    '''Index all of the books in a user's library. Returns the
    number of books indexed.'''
    try:
        indexer.delete_user_database(user.username)
    except indexer.IndexingError:
        log.warn("Existing user database for user %s wasn't there; ignoring" % (user.username))

    indexer.create_user_database(user.username)    
    books = models.EpubArchive.objects.filter(owner=user)
    for b in books:
        index_epub([user.username], b)
    return len(books)
    
def index_epub(usernames, epub, chapter=None):
    '''Index parts of an epub book as a searchable document.
    If an HTMLFile object is passed, index only that chapter;
    otherwise index all chapters.'''
    book_id = epub.id
    book_title = epub.title
    chapters = []
    if chapter is None:
        chapters = [c for c in models.HTMLFile.objects.filter(archive=epub).order_by('id')]
    if chapter is not None:
        chapters.append(chapter)

    language = epub.get_language()

    databases = []

    for index, c in enumerate(chapters):
        content = c.render()
        clean_content = get_searchable_content(content)
        if c.title is not None and c.title is not u'':
            chapter_title = c.title
        else:
            chapter_title = 'Chapter %d' % index
        doc = indexer.create_search_document(book_id, book_title, clean_content,
                                             c.id, c.filename, chapter_title, author_name=epub.orderable_author,
                                             language=language)
        if doc is None:
            continue

        indexer.index_search_document(doc, clean_content)

        for username in usernames:
            user_db_path  = indexer.get_user_database_path(username)
            user_db = xapian.WritableDatabase(user_db_path, xapian.DB_CREATE_OR_OPEN)
            indexer.add_search_document(user_db, doc)

            book_db_path  = indexer.get_book_database_path(username, book_id)
            book_db = xapian.WritableDatabase(book_db_path, xapian.DB_CREATE_OR_OPEN)
            indexer.add_search_document(book_db, doc)

            user_db = None
            book_db = None
            
    epub.indexed = True
    epub.save()

def get_searchable_content(content):
    '''Returns the content of a chapter as a searchable field'''
    html = fromstring(content)
    ns = get_namespace(content)
    headers = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
    if ns is not None:
        temp_para = [ p.xpath('.//text()') for p in html.iter(tag='{%s}p' % ns)]
        for h in headers:
            temp_para += [ p.xpath('.//text()') for p in html.iter(tag='{%s}%s' % (ns, h))]
    else:
        temp_para = [ p.xpath('.//text()') for p in html.iter(tag='p')]
        for h in headers:
            temp_para += [ p.xpath('.//text()') for p in html.iter(tag='%s' % h)]
    paragraphs = []
    for p in temp_para:
        if p is not None:
            paragraphs.append(' '.join([i.strip().replace('\n',' ') for i in p]))


    return '\n'.join(paragraphs)

def get_namespace(content):
    '''Determines whether this content has a namespace or not'''
    html = fromstring(content)
    if html.find('{%s}p' % constants.XHTML_NS) is not None:
        return constants.XHTML_NS
    return None
    
