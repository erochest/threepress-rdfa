import logging, os, sys

from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.contrib.auth.models import User

import bookworm.search.constants as constants
from bookworm.search import epubindexer
from bookworm.library.models import HTMLFile
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
    for h in HTMLFile.objects.filter(words__isnull=True):
        try:
            if not h.processed_content:
                h.render()
                h.words = epubindexer.get_searchable_content(h.processed_content)
        except:
            import traceback
            print traceback.format_exc()
            h.words = "[Unsupported language]"
        
        h.save()

os.rmdir(lockfile)

if __name__ == '__main__':
    sys.exit(index())
