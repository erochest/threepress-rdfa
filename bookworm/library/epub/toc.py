#!/usr/bin/env python
from xml.etree import ElementTree as ET
import sys, logging
from namespaces import init_namespaces
from constants import NAMESPACES as NS

logging.basicConfig(level=logging.INFO)

ns = NS['ncx']

# Helpers for dealing with TOC files

class TOC():
    '''A representation of an NCX TOC file'''

    parsed = None
    tree = []

    def __init__(self, toc_filename):
        self.toc = open(toc_filename).read()

    def parse(self):
        self.parsed = ET.fromstring(self.toc)
        for navmap in self.parsed.findall('.//{%s}navMap' % (ns)):
            self._find_navpoint(navmap, 1)

    def __str__(self):
        if not self.parsed:
            self.parse()
        
        res = ''
        for n in self.tree:
            res += n.__str__()
        return res

    def _find_navpoint(self, element, depth):
        for nav in element.findall('{%s}navPoint' % (ns)):
            self._find_navpoint(nav, depth+1)
            n = NavPoint(nav, depth, element)
            self.tree.append(n)

class NavPoint():
    '''Hold an individual navpoint.'''
    def __init__(self, element, depth=1, parent=None):
        self.element = element
        self.depth = depth
        self.parent = parent
        logging.debug('Created navpoint with title "%s" and depth %d' % (self.title(), self.depth))

    def title(self):
        return self.element.findtext('.//{%s}text' % (ns)).strip()

    def order(self):
        return int(self.element.get('playOrder'))

    def href(self):
        return self.element.find('.//{%s}content' % (ns)).get('src')

    def __str__(self):
        res = ''
        for n in range(1,self.depth):
            res += ' '
        res += self.element.findtext('.//{%s}text' % ns)
        res += '\n'
        return res

    def __repr__(self):
        return "%s (%s) %d" % (self.title, self.href, self.order)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        init_namespaces()
        toc = TOC(sys.argv[1])
        toc.parse()
        print toc
    else:
        print "Usage: toc.py <NCX filename>"
