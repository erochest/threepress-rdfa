#!/usr/bin/env python

import sys
import os
from lxml import etree
from datetime import datetime

TEI = 'http://www.tei-c.org/ns/1.0'

if not len(sys.argv) == 2:
    print "Usage: load-for-search path-to-tei-xml"
    sys.exit(2)

parser = etree.XMLParser(remove_blank_text=True)
xml = etree.parse(sys.argv[1], parser)

sys.path.append('/home/liza/threepress')

import threepress

os.environ['DJANGO_SETTINGS_MODULE'] = 'threepress.settings'

from threepress.search.models import Document, Chapter

print "Current documents loaded: " + ', '.join([t.title for t in Document.objects.all()])


def xpath(field, xml):
    t = xml.xpath(field, namespaces={'tei': TEI})
    if t:
        x = t[0]
        if hasattr(x, 'text'):
            return x.text.strip()
        return x
    return ""

def chapter(xml_root, db_obj, document):
    chapter_ordinal = 1
    chapter_count = len(xml_root.xpath("tei:div[@type='chapter']", namespaces={'tei': TEI}))
    if chapter_count == 1:
        chapter_default_name = 'Content'
    else:
        chapter_default_name = 'Chapter'
    for chapter in xml_root.xpath("tei:div[@type='chapter']", namespaces={'tei': TEI}):
        chapter_id = xpath('@xml:id', chapter)
        chapter_title = xpath('tei:head[1]', chapter) or chapter_default_name
        content = etree.tostring(chapter, encoding='utf-8', pretty_print=True, xml_declaration=False)
        c = db_obj.chapter_set.create(id=chapter_id,
                                      title=chapter_title,
                                      document=document,
                                      ordinal=chapter_ordinal,
                                      content=content)
        chapter_ordinal += 1        

title = xpath('//tei:title', xml)
author = xpath('//tei:author', xml)
id = xpath('/tei:TEI/@xml:id', xml)

d = Document(id=id,
             title=title,
             author=author,
             add_date=datetime.now(),
             pub_date=datetime.now()
             )

d.save()

print "Adding chapters for id %s" %  d.id


# Do we have parts?
if len(xml.xpath("//tei:div[@type='part']", namespaces={'tei': TEI})) > 0:
    print "Adding parts"
    part_ordinal = 1
    for part in xml.xpath("//tei:div[@type='part']", namespaces={'tei': TEI}):
        part_id = xpath('@xml:id', part)
        part_title = xpath('tei:head[1]', part) 
        p = d.part_set.create(id=part_id,
                              title=part_title,
                              ordinal=part_ordinal,
                              label='part')
        chapter(part, p, d)
        part_ordinal += 1
else:
    print "Adding chapters only"
    chapter(xml.xpath("//tei:body", namespaces={'tei': TEI})[0], d, d)


print d.chapter_set.all()





