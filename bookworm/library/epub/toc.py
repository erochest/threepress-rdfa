#!/usr/bin/env python
from lxml import etree as ET
import sys, logging

from bookworm.library.epub.constants import NAMESPACES as NS
from bookworm.library.epub.constants import ENC

from . import InvalidEpubException

log = logging.getLogger('epub.toc')

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
        self.parsed = xml_from_string(toc_string)

        if opf_string:
            self.spine = xml_from_string(opf_string)
    
        self.tree = []
        self.items = []
        self.lists = []
        self.parse() 
        self.parse_auxilliary()

    def parse_auxilliary(self):
        '''Parses any auxilliary nav lists and adds them to self.lists'''
        for l in self.parsed.findall('.//{%s}navList' % (NS['ncx'])):
            n = NavList(l, related_toc=self)
            self.lists.append(n)

    def parse(self):

        try:
            self.doc_title = self.parsed.findtext('.//{%s}docTitle/{%s}text' % (NS['ncx'], NS['ncx'])).strip()
        except AttributeError:
            log.warn("Did not get a docTitle from the NCX, although this is required.")
            self.doc_title = ''
            
           
        for navmap in self.parsed.findall('.//{%s}navMap' % (NS['ncx'])):
            self._find_point(navmap)

        # If we have a spine, we use that to define our next/previous tree, and then
        # find children of each spine element in the NCX, just for display
        if self.spine is not None:
            navpoint_map = dict()
            for np in self.parsed.xpath('//ncx:navPoint', namespaces=NS):
                navpoint_map.setdefault(np.get('id'),list()).append(np)

            item_map = dict()
            for item in self.spine.xpath('//opf:item', namespaces=NS):
                item_map[item.get('id')] = item
            
                

            for itemref in self.spine.xpath('//opf:spine/opf:itemref', namespaces=NS):
                item_ref = item_map.get(itemref.get('idref'))
                # If this is null, we have a pointer to a non-existent item;
                # bad but ignorable
                if item_ref is None:
                    continue
                item = item_ref
                # Get the navpoint that corresponds to this, if any!
                try:
                    np = navpoint_map.get(itemref.get('idref'),[])[0]
                    navpoint = NavPoint(np, doc_title=self.doc_title)
                except IndexError:
                    navpoint = None
                self.items.append(Item(item.get('id'), item.get('href'), item.get('media-type'), 
                                       navpoint=navpoint,
                                       linear=itemref.get('linear'),
                                       toc=self))

            
    def __str__(self):
        res = u''
        for n in self.tree:
            res += n.__str__()

        if self.items:
            res += u"\nOPF:\n"
            for n in self.items:
                res += n.__str__()

        if self.lists:
            res += u"\nNav Lists:\n"
            for n in self.lists:
                res += n.__str__()            
        return res.encode(ENC)

    def find_opf(self):
        '''Get the points in OPF order'''
        return self.items

    def first_item(self):
        '''According to the OPF spec, the first item in the book should be the first
        ordered itemref from the spine which has either 'linear=yes' or no 
        linear attribute, in which case 'yes' is the default.'''
        for i in self.items:
            if i.linear == 'yes':
                return i
        raise InvalidEpubException("Did not find any start items; malformed epub?")

            
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
        return [n for n in self.tree if n.parent is not None and n.parent.element.get('id') == element.element.get('id')]

    def find_descendants(self, element):
        '''Find all the descendants of a node'''
        return [n for n in self.tree if n != element and n.parent is not None and element in n.find_ancestors()]
        
    def _find_point(self, element, parent=None, depth=1):
        for nav in element.findall('{%s}navPoint' % (NS['ncx'])):
            n = NavPoint(nav, depth, parent=parent, doc_title=self.doc_title, tree=self.tree)
            self.tree.append(n)
            self._find_point(nav, parent=n, depth=depth+1)



