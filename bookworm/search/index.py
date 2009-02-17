import logging, os, sys, uuid

from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)

from django.contrib.auth.models import User

import bookworm.search.constants as constants
from bookworm.search import epubindexer
from bookworm.library.models import HTMLFile, EpubArchive
from bookworm.library.epub import InvalidEpubException

log = logging.getLogger('update-meta')
log.setLevel(logging.INFO)

lockfile = '/tmp/update-meta.lck'
try:
    os.mkdir(lockfile)
except OSError:
    # Make sure cron sees our complaint
    sys.stderr.write("Shutting down because already running.  Am I stuck?\n")
    sys.exit()


def index():
    for e in EpubArchive.objects.filter(identifier='').order_by('id')[0:10]:
        log.debug("Processing %s" % e.title)
        for h in HTMLFile.objects.filter(archive=e):
            try:
                if not h.processed_content:
                    log.debug("Rendering HTML content for %s:%s" % (e.title, h.filename))
                    h.render()
            except Exception, e:
                log.error(e)
                h.words = "[Unsupported language]"
            h.words = epubindexer.get_searchable_content(h.processed_content)                
            h.save()
            
        e.get_subjects()
        e.get_rights()
        e.get_language()
        e.get_publisher()
        identifier = e.get_identifier()
        if identifier == None or identifier == '' or identifier == u'':
            log.debug("Creating identifier because none present")
            e.identifier = 'urn:uuid:' + str(uuid.uuid4())
        e.save()

os.rmdir(lockfile)

if __name__ == '__main__':
    sys.exit(index())
