#!/bin/sh

./manage.py sqlclear library > clear.sql
mysql -u threepress --password=3press bookworm < clear.sql
./manage.py syncdb
