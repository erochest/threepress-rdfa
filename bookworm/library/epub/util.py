#!/usr/bin/env python

from lxml import etree as ET
from constants import ENC
import logging

def xml_from_string(xml):
    '''Django stores document data in unicode, but lxml doesn't like that if the
    document itself contains an encoding declaration, so convert from unicode
    first if necessary.'''
    if type(xml) == unicode:
        return ET.fromstring(xml.encode(ENC))
    return ET.fromstring(xml)    
