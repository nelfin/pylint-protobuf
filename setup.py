from setuptools import setup, find_packages

__version__ = '0.1'

setup(
    name='pylint-protobuf',
    version=__version__,
    url='https://github.com/nelfin/pylint-protobuf',
    author='Andrew Haigh',
    author_email='hello@nelf.in',
    license='MIT',
    keywords=['pylint', 'plugin', 'protobuf'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Quality Assurance',
    ],
    packages=find_packages(),
    install_requires=[
        'astroid',
        'pylint',
    ],
)
