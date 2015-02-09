#!/usr/bin/env python

from setuptools import setup


setup(
    name='celery-queued-once',
    version='0.1',
    description='Celery base task de-duplicating tasks',
    author='Corey Farwell',
    author_email='corey@educreations.com',
    packages=['queued_once'],
    install_requires=['celery', 'django'],
)
