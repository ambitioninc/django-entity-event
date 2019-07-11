import re
from setuptools import setup, find_packages

# import multiprocessing to avoid this bug (http://bugs.python.org/issue15881#msg170215)
import multiprocessing
assert multiprocessing


def get_version():
    """
    Extracts the version number from the version.py file.
    """
    VERSION_FILE = 'entity_event/version.py'
    mo = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]', open(VERSION_FILE, 'rt').read(), re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError('Unable to find version string in {0}.'.format(VERSION_FILE))


setup(
    name='django-entity-event',
    version=get_version(),
    description='Newsfeed-style event tracking and subscription management for django-entity.',
    long_description=open('README.rst').read(),
    url='https://github.com/ambitioninc/django-entity-event',
    author='Erik Swanson',
    author_email='opensource@ambition.com',
    keywords='',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: Django',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Framework :: Django :: 2.2',
    ],
    license='MIT',
    install_requires=[
        'cached-property>=1.3.1',
        'Django>=2.0',
        'django-entity>=4.2.0',
        'jsonfield>=0.9.20',
        'six',
    ],
    tests_require=[
        'psycopg2',
        'django-nose>=1.4',
        'mock>=1.0.1',
        'coverage>=3.7.1',
        'freezegun',
        'django-dynamic-fixture',
        'flake8==3.5.0',
    ],
    test_suite='run_tests.run_tests',
    include_package_data=True,
    zip_safe=False,
)
