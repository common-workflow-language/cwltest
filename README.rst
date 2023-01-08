##########################################
Common Workflow Language testing framework
##########################################

|Linux Build Status| |Code coverage|

PyPI: |PyPI Version| |PyPI Downloads Month| |Total PyPI Downloads|

Conda: |Conda Version| |Conda Installs|

.. |Linux Build Status| image:: https://github.com/common-workflow-language/cwltest/actions/workflows/ci-tests.yml/badge.svg?branch=main
   :target: https://github.com/common-workflow-language/cwltest/actions/workflows/ci-tests.yml
.. |Code coverage| image:: https://codecov.io/gh/common-workflow-language/cwltest/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/common-workflow-language/cwltest

.. |PyPI Version| image:: https://badge.fury.io/py/cwltest.svg
   :target: https://badge.fury.io/py/cwltest

.. |PyPI Downloads Month| image:: https://pepy.tech/badge/cwltest/month
   :target: https://pepy.tech/project/cwltest

.. |Total PyPI Downloads| image:: https://static.pepy.tech/personalized-badge/cwltest?period=total&units=international_system&left_color=black&right_color=orange&left_text=Total%20PyPI%20Downloads
   :target: https://pepy.tech/project/cwltest

.. |Conda Version| image:: https://anaconda.org/bioconda/cwltest/badges/version.svg
   :target: https://anaconda.org/bioconda/cwltest

.. |Conda Installs| image:: https://anaconda.org/bioconda/cwltest/badges/downloads.svg
   :target: https://anaconda.org/bioconda/cwltest

This is a testing tool for checking the output of Tools and Workflows described
with the Common Workflow Language.  Among other uses, it is used to run the CWL
conformance tests.

This is written and tested for Python 3.6, 3.7, 3.8, 3.9, 3.10, and 3.11.

.. contents:: Table of Contents
   :local:

*******
Install
*******

Installing the official package from PyPi

.. code:: bash

  pip install cwltest

Or from bioconda

.. code:: bash

  conda install -c bioconda cwltest

Or from source

.. code:: bash

  git clone https://github.com/common-workflow-language/cwltest.git
  cd cwltest && python setup.py install

***********************
Run on the command line
***********************

Simple command::

  cwltest --test test-descriptions.yml --tool cwl-runner

*****************************************
Generate conformance badges using cwltest
*****************************************

To make badges that show the results of the conformance test,
you can generate JSON files for https://badgen.net by using --badgedir option

To generate JSON files::

  cwltest --test test-descriptions.yml --tool cwl-runner --badgedir badges
  ...
  $ cat badges/command_line_tool.json | jq .
  {
    "subject": "command_line_tool",
    "status": "100%",
    "color": "green"
  }

Once you upload JSON file to a server, you make a badge by using a link like https://badgen.net/https/path/to/generated/json or https://flat.badgen.net/https/path/to/generated/json (for flat badges).

Here is an example of markdown to add a badge::

  ![test result](https://flat.badgen.net/https/path/to/generated/json?icon=commonwl)
