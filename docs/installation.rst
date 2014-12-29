Installation
============

Django Entity Event is compatible with Python versions 2.7, 3.3, and
3.4.

Installation with Pip
---------------------

Entity Event is available on PyPi. It can be installed using ``pip``::

    pip install django-entity-event

Use with Django
---------------

To use Entity Event with django, first be sure to install it and/or
include it in your ``requirements.txt`` Then include
``'entity_event'`` in ``settings.INSTALLED_APPS``. After it is
included in your installed apps, run::

    ./manage.py migrate entity_event

if you are using South_. Otherwise run::

    ./manage.py syncdb

.. _South: http://south.aeracode.org/

