#!/usr/bin/env python
import logging
import os
import os.path
import stat
import sys

from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.contrib.auth.models import User

import bookworm.search.constants as constants
from bookworm.search import epubindexer
from bookworm.library.models import *
from bookworm.library.epub import InvalidEpubException

log = logging.getLogger('update-meta')
log.setLevel(logging.DEBUG)

lockfile = '/tmp/update-meta.lck'
try:
    os.mkdir(lockfile)
except OSError:
    log.warn('Shutting down because already running')
    sys.exit()

langs = [l[0] for l in settings.LANGUAGES]

log.info("Will index documents in languages: %s" % langs)

for e in EpubArchive.objects.filter(is_deleted=True).order_by('id'):
    log.warn("Deleting %s because 'is_deleted' was True" % e.name)
    result = epubindexer.delete_epub(e)
    if result:
        e.delete(true_delete=True)
    
for e in EpubArchive.objects.filter(can_be_indexed=True,is_deleted=False).order_by('id'):
    if e.indexed:
        continue

    log.info("Updating %s (%s)" % (e.title, e.name))
    if e.opf is None or e.opf == '':
        #log.warn("Deleting % because OPF was empty " % e.name)
        e.delete(true_delete=True)
        continue

    e.get_subjects()
    e.get_rights()
    e.get_language()
    e.get_publisher()
    e.get_identifier()

    # Get the users for this epub
    users = [u.user for u in e.user_archive.all()]

    # Index it if it's in a language we can handle
    lang = e.get_major_language()
    if lang in langs:
        log.debug("Indexing with lang=%s" % lang)
        try:
            for user in users:
                epubindexer.index_epub([user.username], e)
        except InvalidEpubException, ex:
            log.error("Got invalid epub exception on this content: %s" % ex)
            e.can_be_indexed=False
            e.save()
    else:
        log.warn("skipping %s with lang=%s" % (e.title, lang))
        e.can_be_indexed=False
        e.save()
 
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
os.rmdir(lockfile)
