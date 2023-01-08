*************
Pytest plugin
*************

``cwltest`` can also be used as a Pytest plugin. The CWL test filename must start
with ``conformance_test`` and end with ``.yaml`` or ``.yml``.

In this case, the simple command::

  cwltest --test conformance_test_xxx.yml --tool cwl-runner

becomes::

  pytest conformance_test_xxx.yml --cwl-runner cwl-runner

Command Line Options
====================

.. autoprogram:: cwltest.plugin:_doc_options()
   :prog: pytest

Converting ``cwltest`` options to ``pytest`` options
====================================================

The table below details all the available command conversions between the two formats.

.. list-table::
   :widths: 40 30 30
   :header-rows: 1

   * - Feature
     - ``cwltest``
     - ``pytest``
   * - YAML file describing test cases
     - ``--test conformance_test_xxx.yml``
     - ``conformance_test_xxx.yml``
   * - CWL runner executable to use
     - ``--tool CWL_RUNNER``
     - :option:`--cwl-runner CWL_RUNNER`
   * - Specifies the number of tests

       to run simultaneously
     - ``-j CORES``
     - ``-n CORES`` [#f1]_
   * - Automatically scale the number of tests

       to run simultaneously
     - **UNSUPPORTED**
     - ``-n auto`` [#f1]_
   * - Only run one test at a time

       (good for debugging cwltest itself)
     - ``-j 1``

       (or leave out ``-j``)
     - ``-n 0 -s`` [#f1]_
   * - Time of execution in seconds

       after which the test will be skipped
     - ``--timeout TIMEOUT``
     - ``--timeout TIMEOUT`` [#f3]_
   * - List tests then exit
     - ``-l``
     - ``--collect-only``
   * - Run specific tests using their short names
     - ``-s TEST_NAME[,TEST_NAME…]``
     - :option:`--cwl-include TEST_NAME[,TEST_NAME…]`
   * - Exclude specific tests by short names
     - ``-S TEST_NAME[,TEST_NAME…]``
     - :option:`--cwl-exclude TEST_NAME[,TEST_NAME…]`
   * - Tags to be tested
     - ``--tags TAG[,TAG…]``
     - :option:`--cwl-tags TAG[,TAG…]`
   * - Tags not to be tested
     - ``--exclude-tags TAG[,TAG…]``
     - :option:`--cwl-exclude-tags TAG[,TAG…]`
   * - Path to JUnit xml file
     - ``--junit-xml PATH``
     - ``--junit-xml=PATH`` [#f4]_
   * - More verbose output during test run
     - ``--verbose``
     - ``-v[vv]``
   * - Additional argument given in test cases

       and required prefix for tool runner
     - ``--test-arg ARG_NAME==ARG_PREFIX``
     - :option:`--cwl-test-arg ARG_NAME==ARG_PREFIX`
   * - Arguments to pass first to tool runner
     - ``cwltest -- ARG [ARG …]``
     - :option:`--cwl-args "ARG [ARG …]"`
   * - Only test CommandLineTools
     - ``--only-tools``
     - **UNSUPPORTED**
   * - Show all tags
     - ``--show-tags``
     - **UNSUPPORTED**
   * - Store more verbose output to JUnit xml file
     - ``--junit-verbose``
     - :option:`--cwl-runner-verbose` [#f4]_
   * - Specify classname for the Test Suite
     - ``--classname CLASS_NAME``
     - **UNSUPPORTED**

.. [#f1] Requires `pytest-xdist <https://pypi.org/project/pytest-xdist/>`_.
         See :ref:`pytest_xdist:parallelization`.
.. [#f2] ``-s`` is a shortcut for ``--capture=no``, also helps with debugging
         ``cwltest`` or the cwltest plugin to ``pytest``.
.. [#f3] Requires `pytest-timeout <https://pypi.org/project/pytest-timeout/>`_.
         Note: even if ``pytest-timeout`` is installed, there is no default
         timeout. This is different than ``cwltest``'s default timeout of 10
         minutes.

Differences in the XML output
=============================

``cwltest --junit-xml`` output

* top-level ``<testsuites>`` element has the elapsed time, and counts (errors,
  failures, skipped, and total)
* singular ``<testsuite>`` sub-element the same attributes as the top-level
  ``<testsuites>`` plus ``name`` which is the basename of the YAML test file
* each ``<testcase>`` element has the follow attributes

  * ``name``: the doc string
  * ``class``: the tags
  * ``file``: the test ID
  * ``url``: like "cwltest:conformance_tests#1"
    (contains the basename of the YAML test file)
  * ``time``: the elapsed time

* ``<testcase>`` elements always contain the following sub-elements,
  regardless of outcome

  * ``<system-out>``: the output object
  * ``<system-err>``: stderr (docker pull, other warnings, and errors)

* ``<testcase>`` elements for failed test cases do not have a ``<failure>`` sub-element

``pytest`` with ``cwltest`` plugin XML output

* top-level ``<testsuites>`` element has no attributes
* singular ``<testsuite>`` sub-element has the same attributes as the ``cwltest``
  XML version along with these additional attributes

  * ``name``: default is ``pytest``
    (can be customized with the pytest INI option ``junit_suite_name``)
  * ``timestamp="2023-01-08T11:39:07.425159"``
  * ``hostname``: the hostname of the machine where the tests ran
* inside the ``<testsuite>`` is a ``<properties>..</properties>`` element
  with two ``<property name="…" value="…" />`` elements. But this
  `does not work with pytest-xdist <https://github.com/pytest-dev/pytest/issues/7767>`_.

  * ``runner``: the name of the CWL runner
  * ``runner_extra_args``: the value of `--cwl-args``

* each ``<testcase>`` element has the following attributes

  * ``classname``: always the name of the YAML file (``conformance_tests.yaml``)
  * ``name``: the test ID
  * ``time``: the elapsed time

* ``<testcase>`` elements for failed test cases **do** have a ``<failure>`` sub-element
  with a ``message`` attribute containing the :py:meth:`cwltest.plugin.CWLItem.repr_failure`
  output. This text is repeated as the content of the ``<failure>`` element.
  The presensce of ``<system-out>`` and ``<system-err>`` sub-elements varies. [#f4]_

 .. [#f4] Depending on the value of the pytest INI option ``junit_logging``,
         then ``<system-out>`` and ``<system-err>`` sub-elements will be generated.
         However the default value for ``junit_logging`` is ``no``, so to get
         either of these pick one from `the full list
         <https://docs.pytest.org/en/stable/reference/reference.html#confval-junit_logging>`_.
         You can set ``junit_logging`` in `a configuration file
         <https://docs.pytest.org/en/stable/reference/customize.html#configuration-file-formats>`_
         or on the command line: ``pytest -o junit_logging=out-err``.
