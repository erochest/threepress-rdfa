#!/bin/sh

./manage.py sqlclear search > clear.sql
mysql -u threepress --password=3press threepress < clear.sql
./manage.py syncdb
