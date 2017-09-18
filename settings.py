import os

from django.conf import settings


def configure_settings():
    """
    Configures settings for manage.py and for run_tests.py.
    """
    if not settings.configured:
        # Determine the database settings depending on if a test_db var is set in CI mode or not
        test_db = os.environ.get('DB', None)
        if test_db is None:
            db_config = {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'ambition_dev',
                'USER': 'postgres',
                'PASSWORD': '',
                'HOST': 'db'
            }
        elif test_db == 'postgres':
            db_config = {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'USER': 'postgres',
                'NAME': 'entity_event',
            }
        elif test_db == 'sqlite':
            db_config = {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'entity_event',
            }
        else:
            raise RuntimeError('Unsupported test DB {0}'.format(test_db))

        settings.configure(
            TEST_RUNNER='django_nose.NoseTestSuiteRunner',
            NOSE_ARGS=['--nocapture', '--nologcapture', '--verbosity=1'],
            MIDDLEWARE_CLASSES=(),
            DATABASES={
                'default': db_config,
            },
            TEMPLATES=[
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'APP_DIRS': True,
                },
            ],
            INSTALLED_APPS=(
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.admin',
                'entity',
                'entity_event',
                'entity_event.tests',
                'django_nose',
            ),
            ROOT_URLCONF='entity_event.urls',
            DEBUG=False,
        )
