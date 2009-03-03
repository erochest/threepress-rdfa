
cd /home/liza/bookworm
python ./manage.py runfcgi --settings=settings maxchildren=10 \
maxspare=5 minspare=2 method=prefork socket=/home/liza/bookworm/log/django.sock pidfile=/home/liza/bookworm/log/django.pid 