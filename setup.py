#!/usr/bin/env python

from setuptools import setup


setup(
    name='celery-queued-once',
    version='0.2',
    description='Celery base task de-duplicating tasks',
    author='Educreations Engineering',
    packages=['queued_once'],
    install_requires=['celery', 'django >= 1.7'],
)
