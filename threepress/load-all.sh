#!/bin/sh

cd /home/liza/threepress/data

rm -rf db/threepress
rm pdf/*

books=$(for f in `find src -type f -name \*.xml` ; do basename -s .xml $f; done)

# Convert to TEI
for b in `echo $books`
do
  #echo "Converting $b"
  bin/convert.py src/$b.xml xsl/gut2tei.xsl reindex
done

# Copy TEI to static pages
rm /home/liza/threepress/threepress/search/templates/static/xml/*

for b in `echo $books`
do
    cp tei/$b.xml /home/liza/threepress/threepress/search/templates/static/xml/
done

rm /home/liza/threepress/threepress/search/templates/static/pdf/*
cp pdf/* /home/liza/threepress/threepress/search/templates/static/pdf/

cd /home/liza/threepress/data/epub

for b in `echo $books`
do
  bin/tei2epub.py ../tei/$b.xml
done

cd /home/liza/threepress/threepress

./clear-db.sh

for b in `echo $books`
do
  ./load-for-search.py ../data/tei/$b.xml
done


./run.sh