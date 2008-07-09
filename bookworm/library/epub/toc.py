#!/usr/bin/env python
from lxml import etree as ET
import sys, logging
from namespaces import init_namespaces
from constants import NAMESPACES as NS
from constants import ENC
import util

# Helpers for dealing with TOC file and <spine> elements

class TOC():
    '''A representation of an NCX TOC file:
    toc = holds a string representation of the toc
    parsed = the ET parsed version
    tree = a list of NavPoints, which have parent pointers and depth markers
    '''

    parsed = None
    doc_title = None
    spine = None

    def __init__(self, toc_string, opf_string=None):
        '''If provided, an optional opf file will inform the parsing of the ncx file'''
        self.toc = toc_string
        if opf_string:
            self.spine = util.xml_from_string(opf_string)
    
        self.tree = []
        self.items = []
        self.parse() 

    def parse(self):
        self.parsed = util.xml_from_string(self.toc)
        self.doc_title = self.parsed.findtext('.//{%s}docTitle/{%s}text' % (NS['ncx'], NS['ncx'])).strip()

        for navmap in self.parsed.findall('.//{%s}navMap' % (NS['ncx'])):
            self._find_point(navmap)

        # If we have a spine, we use that to define our next/previous tree, and then
        # find children of each spine element in the NCX, just for display
        if self.spine is not None:

            for itemref in self.spine.xpath('//opf:spine/opf:itemref', namespaces=NS):
                item = self.spine.xpath('//opf:item[@id="%s"]' % itemref.get('idref'),
                                        namespaces=NS)[0]
                assert item is not None
                # Get the navpoint that corresponds to this, if any!
                try:
                    np = self.parsed.xpath('//ncx:navPoint[@id="%s"]' % itemref.get('idref'), namespaces=NS)[0]
                    navpoint = NavPoint(np, doc_title=self.doc_title)
                except IndexError:
                    navpoint = None
                self.items.append(Item(item.get('id'), item.get('href'), item.get('media-type'), navpoint,
                                       toc=self))

            
    def __str__(self):
        res = u''
        for n in self.tree:
            res += n.__str__()

        if self.items:
            res += u"\nOPF:\n"
            for n in self.items:
                res += n.__str__()

        return res.encode(ENC)

    def find_opf(self):
        '''Get the points in OPF order'''
        pass

    def find_points(self, maxdepth=1):
        '''Return all the navpoints in the TOC having a maximum depth of maxdepth'''
        return [p for p in self.tree if p.depth <= maxdepth]

    def find_point_by_id(self, node_id):
        '''For accessing a node in the tree from an id'''
        for n in self.tree:
            if n.element.get('id') == node_id:
                return n

    def find_item_by_id(self, item_id):
        '''For accessing a node in the item list from an id'''
        for n in self.items:
            if n.id == item_id:
                return n

    def find_next_item(self, item):
        i = self._get_index_by_item(item)
        if i == len(self.items) - 1:
            # This is the last item
            return None
        return self.items[i + 1]

    def find_previous_item(self, item):
        i = self._get_index_by_item(item)
        if i == 0:
            return None
        return self.items[i - 1]

    def _get_index_by_item(self, item):
        try:
            i = self.items.index(item)
            return i
        except ValueError:
            for j in self.items:
                if j.id == item.id:
                    return j
        return 0

    def find_children_by_id(self, node_id):
        '''Find all children given the id of a node in the TOC'''
        node = self.find_point_by_id(node_id)
        return self.find_children(node)

    def find_children(self, element):
        '''Find all the children of a node (for expand/collapse navigation)'''
        return [n for n in self.tree if n.parent.get('id') == element.element.get('id')]
    
    def _find_point(self, element, depth=1):
        for nav in element.findall('{%s}navPoint' % (NS['ncx'])):
            n = NavPoint(nav, depth, element, self.doc_title, self.tree)
            self.tree.append(n)
            self._find_point(nav, depth+1)


def get_label(element):
    '''Gets the text label for any element'''
    if element is None:
        return None
    return element.findtext('.//{%s}text' % NS['ncx'])

class Item():
    '''An OPF item, which will itself may contain a navpoint.  

    The 'label' is an identifier that will be unique to this document;
    it will either be the NavPoint's label (if that exists) or the href.

    The 'title' is displayable to end users and should either be the
    label, or nothing.  If there is no title then the item will not show up in 
    any named href on the web site.'''

    def __init__(self, idref, href, media_type, navpoint=None, toc=None):
        self.id = idref
        self.href = href
        self.media_type = media_type
        self.navpoint = navpoint
        self.toc = toc
        if self.navpoint is not None:
            self.label = navpoint.label
            self.title = navpoint.label
        else:
            self.label = href
            self.title = None

    def __str__(self):
        '''Print the depth relative to its navpoint, if it exists'''
        if self.navpoint and self.toc:
            # Get the real navpoint from the tree
            navpoint = self.toc.find_point_by_id(self.navpoint.id)
            return navpoint.__str__()
        return unicode(self.label, encoding=ENC) + u"\n"

class NavPoint():
    '''Hold an individual navpoint, including its text, label and parent relationship.'''
    def __init__(self, element, depth=1, parent=None, doc_title=None, tree=None):
        self.element = element
        self.id = self.element.get('id')
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
        text = self.element.findtext('.//{%s}text' % (NS['ncx']))
        if text:
            return text.strip()
        return ""

    def order(self):
        return int(self.element.get('playOrder'))

    def href(self):
        return self.element.find('.//{%s}content' % (NS['ncx'])).get('src')

    def __str__(self):
        res = u''
        for n in range(1,self.depth):
            res += u' '
        text = self.element.findtext('.//{%s}text' % NS['ncx'])
        if type(text) == unicode:
            res += text
            pass
        else:
            res += unicode(text, encoding=ENC)
        res += u'\n'
        return res

    def __repr__(self):
        return "'%s' %s (%s) %d" % (self.doc_title, self.title(), self.href(), self.order())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
        
    if len(sys.argv) == 2:
        toc = TOC(open(sys.argv[1]).read())
        print toc

    elif len(sys.argv) == 3:
        toc = TOC(open(sys.argv[1]).read(),
                  open(sys.argv[2]).read())
        print toc
    else:
        print "Usage: toc.py <NCX filename> [OPF filename]"
