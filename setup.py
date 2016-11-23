#!/usr/bin/env python

import os

import setuptools.command.egg_info as egg_info_cmd
from setuptools import setup, find_packages

SETUP_DIR = os.path.dirname(__file__)
README = os.path.join(SETUP_DIR, 'README.rst')

try:
    import gittaggers
    tagger = gittaggers.EggInfoFromGit
except ImportError:
    tagger = egg_info_cmd.egg_info

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
      install_requires=[
          'schema-salad >= 1.14',
          'typing >= 3.5.2',
          'junit-xml >= 1.7'
      ],
      extras_require={
          ':python_version == "2.7"': [
              'futures >= 3.0.5',
          ],
      },
      tests_require=[],
      entry_points={
          'console_scripts': [ "cwltest=cwltest:main" ]
      },
      zip_safe=True,
      cmdclass={'egg_info': tagger},
)
