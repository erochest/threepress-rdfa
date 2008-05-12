#!/usr/bin/env python
from lxml import etree
import os, os.path, sys, logging, shutil

from settings import *

logging.basicConfig(level=logging.INFO)

def create_html(directory, tree):
    '''Generate the HTML files that make up each chapter in the TEI document.'''
    xslt = etree.parse(TEI2XHTML_XSLT)

    transform = etree.XSLT(xslt)
    for (i, element) in enumerate(tree.xpath('//tei:div[@type="chapter"]', namespaces={'tei': TEI})):
        processed = transform(element)
        f = '%s/%s/chapter-%d.html' % (directory, OEBPS, i + 1)
        _output_html(f, processed) 

    # Create the title page
    _output_html('%s/%s/title_page.html' % (directory, OEBPS), '<p>Title page</p>', False)

def _output_html(f, content, xml=True):
    if xml:                     
        xslt = etree.parse(HTMLFRAG2HTML_XSLT)        
        processed = content.xslt(xslt)
        html = etree.tostring(processed, encoding='utf-8', pretty_print=True, xml_declaration=False)                    
    else:
        html = '''<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>%s</title>
  </head>
  <body>
%s
  </body>
</html>
''' % ('test', content)
    logging.debug('Outputting file %s' % f)
    content = open(f, 'w')    
    content.write(html)
    content.close()

def create_content(directory, tree):
    '''Create the content file based on our TEI source'''
    xslt = etree.parse(TEI2OPF_XSLT)
    processed = tree.xslt(xslt)
    f = '%s/%s/%s' % (directory, OEBPS, CONTENT)
    _output_xml(f, processed)

def create_navmap(directory, tree):
    '''Create the navmap file based on our TEI source'''
    xslt = etree.parse(TEI2NCX_XSLT)
    processed = tree.xslt(xslt)
    f = '%s/%s/%s' % (directory, OEBPS, NAVMAP)
    _output_xml(f, processed)

def _output_xml(f, xml):
    logging.debug('Outputting file %s' % f)
    content = open(f, 'w')
    content.write(etree.tostring(xml, encoding='utf-8', pretty_print=True, xml_declaration=True))
    content.close()

def create_mimetype(directory):
    '''Create the mimetype file'''
    f = '%s/%s' % (directory, MIMETYPE)
    logging.debug('Creating mimetype file %s' % f)
    f = open(f, 'w')
    f.write(MIMETYPE_CONTENT)
    f.close()

def create_folders(directory):
    '''Create all the top-level directories in our package'''
    for f in FOLDERS:
        d = '%s/%s' % (directory, f)
        if not os.path.exists(d):
            os.mkdir(d)

def create_container(directory):
    '''Create the OPF container file'''
    f = '%s/%s/%s' % (directory, META, CONTAINER)
    logging.debug('Creating container file %s' % f)
    f = open(f, 'w')
    f.write(CONTAINER_CONTENTS)
    f.close()

def create_stylesheet(directory):
    '''Create the stylesheet file'''
    f = '%s/%s/%s' % (directory, OEBPS, CSS_STYLESHEET)
    logging.debug('Creating CSS file %s' % f)
    f = open(f, 'w')
    f.write(STYLESHEET_CONTENTS)
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
        directory = '%s/%s' % (BUILD, args[2])
    else:
        if not '.xml' in source:
            logging.error('Source file must have a .xml extension')
            return 1
        directory = '%s/%s' % (BUILD, os.path.basename(source).replace('.xml', ''))

    tree = etree.parse(source)

    if not os.path.exists(BUILD):
        os.mkdir(BUILD)

    if not os.path.exists(DIST):
        os.mkdir(DIST)

    if os.path.exists(directory):
        logging.debug('Removing previous output directory %s' % directory)
        shutil.rmtree(directory)

    logging.debug('Creating directory %s' % directory)
    os.mkdir(directory)

    # Create the epub content
    create_folders(directory)
    create_mimetype(directory)
    create_container(directory)
    create_stylesheet(directory)
    create_navmap(directory, tree)
    create_content(directory, tree)
    create_html(directory, tree)

    # Create the epub format
    os.chdir(directory)
    os.system('%s -v0Xq %s %s' % (ZIP, directory, MIMETYPE))
    os.system('%s -vrq %s * -x %s.zip %s' % (ZIP, directory, directory, MIMETYPE))
    os.rename('%s.zip' % directory, '%s.epub' % directory)
    shutil.move('%s.epub' % directory, DIST)

    return 0

if __name__ == '__main__':
    sys.exit(main(*sys.argv))
