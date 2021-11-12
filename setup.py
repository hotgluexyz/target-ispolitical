#!/usr/bin/env python

from setuptools import setup

setup(
    name='target-ispolitical',
    version='1.1.0',
    description='hotglue target for exporting data to ISPolitical API',
    author='hotglue',
    url='https://hotglue.xyz',
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    py_modules=['target_ispolitical'],
    install_requires=[
        'phonenumbers==8.12.37',
        'requests==2.20.0',
        'argparse==1.4.0'
    ],
    entry_points='''
        [console_scripts]
        target-ispolitical=target_ispolitical:main
    ''',
    packages=['target_ispolitical']
)
