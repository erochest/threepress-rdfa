#!/usr/bin/env python

import sys
import os
from datetime import datetime

path = '/Users/liza/threepress'
sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'threepress.settings'

from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site

from threepress import settings

pages = ('About', 'Contact', 'Download')
page_dir = '%s/threepress/search/templates/flatpages' % path

loaded = [t for t in FlatPage.objects.all()]

print "Current flatpages loaded: " + ', '.join([t.title for t in loaded])

for p in pages:
    if p not in [t.title for t in loaded]:
        url = p.lower().replace(' ', '_')
        fp = FlatPage(title=p,
                      url='/%s/' % (url),
                      content = open('%s/%s.html' % (page_dir, url)).read(),
                      enable_comments=False,
                      registration_required=False
                      )
        s = Site.objects.get(id=settings.SITE_ID)
        fp.save()
        fp.sites.add(s)
        fp.save()


print "New flatpages loaded: " + ', '.join([t.title for t in loaded])

