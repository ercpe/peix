#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='peix',
    version='0.1',
    description='Python implementation of the eix database format',
    author='Johann Schmitz',
    author_email='johann@j-schmitz.net',
    url='https://ercpe.de/projects/peix',
    download_url='https://code.not-your-server.de/peix.git/tags/',
    packages=find_packages(exclude=('tests', )),
    include_package_data=True,
    zip_safe=False,
    license='GPL-3',
)
