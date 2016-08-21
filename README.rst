==========================================
Common workflow language testing framework
==========================================

This is a testing tool for checking the output of Tools and Workflows described
with the Common Workflow Language.  Among other uses, it is used to run the CWL
conformance tests.

This is written and tested for Python 2.7.

Install
-------

Installing the official package from PyPi::

  pip install cwltest

Or from source::

  git clone https://github.com/common-workflow-language/cwltest.git
  cd cwltest && python setup.py install

Run on the command line
-----------------------

Simple command::

  cwltest --test test-descriptions.yml --tool cwl-runner
