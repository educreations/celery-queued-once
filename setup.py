#!/usr/bin/env python

import os
import sys

from setuptools import setup


if sys.argv[-1] == "publish":
    os.system("python setup.py register sdist bdish_wheel upload")
    sys.exit()


setup(
    name="celery-queued-once",
    version="0.2",
    description="Celery base task de-duplicating tasks",
    author="Educreations Engineering",
    author_email="engineering@educreations.com",
    url="https://github.com/educreations/celery-queued-once",
    packages=["queued_once"],
    install_requires=["celery>=3.1.17,<4.0", "Django>=1.8.0,<1.10"],
)
