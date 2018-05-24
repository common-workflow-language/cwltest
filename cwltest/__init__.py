#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Text
from concurrent.futures import ThreadPoolExecutor

import ruamel.yaml as yaml
import ruamel.yaml.scanner as yamlscanner
import schema_salad.ref_resolver
from six.moves import range
from six.moves import zip
import pkg_resources  # part of setuptools

import junit_xml
from cwltest.utils import (compare, CompareFail, TestResult, REQUIRED,
                           get_test_number_by_key)

_logger = logging.getLogger("cwltest")
_logger.addHandler(logging.StreamHandler())
_logger.setLevel(logging.INFO)

UNSUPPORTED_FEATURE = 33
DEFAULT_TIMEOUT = 600  # 10 minutes

if sys.version_info < (3, 0):
    import subprocess32 as subprocess
    from pipes import quote
else:
    import subprocess
    from shlex import quote
if sys.stderr.isatty():
    PREFIX = "\r"
    SUFFIX=''
else:
    PREFIX=''
    SUFFIX= "\n"

templock = threading.Lock()


def prepare_test_command(tool,      # type: str
                         args,      # type: List[str]
                         testargs,  # type: Optional[List[str]]
                         test       # type: Dict[str, str]
                        ):  # type: (...) -> List[str]
    """ Turn the test into a command line. """
    test_command = [tool]
    test_command.extend(args)

    # Add additional arguments given in test case
    if testargs is not None:
        for testarg in testargs:
            (test_case_name, prefix) = testarg.split('==')
            if test_case_name in test:
                test_command.extend([prefix, test[test_case_name]])

    # Add prefixes if running on MacOSX so that boot2docker writes to /Users
    with templock:
        if 'darwin' in sys.platform and tool == 'cwltool':
            outdir = tempfile.mkdtemp(prefix=os.path.abspath(os.path.curdir))
            test_command.extend(["--tmp-outdir-prefix={}".format(outdir),
                                 "--tmpdir-prefix={}".format(outdir)])
        else:
            outdir = tempfile.mkdtemp()
    test_command.extend(["--outdir={}".format(outdir),
                         "--quiet",
                         os.path.normcase(test["tool"])])
    if test.get("job"):
        test_command.append(os.path.normcase(test["job"]))
    return test_command



def run_test(args,         # type: argparse.Namespace
             test,         # type: Dict[str, str]
             test_number,  # type: int
             total_tests,  # type: int
             timeout       # type: int
            ):  # type: (...) -> TestResult

    if test.get("short_name"):
        sys.stderr.write(
            "%sTest [%i/%i] %s: %s%s\n"
            % (PREFIX, test_number, total_tests, test.get("short_name"),
               test.get("doc"), SUFFIX))
    else:
        sys.stderr.write(
            "%sTest [%i/%i] %s%s\n"
            % (PREFIX, test_number, total_tests, test.get("doc"), SUFFIX))
    sys.stderr.flush()
    return run_test_plain(args, test, timeout)


