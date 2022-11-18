# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

long_desc = open('README.rst').read()

setup(
    name='sphinxcontrib-plantuml',
    version='0.24.1',
    url='https://github.com/sphinx-contrib/plantuml/',
    download_url='https://pypi.python.org/pypi/sphinxcontrib-plantuml',
    license='BSD',
    author='Yuya Nishihara',
    author_email='yuya@tcha.org',
    description='Sphinx "plantuml" extension',
    long_description=long_desc,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Sphinx :: Extension',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    namespace_packages=['sphinxcontrib'],
)
