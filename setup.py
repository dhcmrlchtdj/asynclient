#!/usr/bin/env python3

from setuptools import setup
import asynclient as ac

setup(
    name="asynclient",
    version=ac.__version__,
    description=ac.__description__,

    author="niris",
    author_email="nirisix@gmail.com",
    url="https://github.com/dhcmrlchtdj/asynclient",

    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "License :: OSI Approved :: MIT License",

        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: 3.4",

        "Topic :: Internet :: WWW/HTTP",
    ],
)
