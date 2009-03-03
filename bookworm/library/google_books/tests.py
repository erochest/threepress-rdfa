from search import Request
from lxml import etree
from nose.tools import *

def test_query():
    r = Request('intitle:pride+intitle:prejudice')
    assert r
    resp = r.get()
    assert resp
    
def test_title():
    r = Request('intitle:pride+intitle:prejudice')
    resp = r.get()
    as_text = etree.tostring(resp.tree)
    assert 'Pride' in as_text
    assert 'Jane Austen' in as_text
    
def test_entries():
    r = Request('intitle:tale+intitle:cities')
    resp = r.get()
    assert_true(len(resp.entries) > 0)
    
def test_publisher():
    r = Request('intitle:tale+intitle:cities')
    resp = r.get()
    found_publisher = False
    for e in resp.entries:
        p = e.publisher
        if p is not None and p != '':
            found_publisher = True
    assert found_publisher

def test_pages():
    r = Request('intitle:tale+intitle:cities')
    resp = r.get()
    found_pages = False
    for e in resp.entries:
        p = e.pages
        if p is not None and p != '':
            found_pages = True
    assert found_pages

def test_description():
    r = Request('intitle:tale+intitle:cities')
    resp = r.get()
    found_description = False
    for e in resp.entries:
        p = e.description
        if p is not None and p != '':
            found_description = True
    assert found_description

def test_thumbnail():
    r = Request('intitle:tale+intitle:cities')
    resp = r.get()
    href = None
    for e in resp.entries:
        p = e.thumbnail
        if p is not None and 'http' in p:
            href = p
    assert href
    # Originally I was checking that what got returned
    # was really an image, but Google somehow figures out
    # that the request isn't coming from a real browser 
    # and instead it returns 401 Unauthorized.
    # Even setting the user-agent didn't work.


def test_preview():
    r = Request('intitle:tale+intitle:cities')
    resp = r.get()
    e = resp.entries[0]
    assert_true('http' in e.preview)

def test_info():
    r = Request('intitle:tale+intitle:cities')
    resp = r.get()
    e = resp.entries[0]
    assert_true('http' in e.info)

def test_viewability():
    r = Request('intitle:tale+intitle:cities')
    resp = r.get()
    e = resp.entries[0]
    assert_true(e.viewability)


    
