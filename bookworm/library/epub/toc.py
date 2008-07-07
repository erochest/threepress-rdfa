#!/usr/bin/env python
from xml.etree import cElementTree as ET
import sys, logging
from namespaces import init_namespaces
from constants import NAMESPACES as NS
from constants import ENC

ns = NS['ncx']

# Helpers for dealing with TOC files

class TOC():
    '''A representation of an NCX TOC file:
    toc = holds a string representation of the toc
    parsed = the ET parsed version
    tree = a list of NavPoints, which have parent pointers and depth markers
    '''

    parsed = None
    doc_title = None

    def __init__(self, toc_string):
        self.toc = toc_string
        self.tree = []
        self.parse() 

    def parse(self):
        self.parsed = ET.fromstring(self.toc.encode(ENC))
        self.doc_title = self.parsed.findtext('.//{%s}docTitle/{%s}text' % (ns, ns)).strip()
        for navmap in self.parsed.findall('.//{%s}navMap' % (ns)):
            self._find_point(navmap)

    def __str__(self):
        res = ''
        for n in self.tree:
            res += n.__str__()
        return res

    def find_points(self, maxdepth=1):
        '''Return all the navpoints in the TOC having a maximum depth of maxdepth'''
        return [p for p in self.tree if p.depth <= maxdepth]

    def find_children_by_id(self, node_id):
        '''Find all children given the id of a node in the TOC'''
        node = None
        for n in self.tree:
            if n.element.get('id') == node_id:
                node = n
                break
        return self.find_children(node)

    def find_children(self, element):
        '''Find all the children of a node (for expand/collapse navigation)'''
        return [n for n in self.tree if n.parent.get('id') == element.element.get('id')]
    
    def _find_point(self, element, depth=1):
        for nav in element.findall('{%s}navPoint' % (ns)):
            n = NavPoint(nav, depth, element, self.doc_title, self.tree)
            self.tree.append(n)
            self._find_point(nav, depth+1)


def get_label(element):
    '''Gets the text label for any element'''
    if element is None:
        return None
    return element.findtext('.//{%s}text' % ns)

class NavPoint():
    '''Hold an individual navpoint, including its text, label and parent relationship.'''
    def __init__(self, element, depth=1, parent=None, doc_title=None, tree=None):
        self.element = element
        self.depth = depth
        self.parent = parent
        self.doc_title = doc_title
        self.tree = tree
        self.label = get_label(self.element)

        #logging.debug('Created navpoint for book "%s" with title "%s", parent label "%s" and depth %d' 
        #              % (self.doc_title, self.title(), get_label(self.parent), self.depth))

    def find_children(self):
        '''Returns all the children of this NavPoint'''
        return [n for n in self.tree if n.parent.get('id') == self.element.get('id')]

    def title(self):
        return self.element.findtext('.//{%s}text' % (ns)).strip()

    def order(self):
        return int(self.element.get('playOrder'))

    def href(self):
        return self.element.find('.//{%s}content' % (ns)).get('src')

    def id(self):
        return self.element.get('id')

    def __str__(self):
        res = ''
        for n in range(1,self.depth):
            res += ' '
        res += self.element.findtext('.//{%s}text' % ns)
        res += '\n'
        return res

    def __repr__(self):
        return "'%s' %s (%s) %d" % (self.doc_title, self.title(), self.href(), self.order())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        init_namespaces()
        toc = TOC(open(sys.argv[1]).read())
        print toc

    else:
        print "Usage: toc.py <NCX filename>"
