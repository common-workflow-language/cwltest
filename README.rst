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

This is written and tested for Python 3.10, 3.11, 3.12, 3.13, and 3.14

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
  cd cwltest && pip install  .

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

*************************
Custom file access module
*************************

If your CWL implementation does not write output files to a local file
system location but instead to some other remote storage system, you
can provide an alternate implementation of the *StdFsAccess* object
that is able to access your storage system.

Step 1:

Implement your own class with the same public interface of the
*StdFsAccess* object in *cwltest/stdfsaccess.py* (as of this writing,
the methods are *open*, *size*, *isfile* and *isdir*).  These methods
should expect to be called with URIs from the *location* field of the
outputs of test cases.

Define a function that, when called, returns a new instance of your object.

Step 2:

Create a Python package containing your class (or add it to an
existing one).

In the package metadata, add an entry point that declares the module
(in this example, *my_cwl_runner.fsaccess*) containing the function
(in this example, *get_fsaccess*) that *cwltest* will invoke to get an
object implementing the *StdFsAccess* interface.

In *setup.py* this looks like:

.. code:: python

  setup(
    ...
    entry_points={"cwltest.fsaccess": ["fsaccess=my_cwl_runner.fsaccess:get_fsaccess"]}},
    ...
  )

In *pyproject.toml* it looks like:

.. code::

  [project.entry-points.'cwltest.fsaccess']
  fsaccess = 'my_cwl_runner.fsaccess:get_fsaccess'


Step 3:

Install your package in the same Python environemnt as the
installation of *cwltest*. When invoked, *cwltest* will query Python
package metadata for a package with the *cwltest.fsaccess* entry point
and call it to get back a custom filesystem access object.
