#!/usr/bin/env python
import logging

from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.contrib.auth.models import User

import search.constants as constants
from search import epubindexer
from library.models import *
from library.epub import InvalidEpubException

log = logging.getLogger('update-meta')
log.setLevel(logging.DEBUG)

# Update all of the metadata in all of the objects on the
# site
admin = User.objects.get(username='liza')

langs = [l[0] for l in settings.LANGUAGES]

log.info("Will index documents in languages: %s" % langs)

for e in EpubArchive.objects.all().order_by('id'):
    if e.indexed:
        continue

    log.info("Updating %s (%s)" % (e.title, e.name))
    if e.opf is None or e.opf == '':
        log.warn("Deleting " + e.name)
        e.delete()
        continue
    e.get_subjects()
    e.get_rights()
    e.get_language()
    e.get_publisher()
    e.get_identifier()

    # Get the user for this epub
    user = e.owner

    # Index it if it's in a language we can handle
    lang = e.get_major_language()
    if lang in langs:
        log.debug("Indexing with lang=%s" % lang)
        try:
            epubindexer.index_epub([user.username], e)
        except InvalidEpubException, e:
            log.error("Got invalid epub exception on this content: %s" % e)
    else:
        log.warn("skipping %s with lang=%s" % (e.title, lang))

import os
import os.path
import stat

perms = stat.S_IREAD | stat.S_IWRITE | stat.S_IROTH | stat.S_IWOTH | stat.S_IRGRP | stat.S_IWGRP
dir_perms = stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC | stat.S_IROTH | stat.S_IXOTH | stat.S_IWOTH | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP

# Update all the permissions
for users in os.listdir(settings.SEARCH_ROOT):
    os.chmod(os.path.join(settings.SEARCH_ROOT, users), dir_perms)
    for f in os.listdir(os.path.join(settings.SEARCH_ROOT, users)):
        os.chmod(os.path.join(settings.SEARCH_ROOT, users, f), dir_perms)
        if os.path.isdir(os.path.join(settings.SEARCH_ROOT, users, f)):
            for i in os.listdir(os.path.join(settings.SEARCH_ROOT, users, f)):
                os.chmod(os.path.join(settings.SEARCH_ROOT, users, f, i), perms)
        else:
            os.chmod(os.path.join(settings.SEARCH_ROOT, users, f), perms)            

log.info("Done.")
