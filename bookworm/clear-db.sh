#!/bin/sh

if [ "$HOSTNAME" = "host.threepress.org" ]; then 
    echo 'Cowardly refusing to let you delete the live database.'
    exit
fi

if [ "$1" = "" ]; then
    echo "Clearing library"
    ./manage.py sqlclear library > clear.sql
fi
if [ "$1" = "auth" ]; then
    echo "Clearing $1"
    ./manage.py sqlclear auth > clear.sql
fi
if [ "$1" = "openid" ]; then
    echo "Clearing $1"
    ./manage.py sqlclear django_authopenid > clear.sql
fi
if [ "$1" = "all" ]; then
    echo "Clearing $1"
    ./manage.py sqlclear library auth django_authopenid > clear.sql
fi
mysql -u threepress --password=3press bookworm < clear.sql
./manage.py syncdb
