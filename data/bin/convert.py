#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import etree
import os, sys, logging, subprocess
from os.path import realpath, dirname
import xapian

sys.path.append('/home/liza/threepress')
from threepress import settings

db_dir = 'db/'
main_db = 'threepress'

logging.basicConfig(level=logging.WARNING)

indexer = xapian.TermGenerator()
stemmer = xapian.Stem("english")
indexer.set_stemmer(stemmer)

if len(sys.argv) < 3:
    logging.error("Usage: convert.py xml-file xslt [re-index]")
    sys.exit(1)

xml = sys.argv[1]
xsl = sys.argv[2]

reindex = False
if len(sys.argv) > 3:
    reindex = True


tei_xsl = 'xsl/tei-xsl-5.9/p5/xhtml/tei.xsl'
fo_xsl  = 'xsl/tei-xsl-5.9/p5/fo/tei.xsl'
fop = '/usr/local/bin/fop'

out_file = xml.replace('src', 'tei')
out = open(out_file, 'w')

schema = 'src/teilite.xsd'
xmlschema_doc = etree.parse(schema)
xmlschema = etree.XMLSchema(xmlschema_doc)

tree = etree.parse(xml)
xslt = etree.parse(xsl)
root = tree.xslt(xslt)

# Check the document
try:
    xmlschema.assertValid(root)
except etree.DocumentInvalid, e:
    logging.error(e)

    
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

id = root.xpath('/tei:TEI/@xml:id', namespaces={'tei':settings.TEI})[0]

if reindex:
    # Open the database for update, creating a new database if necessary.

    # Delete the old database
    os.system('rm -rf %s/%s' % (db_dir, id))
    database = xapian.WritableDatabase('%s/%s' % (db_dir, id), xapian.DB_CREATE_OR_OPEN)


    body = root.xpath('//tei:body', namespaces={'tei':settings.TEI})[0]
    for element in body.iter(tag='{%s}p' % settings.TEI):
        para = element.text
        doc = xapian.Document()
        doc.set_data(para)
    
        indexer.set_document(doc)
        indexer.index_text(para)
    
        # Add the document to the database.
        para_id = element.xpath('@xml:id')[0].replace('id', '')
        chapter_id = element.xpath('parent::tei:div[@type="chapter"]/@xml:id', namespaces={'tei':settings.TEI})[0]

        # Chapter ID is value 0
        doc.add_value(settings.SEARCH_CHAPTER_ID, chapter_id)

        # Document title is value 2
        doc.add_value(settings.SEARCH_DOCUMENT_TITLE, element.xpath('//tei:titleStmt/tei:title/text()', namespaces={'tei':settings.TEI})[0])

        # Document ID is value 3
        doc.add_value(settings.SEARCH_DOCUMENT_ID, id)

        # Create the document with the paragraph ID from the XML
        database.replace_document(int(para_id), doc)
        main_database.replace_document(int(para_id), doc)
else:
    logging.debug("Skipping re-index...")
    
out.write(etree.tostring(root, encoding='utf-8', pretty_print=True, xml_declaration=True))
out.close()


# Also transform it to FO
fo_file = out_file
fo_file = fo_file.replace('tei/', 'fo/')
fo_file = fo_file.replace('xml', 'fo')

logging.debug("Writing out to %s" % fo_file)

fo_out = open(fo_file, 'w')

xslt = etree.parse(fo_xsl)
fo = root.xslt(xslt)

fo_out.write(etree.tostring(fo, encoding='utf-8', pretty_print=True, xml_declaration=True))
fo_out.close()

pdf_file = "pdf/%s.pdf" % id
path = "%s/.." % realpath(dirname(sys.argv[0]))

pdf_file = "%s/%s" % (path, pdf_file)
fo_file = "%s/%s" % (path, fo_file)

logging.debug("Converting from FO %s to PDF as %s" % (fo_file, pdf_file))


subprocess.check_call([fop, '-r', fo_file, '-pdf', pdf_file])

logging.debug("Done.")
