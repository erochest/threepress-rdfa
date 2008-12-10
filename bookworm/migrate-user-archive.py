import logging

from django.core.management import setup_environ
import settings
setup_environ(settings)

import bookworm.library.models as models

# For each archive, create a new record for it and its user,
# and copy the last_chapter_read value to the new model

for epub in models.EpubArchive.objects.filter(user_archive=None):
    logging.debug("Creating new archive for '%s'" % epub.title)
    ua = models.UserArchive.objects.create(archive=epub,
                                           user=epub.owner,
                                           last_chapter_read=epub.last_chapter_read)
    
    
