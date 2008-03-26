#!/usr/bin/env python
from lxml import etree
import os, os.path, sys, logging, shutil

MIMETYPE = 'mimetype'
META = 'META-INF'
CONTENT = 'content.opf'
NAVMAP = 'toc.ncx'
OEBPS = 'OEBPS'
FOLDERS  = (META, OEBPS)
CONTAINER = 'container.xml'
TEI2OPF_XSLT='../xsl/tei2opf.xsl'
TEI2NCX_XSLT='../xsl/tei2ncx.xsl'

CONTAINER_CONTENTS = '''
<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
'''

logging.basicConfig(level=logging.DEBUG)

def create_content(dir, xml_file):
    tree = etree.parse(xml_file)
    xslt = etree.parse(TEI2OPF_XSLT)
    processed = tree.xslt(xslt)
    file = '%s/%s/%s' % (dir, OEBPS, CONTENT)
    _output_xml(file, processed)

def create_navmap(dir, xml_file):
    tree = etree.parse(xml_file)
    xslt = etree.parse(TEI2NCX_XSLT)
    processed = tree.xslt(xslt)
    file = '%s/%s/%s' % (dir, OEBPS, NAVMAP)
    _output_xml(file, processed)

def _output_xml(file, xml):
    logging.debug('Outputting file %s' % file)
    content = open(file, 'w')
    content.write(etree.tostring(xml, encoding='utf-8', pretty_print=True, xml_declaration=True))
    content.close()



def create_mimetype(dir):
    file = '%s/%s' % (dir, MIMETYPE)
    logging.debug('Creating mimetype file %s' % file)
    f = open(file, 'w')
    f.write('application/epub+zip')
    f.close()

def create_folders(dir):

    for f in FOLDERS:
        d = '%s/%s' % (dir, f)
        if not os.path.exists(d):
            os.mkdir(d)

def create_container(dir):
    file = '%s/%s/%s' % (dir, META, CONTAINER)
    logging.debug('Creating container file %s' % file)
    f = open(file, 'w')
    f.write(CONTAINER_CONTENTS)
    f.close()

def main(*args):
    '''Create an epub-format zip file given a source XML file.
       Based on the tutorial from: http://www.jedisaber.com/eBooks/tutorial.asp
    '''
    if len(args) < 3:
        print 'Usage: create-epub.py directory-for-output tei-source-file'
        return 1

    dir = args[1]
    source = args[2]

    if os.path.exists(dir):
        logging.debug('Removing previous output directory %s' % dir)
        shutil.rmtree(dir)
    os.mkdir(dir)

    create_folders(dir)
    create_mimetype(dir)
    create_container(dir)
    create_navmap(dir, source)
    create_content(dir, source)

    return 0
if __name__ == '__main__':
    sys.exit(main(*sys.argv))
