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

if sys.version_info.major == 2:
    install_requires.append('futures >= 3.0.5')

if sys.version_info[:2] < (3, 5):
    install_requires.append('typing >= 3.5.2, < 3.6')


setup(name='cwltest',
      version='1.0',
      description='Common workflow language testing framework',
      long_description=open(README).read(),
      author='Common workflow language working group',
      author_email='common-workflow-language@googlegroups.com',
      url="https://github.com/common-workflow-language/cwltest",
      download_url="https://github.com/common-workflow-language/cwltest",
      license='Apache 2.0',
      packages=["cwltest"],
      install_requires=install_requires,
      tests_require=[],
      entry_points={
          'console_scripts': ["cwltest=cwltest:main"]
      },
      zip_safe=True,
      cmdclass={'egg_info': tagger},
)