def run_test_plain(args,         # type: argparse.Namespace
                   test,         # type: Dict[str, str]
                   timeout       # type: int
                  ):  # type: (...) -> TestResult


    global templock

    out = {}  # type: Dict[str,Any]
    outdir = outstr = outerr = None
    test_command = []  # type: List[str]
    duration = 0.0
    try:
        process = None  # type: subprocess.Popen
        test_command = prepare_test_command(
            args['tool'], args['args'], args['testargs'], test)

        start_time = time.time()
        stderr = subprocess.PIPE if not args['verbose'] else None
        process = subprocess.Popen(test_command, stdout=subprocess.PIPE, stderr=stderr)
        outstr, outerr = process.communicate(timeout=timeout)
        for out in outstr, outerr:
            if out:
                out = out.decode('utf-8')
        return_code = process.poll()
        duration = time.time() - start_time
        if return_code:
            raise subprocess.CalledProcessError(return_code, " ".join(test_command))

        out = json.loads(outstr)
    except subprocess.CalledProcessError as err:
        if err.returncode == UNSUPPORTED_FEATURE:
            return TestResult(UNSUPPORTED_FEATURE, outstr, outerr, duration,
                    args['classname'])
        if test.get("should_fail", False):
            return TestResult(0, outstr, outerr, duration, args['classname'])
        _logger.error(u"""Test failed: %s""", " ".join([quote(tc) for tc in test_command]))
        _logger.error(test.get("doc"))
        _logger.error(u"Returned non-zero")
        _logger.error(outerr)
        return TestResult(1, outstr, outerr, duration, args['classname'], str(err))
    except (yamlscanner.ScannerError, TypeError) as err:
        _logger.error(u"""Test failed: %s""",
                      u" ".join([quote(tc) for tc in test_command]))
        _logger.error(outstr)
        _logger.error(u"Parse error %s", str(err))
        _logger.error(outerr)
    except KeyboardInterrupt:
        _logger.error(u"""Test interrupted: %s""",
                      u" ".join([quote(tc) for tc in test_command]))
        raise
    except subprocess.TimeoutExpired:
        _logger.error(u"""Test timed out: %s""",
                      u" ".join([quote(tc) for tc in test_command]))
        _logger.error(test.get("doc"))
        return TestResult(2, outstr, outerr, timeout, args['classname'], "Test timed out")
    finally:
        if process is not None and process.returncode is None:
            _logger.error(u"""Terminating lingering process""")
            process.terminate()
            for _ in range(0, 3):
                time.sleep(1)
                if process.poll() is not None:
                    break
            if process.returncode is None:
                process.kill()

    fail_message = ''

    if test.get("should_fail", False):
        _logger.warning(u"""Test failed: %s""", u" ".join([quote(tc) for tc in test_command]))
        _logger.warning(test.get("doc"))
        _logger.warning(u"Returned zero but it should be non-zero")
        return TestResult(1, outstr, outerr, duration, args['classname'])

    try:
        compare(test.get("output"), out)
    except CompareFail as ex:
        _logger.warning(u"""Test failed: %s""", u" ".join([quote(tc) for tc in test_command]))
        _logger.warning(test.get("doc"))
        _logger.warning(u"Compare failure %s", ex)
        fail_message = str(ex)

    if outdir:
        shutil.rmtree(outdir, True)

    return TestResult((1 if fail_message else 0), outstr, outerr, duration,
                      args['classname'], fail_message)


def arg_parser():  # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(description='Common Workflow Language testing framework')
    parser.add_argument("--test", type=str, help="YAML file describing test cases", required=True)
    parser.add_argument("--basedir", type=str, help="Basedir to use for tests", default=".")
    parser.add_argument("-l", action="store_true", help="List tests then exit")
    parser.add_argument("-n", type=str, default=None, help="Run specific tests, format is 1,3-6,9")
    parser.add_argument("-s", type=str, default=None, help="Run specific tests using their short names separated by comma")
    parser.add_argument("--tool", type=str, default="cwl-runner",
                        help="CWL runner executable to use (default 'cwl-runner'")
    parser.add_argument("--only-tools", action="store_true", help="Only test CommandLineTools")
    parser.add_argument("--junit-xml", type=str, default=None, help="Path to JUnit xml file")
    parser.add_argument("--test-arg", type=str, help="Additional argument "
        "given in test cases and required prefix for tool runner.",
        default=None, metavar="cache==--cache-dir", action="append", dest="testargs")
    parser.add_argument("args", help="arguments to pass first to tool runner", nargs=argparse.REMAINDER)
    parser.add_argument("-j", type=int, default=1, help="Specifies the number of tests to run simultaneously "
                                                        "(defaults to one).")
    parser.add_argument("--verbose", action="store_true", help="More verbose output during test run.")
    parser.add_argument("--classname", type=str, default="", help="Specify classname for the Test Suite.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
            help="Time of execution in seconds after which the test will be "
            "skipped. Defaults to {} seconds ({} minutes).".format(
                DEFAULT_TIMEOUT, DEFAULT_TIMEOUT/60))

    pkg = pkg_resources.require("cwltest")
    if pkg:
        ver = u"%s %s" % (sys.argv[0], pkg[0].version)
    else:
        ver = u"%s %s" % (sys.argv[0], "unknown version")
    parser.add_argument('--version', action='version', version=ver)

    return parser


