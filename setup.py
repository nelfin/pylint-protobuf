from setuptools import setup, find_packages

__version__ = '0.1'

setup(
    name='pylint-protobuf',
    version=__version__,
    url='https://github.com/nelfin/pylint-protobuf',
    author='Andrew Haigh',
    author_email='hello@nelf.in',
    license='MIT',
    keywords='pylint plugin protobuf',
    packages=find_packages(),
)
