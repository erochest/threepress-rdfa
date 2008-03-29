#!/usr/bin/env python
from lxml import etree
import os, os.path, sys, logging, shutil

from settings import *

logging.basicConfig(level=logging.DEBUG)

def create_html(dir, tree):
    '''Generate the HTML files that make up each chapter in the TEI document.'''
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
    '''Create the content file based on our TEI source'''
    xslt = etree.parse(TEI2OPF_XSLT)
    processed = tree.xslt(xslt)
    file = '%s/%s/%s' % (dir, OEBPS, CONTENT)
    _output_xml(file, processed)

def create_navmap(dir, tree):
    '''Create the navmap file based on our TEI source'''
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
    '''Create the mimetype file'''
    file = '%s/%s' % (dir, MIMETYPE)
    logging.debug('Creating mimetype file %s' % file)
    f = open(file, 'w')
    f.write(MIMETYPE_CONTENT)
    f.close()

def create_folders(dir):
    '''Create all the top-level directories in our package'''
    for f in FOLDERS:
        d = '%s/%s' % (dir, f)
        if not os.path.exists(d):
            os.mkdir(d)

def create_container(dir):
    '''Create the OPF container file'''
    file = '%s/%s/%s' % (dir, META, CONTAINER)
    logging.debug('Creating container file %s' % file)
    f = open(file, 'w')
    f.write(CONTAINER_CONTENTS)
    f.close()

def main(*args):
    '''Create an epub-format zip file given a source XML file.
       Based on the tutorial from: http://www.jedisaber.com/eBooks/tutorial.asp
    '''
    if len(args) < 2:
        print 'Usage: create-epub.py tei-source-file [alternate output directory]'
        return 1

    source = args[1]

    if len(args) > 2:
        dir = args[2]
    else:
        if not '.xml' in source:
            logging.error('Source file must have a .xml extension')
            return 1
        dir = '%s/%s' % (BUILD, os.path.basename(source).replace('.xml', ''))

    tree = etree.parse(source)

    if not os.path.exists(BUILD):
        os.mkdir(BUILD)

    if not os.path.exists(DIST):
        os.mkdir(DIST)

    if os.path.exists(dir):
        logging.debug('Removing previous output directory %s' % dir)
        shutil.rmtree(dir)

    logging.debug('Creating directory %s' % dir)
    os.mkdir(dir)

    # Create the epub content
    create_folders(dir)
    create_mimetype(dir)
    create_container(dir)
    create_navmap(dir, tree)
    create_content(dir, tree)
    create_html(dir, tree)

    # Create the epub format
    os.chdir(dir)
    os.system('%s -v0X %s %s' % (ZIP, dir, MIMETYPE))
    os.system('%s -vr %s * -x %s.zip %s' % (ZIP, dir, dir, MIMETYPE))
    os.rename('%s.zip' % dir, '%s.epub' % dir)
    shutil.move('%s.epub' % dir, DIST)

    return 0

if __name__ == '__main__':
    sys.exit(main(*sys.argv))
