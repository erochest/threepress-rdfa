#!/usr/bin/env python
import sys, os, logging
from lxml import etree
from datetime import datetime
from settings import TEI

logging.basicConfig(level=logging.WARNING)

if not len(sys.argv) == 2:
    logging.error("Usage: load-for-search path-to-tei-xml")
    sys.exit(2)

parser = etree.XMLParser(remove_blank_text=True)
xml = etree.parse(sys.argv[1], parser)

sys.path.append('/home/liza/threepress')

os.environ['DJANGO_SETTINGS_MODULE'] = 'threepress.settings'

from search.models import Document

logging.info("Current documents loaded: " + ', '.join([t.title for t in Document.objects.all()]))

def xpath(field, xml):
    t1 = xml.xpath(field, namespaces={'tei': TEI})
    if t1:
        x = t1[0]
        if hasattr(x, 'text'):
            return x.text.strip()
        return x
    return u""

def chapter(xml_root, db_obj, document, ordinal_start):
    chapter_ordinal = ordinal_start

    chapter_count = len(xml_root.xpath("tei:div[@type='chapter']", namespaces={'tei': TEI}))

    if chapter_count == 1:
        chapter_default_name = 'Complete story'
    else:
        chapter_default_name = 'Chapter'

    for chapter in xml_root.xpath("tei:div[@type='chapter']", namespaces={'tei': TEI}):
        chapter_id = xpath('@xml:id', chapter)
        chapter_title = xpath('tei:head[1]', chapter) or chapter_default_name
        content = etree.tostring(chapter, encoding='utf-8', pretty_print=True, xml_declaration=False)
        logging.debug("Setting ordinal to %d " % chapter_ordinal)
        c = db_obj.chapter_set.create(id=chapter_id,
                                      title=chapter_title,
                                      document=document,
                                      ordinal=chapter_ordinal,
                                      content=content)
        chapter_ordinal += 1

    return chapter_ordinal

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

logging.info("Adding content for id %s" %  d.id)
chapter_ordinal = 1

# Do we have parts?
if len(xml.xpath("//tei:div[@type='part']", namespaces={'tei': TEI})) > 0:
    part_ordinal = 1
    for part in xml.xpath("//tei:div[@type='part']", namespaces={'tei': TEI}):
        part_id = xpath('@xml:id', part)
        part_title = xpath('tei:head[1]', part) 
        logging.debug("Adding part", part_title.encode('utf-8'))
        p = d.part_set.create(id=part_id,
                              title=part_title,
                              ordinal=part_ordinal,
                              label='part')
        chapter_ordinal = chapter(part, p, d, chapter_ordinal)
        part_ordinal += 1
else:
    logging.info("Adding chapters only")
    chapter_ordinal = chapter(xml.xpath("//tei:body", namespaces={'tei': TEI})[0], d, d, chapter_ordinal)


logging.debug(d.chapter_set.all())





