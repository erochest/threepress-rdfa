import logging, os, sys, uuid

from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)

from django.contrib.auth.models import User

import bookworm.search.constants as constants
from bookworm.search import epubindexer
from bookworm.library.models import HTMLFile, EpubArchive
from bookworm.library.epub import InvalidEpubException
import bookworm.library.epub.toc as util

log = logging.getLogger('update-meta')
log.setLevel(logging.DEBUG)

lockfile = '/tmp/update-meta.lck'
try:
    os.mkdir(lockfile)
except OSError:
    # Make sure cron sees our complaint
    sys.stderr.write("Shutting down because already running.  Am I stuck?\n")
    sys.exit()

def index():

    to_delete = []
    for e in EpubArchive.objects.filter(identifier='').order_by('id')[0:10]:
        log.debug("Processing %s" % e.title)
        # Make sure this is valid at all
        try:
            util.xml_from_string(e.opf)
        except InvalidEpubException:
            log.debug("Will delete %s (Bookworm ID %s)" % (e.title, e.id))
            to_delete.append(e)
            continue
            
        for h in HTMLFile.objects.filter(archive=e):
            try:
                if not h.processed_content:
                    log.debug("Rendering HTML content for %s:%s" % (e.title, h.filename))
                    h.render()
            except Exception, e1:
                log.error(e1)
                h.words = "[Unsupported language]"
            if not h.words:
                h.words = epubindexer.get_searchable_content(h.processed_content)                
            h.save()
        log.debug("Done processing HTML for %s" % e.title)
        # If we get None from any of these metadata items, then the document is
        # invalid
        e.get_subjects()
        e.get_rights()
        e.get_language()
        e.get_publisher()
        e.get_identifier()
        log.debug("Saving %s" % e.title)
        e.save()

    for d in to_delete:
        log.warn("Deleting document %s" % d.name)
        d.delete()

os.rmdir(lockfile)

if __name__ == '__main__':
    sys.exit(index())
