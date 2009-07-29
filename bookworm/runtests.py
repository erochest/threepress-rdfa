#This file mainly exists to allow python setup.py test to work.
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'
test_dir = os.path.dirname(__file__)
sys.path.insert(0, test_dir)
sys.path.insert(0, os.path.join('..', test_dir))

from django.conf import settings
import bookworm.runner

def runtests():
    test_runner = bookworm.runner.run_tests('')
    failures = test_runner([], verbosity=1, interactive=True)
    sys.exit(failures)

if __name__ == '__main__':
    runtests()
