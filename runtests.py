#!/usr/bin/env python

# Django must be set up before we import our libraries and run our tests

import os
import sys

import django
from django.conf import settings


if os.environ.get('TEST_WITH_REDIS'):
    CACHE = {
        'BACKEND': 'django_redis.cache.RedisCache',
        "LOCATION": 'redis://127.0.0.1:6379/1',
    }
else:
    CACHE = {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'localhost',
        'OPTIONS': {
            'MAX_ENTRIES': 2 ** 32,
        },
    }


settings.configure(
    TESTING=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        },
    },
    CACHES={
        'default': CACHE,
    },
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
    ),
    MIDDLEWARE_CLASSES=('django.middleware.common.CommonMiddleware',),
    BROKER_URL='memory://',
    CELERY_RESULT_BACKEND='cache',
    CELERY_CACHE_BACKEND='memory',
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
)

if django.VERSION[:2] >= (1, 7):
    django.setup()


# Run tests

from django.test.runner import DiscoverRunner

test_runner = DiscoverRunner(verbosity=1)
failures = test_runner.run_tests(['queued_once.tests'])
if failures:
    sys.exit(failures)
