# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path
from distutils.cmd import Command
import re

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

re_version = re.compile(r'__version__\s*=\s*(["\'])(.*?)\1')

with open(path.join(here, 'src/grello/__init__.py'), encoding='utf-8') as f:
    m = re_version.search(f.read())
    if not m:
        raise Exception("Could not detect package version")
    version = m.group(2)

class CoverageCommand(Command):
    description = "Run coverage tool and generate html raport in ./coverage dir"
    user_options = []
    
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    
    def run(self):
        import coverage
        c = coverage.Coverage(source=["%s/src" % here])
        c.start()
        self.run_command("test")
        c.stop()
        c.html_report(directory="%s/coverage" % here)

setup(
    name='grello',
    version=version,
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
        'Programming Language :: Python :: 3.6',
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
    test_suite="grello.tests",
    cmdclass={'coverage': CoverageCommand}
)
