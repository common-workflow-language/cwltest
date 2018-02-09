#!/usr/bin/env python
from __future__ import absolute_import

import os
import sys

import setuptools.command.egg_info as egg_info_cmd
from setuptools import setup

SETUP_DIR = os.path.dirname(__file__)
README = os.path.join(SETUP_DIR, 'README.rst')

try:
    import gittaggers
    tagger = gittaggers.EggInfoFromGit
except ImportError:
    tagger = egg_info_cmd.egg_info

install_requires = [
    'schema-salad >= 1.14',
    'junit-xml >= 1.7',
    'six>=1.10.0'
]

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(name='cwltest',
      version='1.0',
      description='Common workflow language testing framework',
      long_description=open(README).read(),
      author='Common workflow language working group',
      author_email='common-workflow-language@googlegroups.com',
      url="https://github.com/common-workflow-language/cwltest",
      download_url="https://github.com/common-workflow-language/cwltest",
      license='Apache 2.0',
      packages=["cwltest", "cwltest.tests"],
      package_dir={'cwltest.tests': 'tests'},
      include_package_data=True,
      install_requires=install_requires,
      test_suite='tests',
      setup_requires=[] + pytest_runner,
      tests_require=['pytest'],
      entry_points={
          'console_scripts': ["cwltest=cwltest:main"]
      },
      zip_safe=True,
      cmdclass={'egg_info': tagger},
      extras_require={':python_version<"3"': [
                      'futures >= 3.0.5', 'subprocess32'],
                      ':python_version<"3.5"': ['typing >= 3.5.2'] }
)
