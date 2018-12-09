==========================================
Common workflow language testing framework
==========================================
.. image:: https://travis-ci.org/common-workflow-language/cwltest.svg?branch=master
    :target: https://travis-ci.org/common-workflow-language/cwltest

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

Generate conformance badges using cwltest
-----------------------------------------

To make badges that show the results of the conformance test,
you can generate JSON files for https://badgen.net by using --badgedir option

To generate JSON files::

  cwltest --test test-descriptions.yml --tool cwl-runner --badgedir badges
  ...
  $ cat badges/command_line_tool.json | jq .
  {
    "subject": "[CWL] command_line_tool",
    "status": "100%",
    "color": "green"
  }

Once you upload JSON file to a server, you make a badge by using a link like https://flat.badgen.net/https/path/to/generated/json.

Here is an example of markdown to add a badge::

  ![test result](https://flat.badgen.net/https/path/to/generated/json)