class Item():
    '''An OPF item, which will itself may contain a navpoint.  

    The 'label' is an identifier that will be unique to this document;
    it will either be the NavPoint's label (if that exists) or the href.

    The 'title' is displayable to end users and should either be the
    label, or nothing.  If there is no title then the item will not show up in 
    any named href on the web site.'''

    def __init__(self, idref, href, media_type, linear='yes', navpoint=None, toc=None):
        self.id = idref
        self.href = href
        self.media_type = media_type
        self.navpoint = navpoint
        self.toc = toc
        if linear == None:
            self.linear = 'yes'
        else:
            self.linear = linear
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
        self.ancestors = []

    def find_ancestors(self):
        '''All the parents of our parent, which will allow for deeper exploration of the tree'''
        self._find_ancestor(self)
        return self.ancestors

    def _find_ancestor(self, navpoint):
        if navpoint.parent is None:
            return 
        self.ancestors.append(navpoint.parent)
        return self._find_ancestor(navpoint.parent)

    def find_children(self):
        '''Returns all the children of this NavPoint'''
        return [n for n in self.tree if n.parent is not None and n.parent.element.get('id') == self.element.get('id')]
        
    def find_descendants(self):
        '''Find all the descendants of a node'''
        return [n for n in self.tree if n != self and n.parent is not None and self in n.find_ancestors()]


    def title(self):
        text = self.element.findtext('.//{%s}text' % (NS['ncx']))
        if text:
            return text.strip()
        return ""

    def order(self):
        try:
            return int(self.element.get('playOrder'))
        except ValueError:
            log.warn("Got non-numeric value from playOrder: %s" % self.element.get('playOrder'))
        except TypeError:
            log.warn('Could not find playOrder value in %s' % self.element)
        # Get it by counting where we are from the parent; I want to use
        # self::*/position() here but lxml is complaining
        if not self.tree:
            return 0
        else:
            for index, x in enumerate(self.tree):
                if x.id == self.id:
                    return index + 1

    def href(self):
        return self.element.find('.//{%s}content' % (NS['ncx'])).get('src')

    def __str__(self):
        res = u''
        for n in range(1,self.depth):
            res += u' '
        text = self.element.findtext('.//{%s}text' % NS['ncx'])
        if type(text) == unicode:
            res += text
        else:
            res += unicode(text, encoding=ENC)
        res += u'\n'
        return res

    def __repr__(self):
        return "doc='%s' title=%s href=(%s) order=%d" % (self.doc_title, self.title(), self.href(), self.order())


class NavTarget(NavPoint):
    '''A subclass of NavPoint which is found in ncx:navList rather than ncx:navMap'''
    pass

class NavList():
    '''An auxilliary content list, as a list of illustrations'''
    def __init__(self, nav_list, related_toc):
        self.toc = related_toc
        self.nav_list = nav_list
        self.title = self.nav_list.findtext('.//{%s}text' % NS['ncx'])
        self.tree = []
        for t in self.nav_list.findall('.//{%s}navTarget' % NS['ncx']):
            self.tree.append(NavTarget(t, parent=None, doc_title=self.toc.doc_title))

    def __str__(self):
        return u''.join([n.__str__() for n in self.tree])
                        

def get_label(element):
    '''Gets the text label for any element'''
    if element is None:
        return None
    return element.findtext('.//{%s}text' % NS['ncx'])

def xml_from_string(xml):
    '''Django stores document data in unicode, but lxml doesn't like that if the
    document itself contains an encoding declaration, so convert from unicode
    first if necessary.'''
    if type(xml) == unicode:
        try:
            return ET.fromstring(xml.encode(ENC))
        except ET.XMLSyntaxError:
            raise InvalidEpubException("Unable to parse file")
    return ET.fromstring(xml)    
                            
if __name__ == '__main__':
    log.basicConfig(level=logging.INFO)
        
    if len(sys.argv) == 2:
        toc = TOC(open(sys.argv[1]).read())
        print toc

    elif len(sys.argv) == 3:
        toc = TOC(open(sys.argv[1]).read(),
                  open(sys.argv[2]).read())
        print toc
    else:
        print "Usage: toc.py <NCX filename> [OPF filename]"
