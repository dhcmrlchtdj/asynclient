#!/usr/bin/env python3

from setuptools import setup
import asynclient as ac

setup(
    name="asynclient",
    version=ac.__version__,
    description="An asynchronous HTTP client.",

    author="niris",
    author_email="nirisix@gmail.com",
    url="https://github.com/dhcmrlchtdj",

    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "License :: OSI Approved :: MIT License",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
    ],

    packages = ["asynclient"],
)
