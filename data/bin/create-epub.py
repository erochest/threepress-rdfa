#!/usr/bin/env python
from lxml import etree
import os, os.path, sys, logging, shutil

TEI = 'http://www.tei-c.org/ns/1.0'
MIMETYPE = 'mimetype'
META = 'META-INF'
CONTENT = 'content.opf'
NAVMAP = 'toc.ncx'
OEBPS = 'OEBPS'
FOLDERS = (META, OEBPS)
CONTAINER = 'container.xml'
TEI2OPF_XSLT = '../xsl/tei2opf.xsl'
TEI2NCX_XSLT = '../xsl/tei2ncx.xsl'
TEI2XHTML_XSLT = '../xsl/tei-xsl-5.9/p5/xhtml/tei.xsl'

CONTAINER_CONTENTS = '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
'''

logging.basicConfig(level=logging.DEBUG)

def create_html(dir, tree):

    xslt = etree.parse(TEI2XHTML_XSLT)
    shell = tree

    transform = etree.XSLT(xslt)
    for (i, element) in enumerate(tree.xpath('//tei:div[@type="chapter"]', namespaces={'tei': TEI})):
        processed = transform(element)
        file = '%s/%s/chapter-%d.html' % (dir, OEBPS, i + 1)
        _output_html(file, processed)

def _output_html(file, tree):
    html = '''<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>%s</title>
</head>
<body>
%s
</body>
</html>
''' % ('test', etree.tostring(tree, encoding='utf-8', pretty_print=True, xml_declaration=False))
    logging.debug('Outputting file %s' % file)
    content = open(file, 'w')    
    content.write(html)
    content.close()

def create_content(dir, tree):
    xslt = etree.parse(TEI2OPF_XSLT)
    processed = tree.xslt(xslt)
    file = '%s/%s/%s' % (dir, OEBPS, CONTENT)
    _output_xml(file, processed)

def create_navmap(dir, tree):
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
    tree = etree.parse(source)

    create_navmap(dir, tree)
    create_content(dir, tree)
    create_html(dir, tree)

    # Create the epub format
    os.chdir(dir)
    os.system('zip -v0X pandp mimetype')
    os.system('zip -vr pandp * -x pandp.zip mimetype')
    os.system('mv pandp.zip pandp.epub')

    return 0
if __name__ == '__main__':
    sys.exit(main(*sys.argv))
