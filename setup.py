# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

long_desc = open('README').read()

requires = ['Sphinx>=0.6']

setup(
    name='sphinxcontrib-plantuml',
    version='0.1',
    url='http://bitbucket.org/birkenfeld/sphinx-contrib',
    download_url='http://pypi.python.org/pypi/sphinxcontrib-plantuml',
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
    install_requires=requires,
    namespace_packages=['sphinxcontrib'],
)
