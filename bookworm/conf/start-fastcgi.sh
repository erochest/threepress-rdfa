
cd /home/liza/bookworm2
python ./manage.py runfcgi --settings=settings maxchildren=10 \
maxspare=5 minspare=2 method=prefork socket=/home/liza/bookworm2/log/django.sock pidfile=/home/liza/bookworm2/log/django.pid 