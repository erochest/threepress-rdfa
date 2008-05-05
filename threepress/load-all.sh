#!/bin/sh

cd /home/liza/threepress/data

rm -rf db/threepress
rm pdf/*

books='The-Mysterious-Affair-at-Styles_Agatha-Christie Pride-and-Prejudice_Jane-Austen Emma_Jane-Austen The-Cask-of-Amontillado_Edgar-Allan-Poe A-Tale-of-Two-Cities_Charles-Dickens Sense-and-Sensibility_Jane-Austen'

#books='The-Mysterious-Affair-at-Styles_Agatha-Christie Pride-and-Prejudice_Jane-Austen Emma_Jane-Austen Sense-and-Sensibility_Jane-Austen'

# Convert to TEI
for b in `echo $books`
do
  echo "Converting $b"
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
  bin/create.py ../tei/$b.xml
done

cd /home/liza/threepress/threepress

./clear-db.sh

for b in `echo $books`
do
  ./load-for-search.py ../data/tei/$b.xml
done





./load-flatpages.py

./run.sh