def main():  # type: () -> int

    args = arg_parser().parse_args(sys.argv[1:])
    if '--' in args.args:
        args.args.remove('--')

    # Remove test arguments with wrong syntax
    if args.testargs is not None:
        args.testargs = [testarg for testarg in args.testargs if testarg.count('==') == 1]

    if not args.test:
        arg_parser().print_help()
        return 1

    with open(args.test) as f:
        tests = yaml.load(f, Loader=yaml.SafeLoader)

    failures = 0
    unsupported = 0
    passed = 0
    suite_name, _ = os.path.splitext(os.path.basename(args.test))
    report = junit_xml.TestSuite(suite_name, [])

    if args.only_tools:
        alltests = tests
        tests = []
        for t in alltests:
            loader = schema_salad.ref_resolver.Loader({"id": "@id"})
            cwl = loader.resolve_ref(t["tool"])[0]
            if isinstance(cwl, dict):
                if cwl["class"] == "CommandLineTool":
                    tests.append(t)
            else:
                raise Exception("Unexpected code path.")

    if args.l:
        for i, t in enumerate(tests):
            if t.get("short_name"):
                print(u"[%i] %s: %s" % (i + 1, t["short_name"], t["doc"].strip()))
            else:
                print(u"[%i] %s" % (i + 1, t["doc"].strip()))

        return 0

    if args.n is not None or args.s is not None:
        ntest = []
        if args.n is not None:
            for s in args.n.split(","):
                sp = s.split("-")
                if len(sp) == 2:
                    ntest.extend(list(range(int(sp[0]) - 1, int(sp[1]))))
                else:
                    ntest.append(int(s) - 1)
        if args.s is not None:
            for s in args.s.split(","):
                test_number = get_test_number_by_key(tests, "short_name", s)
                if test_number:
                    ntest.append(test_number)
                else:
                    _logger.error('Test with short name "%s" not found ', s)
                    return 1
    else:
        ntest = list(range(0, len(tests)))

    total = 0
    with ThreadPoolExecutor(max_workers=args.j) as executor:
        jobs = [executor.submit(run_test, args, tests[i], i+1, len(tests), args.timeout)
                for i in ntest]
        try:
            for i, job in zip(ntest, jobs):
                test_result = job.result()
                test_case = test_result.create_test_case(tests[i])
                total += 1
                return_code = test_result.return_code
                category = test_case.category
                if return_code == 0:
                    passed += 1
                elif return_code != 0 and return_code != UNSUPPORTED_FEATURE:
                    failures += 1
                    test_case.add_failure_info(output=test_result.message)
                elif return_code == UNSUPPORTED_FEATURE and category == REQUIRED:
                    failures += 1
                    test_case.add_failure_info(output=test_result.message)
                elif category != REQUIRED and return_code == UNSUPPORTED_FEATURE:
                    unsupported += 1
                    test_case.add_skipped_info("Unsupported")
                else:
                    raise Exception(
                        "This is impossible, return_code: {}, category: "
                        "{}".format(return_code, category))
                report.test_cases.append(test_case)
        except KeyboardInterrupt:
            for job in jobs:
                job.cancel()
            _logger.error("Tests interrupted")

    if args.junit_xml:
        with open(args.junit_xml, 'w') as xml:
            junit_xml.TestSuite.to_file(xml, [report])

    if failures == 0 and unsupported == 0:
        _logger.info("All tests passed")
        return 0
    if failures == 0 and unsupported > 0:
        _logger.warning("%i tests passed, %i unsupported features",
                        total - unsupported, unsupported)
        return 0
    _logger.warning("%i tests passed, %i failures, %i unsupported features",
                    total - (failures + unsupported), failures, unsupported)
    return 1


if __name__ == "__main__":
    sys.exit(main())
