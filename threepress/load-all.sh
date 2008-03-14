#!/bin/sh

cd /home/liza/threepress/data

rm -rf db/threepress
rm pdf/*

bin/convert.py src/masac10.xml xsl/gut2tei.xsl reindex
bin/convert.py src/pandp10.xml xsl/gut2tei.xsl reindex
bin/convert.py src/emma10.xml xsl/gut2tei.xsl reindex
bin/convert.py src/cask.xml xsl/gut2tei.xsl reindex
bin/convert.py src/2city11.xml xsl/gut2tei.xsl reindex

rm /home/liza/threepress/threepress/search/templates/static/pdf/*
cp pdf/* /home/liza/threepress/threepress/search/templates/static/pdf/


cd /home/liza/threepress/threepress

./clear-db.sh
./load-for-search.py ../data/tei/masac10.xml 
./load-for-search.py ../data/tei/pandp10.xml
./load-for-search.py ../data/tei/emma10.xml
./load-for-search.py ../data/tei/cask.xml
./load-for-search.py ../data/tei/2city11.xml

./load-flatpages.py

./run.sh