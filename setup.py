#!/usr/bin/env python

import os
import sys

from setuptools import setup


if sys.argv[-1] == 'publish':
    os.system('python setup.py register sdist bdish_wheel upload')
    sys.exit()


setup(
    name='celery-queued-once',
    version='0.1',
    description='Celery base task de-duplicating tasks',
    author='Educreations Engineering',
    author_email='engineering@educreations.com',
    url='https://github.com/educreations/celery-queued-once',
    packages=['queued_once'],
    install_requires=['celery', 'django >= 1.7'],
)
