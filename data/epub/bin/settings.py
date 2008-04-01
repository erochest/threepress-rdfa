from os.path import realpath, dirname
import sys

# Path of the executable
path = realpath(dirname(sys.argv[0]))

# TEI is not included in the distribution
TEI2XHTML_XSLT = '%s/../../xsl/tei-xsl-5.9/p5/xhtml/tei.xsl' % path

# XSL templates
XSLT_DIR = '%s/../xsl' % path
TEI2OPF_XSLT = '%s/tei2opf.xsl' % XSLT_DIR
TEI2NCX_XSLT = '%s/tei2ncx.xsl' % XSLT_DIR
HTMLFRAG2HTML_XSLT = '%s/htmlfrag2html.xsl' % XSLT_DIR

# You should not have to change any items below this as they are standard
# OPF filenames

# Directory where our output will go
DIST = '%s/../../../threepress/search/templates/static/epub' % path

# Working directory
BUILD = '%s/../build' % path

# zip command
ZIP = 'zip'

# Name of our OPF mimetype file
MIMETYPE = 'mimetype'
MIMETYPE_CONTENT = 'application/epub+zip'

CSS_STYLESHEET = 'stylesheet.css'
STYLESHEET_CONTENTS = '''
body { font-family: serif }
'''

META = 'META-INF'

CONTENT = 'content.opf'

NAVMAP = 'toc.ncx'

OEBPS = 'OEBPS'

# Top-level folders in our epub directory
FOLDERS = (META, OEBPS)

CONTAINER = 'container.xml'
CONTAINER_CONTENTS = '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
'''

# TEI namespace
TEI = 'http://www.tei-c.org/ns/1.0'
