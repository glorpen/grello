# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='grello',
    version='1.0',
    description='Python library for interacting with trello api',
    long_description=long_description,
    url='https://github.com/glorpen/grello',
    author='Arkadiusz Dzięgiel',
    author_email='arkadiusz.dziegiel@glorpen.pl',
    license='GPL',
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',

        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',

        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='trello api library',
    package_dir={'': 'src'},
    packages=find_packages("src", exclude=['grello.tests']),
    install_requires=['requests', 'requests-oauthlib'],
    extras_require={
        'dev': [],
        'test': ['coverage', 'unittest'],
    },
    package_data={},
    data_files=[],
    entry_points={},
)
