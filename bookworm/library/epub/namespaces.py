from xml.etree import ElementTree as ET
import logging
from constants import NAMESPACES as NS

def register_namespace(prefix, uri):
    logging.debug('Registering prefix "%s" with uri "%s"' % (prefix, uri))
    ET._namespace_map[uri] = prefix

def init_namespaces():
    for prefix in NS.keys():
        register_namespace(prefix, NS[prefix])
