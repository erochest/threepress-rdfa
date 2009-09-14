#!/bin/bash

# Example Bookworm API client implementation using curl.  This script 
# expects three arguments: the Bookworm installation URL and a valid API key.
#
# Curl must be installed.
# The Bookworm URL should have no trailing slash (e.g. http://bookworm.oreilly.com)

BW=$1
KEY=$2

# Upload a document
curl -F epub_data=@test.epub -F api_key=$KEY $1/api/documents/ -D result.txt

# Get a list of documents (your earlier document should appear)
curl $1/api/documents/?api_key=$KEY -o library-list.html

# Download a particular document by BW id (this uses the document we just uploaded)
url=`cat result.txt|grep "Content-Location" | tr -d "\n" | tr -d "\r" `
curl ${url:17}?api_key=$KEY > result.epub

