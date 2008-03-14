#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import etree

import os
import sys
import xapian

#sys.path.append('/home/liza/threepress')
sys.path.append('/Users/liza/threepress')
from threepress import settings


TEI = 'http://www.tei-c.org/ns/1.0'

db_dir = 'db/'

main_db = 'threepress'

indexer = xapian.TermGenerator()
stemmer = xapian.Stem("english")
indexer.set_stemmer(stemmer)

if len(sys.argv) < 3:
    print "Usage: convert.py xml-file xslt [re-index]"
    sys.exit(1)

xml = sys.argv[1]
xsl = sys.argv[2]
reindex = False
if len(sys.argv) > 3:
    reindex = True

tei_xsl = 'xsl/tei-xsl-5.9/p5/xhtml/tei.xsl'
fo_xsl  = 'xsl/tei-xsl-5.9/p5/fo/tei.xsl'
fop = 'fop'

out_file = xml.replace('src', 'tei')
out = open(out_file, 'w')

schema = 'src/teilite.xsd'
#xmlschema_doc = etree.parse(schema)
#xmlschema = etree.XMLSchema(xmlschema_doc)

tree = etree.parse(xml)
xslt = etree.parse(xsl)
root = tree.xslt(xslt)

# Check the document
#xmlschema.assertValid(root)
    
for element in root.iter():
    if element.text:
        element.text = element.text.replace('--', u'—')
        element.text = element.text.replace("'", u'’')
        element.text = element.text.replace('`', u'‘')
        words = []
        is_open = False
        for index, word in enumerate(element.text.split(' ')):
            if index == 0 and '"' in word:
                # Definitely an open quote at the beginning
                word = word.replace('"', u'“')
                is_open = True
            else:
                if '"' in word and is_open:
                    word = word.replace('"', u'”')
                    is_open = False
                elif '"' in word and not is_open:
                    word = word.replace('"', u'“')
                    is_open = True
            words.append(word)
        element.text = ' '.join([word for word in words]) 


main_database = xapian.WritableDatabase('%s/%s' % (db_dir, main_db), xapian.DB_CREATE_OR_OPEN)

id = root.xpath('/tei:TEI/@xml:id', namespaces={'tei':TEI})[0]

if reindex:
    # Open the database for update, creating a new database if necessary.

    # Delete the old database
    os.system('rm -rf %s/%s' % (db_dir, id))
    database = xapian.WritableDatabase('%s/%s' % (db_dir, id), xapian.DB_CREATE_OR_OPEN)


    body = root.xpath('//tei:body', namespaces={'tei':TEI})[0]
    for element in body.iter(tag='{%s}p' % TEI):
        para = element.text
        doc = xapian.Document()
        doc.set_data(para)
    
        indexer.set_document(doc)
        indexer.index_text(para)
    
        # Add the document to the database.
        para_id = element.xpath('@xml:id')[0].replace('id', '')
        chapter_id = element.xpath('parent::tei:div[@type="chapter"]/@xml:id', namespaces={'tei':TEI})[0]

        # Chapter ID is value 0
        doc.add_value(settings.SEARCH_CHAPTER_ID, chapter_id)

        # Document title is value 2
        doc.add_value(settings.SEARCH_DOCUMENT_TITLE, element.xpath('//tei:titleStmt/tei:title/text()', namespaces={'tei':TEI})[0])

        # Document ID is value 3
        doc.add_value(settings.SEARCH_DOCUMENT_ID, id)

        # Create the document with the paragraph ID from the XML
        database.replace_document(int(para_id), doc)
        main_database.replace_document(int(para_id), doc)
else:
    print "Skipping re-index..."
    
out.write(etree.tostring(root, encoding='utf-8', pretty_print=True, xml_declaration=True))
out.close()


# Also transform it to FO
fo_file = out_file
fo_file = fo_file.replace('tei/', 'fo/')
fo_file = fo_file.replace('xml', 'fo')

print "Writing out to %s" % fo_file

fo_out = open(fo_file, 'w')

xslt = etree.parse(fo_xsl)
fo = root.xslt(xslt)

fo_out.write(etree.tostring(fo, encoding='utf-8', pretty_print=True, xml_declaration=True))
fo_out.close()

pdf_file = "pdf/%s.pdf" % id

print "Converting from FO %s to PDF as %s" % (fo_file, pdf_file)
cmd = '%s %s -pdf %s &> pdf/log.txt' % (fop, fo_file, pdf_file)
os.system(cmd)


#out_file = out_file.replace('tei/', '')
#out_file = out_file.replace('xml', 'html')

print "Done."
