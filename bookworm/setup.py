import ez_setup, sys, os

ez_setup.use_setuptools()
from setuptools import setup, find_packages
test_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join('..', test_dir))
setup(
    name = "Bookworm",
    version = "1.0",
    packages = find_packages(),
    author = "Liza Daly",
    author_email = "liza@threepress.org",
    description = "Django application to read and search ePub ebooks",
    url = "http://code.google.com/p/threepress/",
    install_requires = ['Django <1.1',
                        'cssutils',
                        'python-openid',
                        'twill',
                        'lxml >2.0',
                        'BeautifulSoup'],
    include_package_data = True,
    test_suite= 'runtests.runtests',
)
