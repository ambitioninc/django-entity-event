Contributing
============

Contributions and issues are most welcome! All issues and pull requests are
handled through github on the `ambitioninc repository`_. Also, please check for
any existing issues before filing a new one. If you have a great idea but it
involves big changes, please file a ticket before making a pull request! We
want to make sure you don't spend your time coding something that might not fit
the scope of the project.

.. _ambitioninc repository: https://github.com/ambitioninc/django-entity-event/issues

Running the tests
-----------------

To get the source source code and run the unit tests, run::

    $ git clone git://github.com/ambitioninc/django-entity-event.git
    $ cd django-entity-event
    $ virtualenv env
    $ . env/bin/activate
    $ python setup.py install
    $ coverage run setup.py test
    $ coverage report --fail-under=100

While 100% code coverage does not make a library bug-free, it significantly
reduces the number of easily caught bugs! Please make sure coverage is at 100%
before submitting a pull request!

Code Quality
------------

For code quality, please run flake8::

    $ pip install flake8
    $ flake8 .

Code Styling
------------
Please arrange imports with the following style

.. code-block:: python

    # Standard library imports
    import os

    # Third party package imports
    from mock import patch
    from django.conf import settings

    # Local package imports
    from entity_event.version import __version__

Please follow `Google's python style`_ guide wherever possible.

.. _Google's python style: http://google-styleguide.googlecode.com/svn/trunk/pyguide.html

Building the docs
-----------------

When in the project directory::

    pip install -r requirements/docs.txt
    python setup.py build_sphinx
    open docs/_build/html/index.html

Release Checklist
-----------------

Before a new release, please go through the following checklist:

* Bump version in entity_event/version.py
* Add a release note in docs/release_notes.rst
* Git tag the version
* Upload to pypi::

    pip install wheel
    python setup.py sdist bdist_wheel upload

Vulnerability Reporting
-----------------------

For any security issues, please do NOT file an issue or pull request on github!
Please contact `security@ambition.com`_ with the GPG key provided on `Ambition's
website`_.

.. _security@ambition.com: mailto:security@ambition.com
.. _Ambition's website: http://ambition.com/security/
