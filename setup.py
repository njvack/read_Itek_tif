#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

def get_locals(filename):
    l = {}
    with open(filename, 'r') as f:
        code = compile(f.read(), filename, 'exec')
        exec(code, {}, l)
    return l

metadata = get_locals(os.path.join('src', 'read_itek', '_metadata.py'))

def read(f):
    return open(f, 'r').read()

requirements = [
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='read_itek',
    version='0.1.0dev',
    description="Reads the files written by our MRI-compatible EMG amplifier",
    long_description=read('README.md'),
    author="Nathan Vack",
    author_email='njvack@wisc.edu',
    url='https://github.com/njvack/read_itek',
    packages=find_packages('src'),
    package_dir={'':'src'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='read_itek',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
