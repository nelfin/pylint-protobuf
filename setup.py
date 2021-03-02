import os.path
from setuptools import setup, find_packages

__version__ = '0.18.1'

description = (
    'A plugin for making Pylint aware of the fields of protobuf-generated '
    'classes'
)
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(
    name='pylint-protobuf',
    version=__version__,
    url='https://github.com/nelfin/pylint-protobuf',
    author='Andrew Haigh',
    author_email='hello@nelf.in',
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    keywords=['pylint', 'plugin', 'protobuf'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Quality Assurance',
    ],
    packages=find_packages(),
    install_requires=[
        'astroid',
        'pylint',
        'protobuf',
    ],
    zip_safe=False
)
