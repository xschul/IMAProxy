#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='imaptproxy',
    version='1.0.0',
    author='Xavier Schul',
    author_email='schul.x@hotmail.com',
    maintainer='Xavier Schul',
    url='https://github.com/xschul/IMAProxy',
    description='IMAP Transparent Proxy',
    packages=['imaptproxy'],
    scripts=['bin/start.py', 'bin/test_proxy.py'],
    classifiers=[
        'Environment :: Console',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Security'
    ]
)