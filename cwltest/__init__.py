#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

from six.moves import range
from six.moves import zip

import argparse
import json
import os
import subprocess
import sys
import shutil
import tempfile
import junit_xml
import ruamel.yaml as yaml
import ruamel.yaml.scanner as yamlscanner
import pipes
import logging
import schema_salad.ref_resolver
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Text

from cwltest.utils import compare, CompareFail

_logger = logging.getLogger("cwltest")
_logger.addHandler(logging.StreamHandler())
_logger.setLevel(logging.INFO)

UNSUPPORTED_FEATURE = 33
RUNTIME = sys.version_info.major


class TestResult(object):

    """Encapsulate relevant test result data."""

    def __init__(self, return_code, standard_output, error_output, duration, classname, message=''):
        # type: (int, Text, Text, float, Text, str) -> None
        self.return_code = return_code
        self.standard_output = standard_output
        self.error_output = error_output
        self.duration = duration
        self.message = message
        self.classname = classname

    def create_test_case(self, test):
        # type: (Dict[Text, Any]) -> junit_xml.TestCase
        doc = test.get(u'doc', 'N/A').strip()
        case = junit_xml.TestCase(
            doc, elapsed_sec=self.duration, classname=self.classname,
            stdout=self.standard_output, stderr=self.error_output,
        )
        if self.return_code > 0:
            case.failure_message = self.message
        return case


templock = threading.Lock()


def run_test(args, i, tests):  # type: (argparse.Namespace, int, List[Dict[str, str]]) -> TestResult
    global templock

    out = {}  # type: Dict[str,Any]
    outdir = outstr = outerr = test_command = None
    duration = 0.0
    t = tests[i]
    prefix = ""
    suffix = ""
    if sys.stderr.isatty():
        prefix = "\r"
    else:
        suffix = "\n"
    try:
        test_command = [args.tool]
        test_command.extend(args.args)

        # Add additional arguments given in test case
        if args.testargs is not None:
            for testarg in args.testargs:
                (test_case_name, prefix) = testarg.split('==')
                if test_case_name in t:
                    test_command.extend([prefix, t[test_case_name]])

        # Add prefixes if running on MacOSX so that boot2docker writes to /Users
        with templock:
            if 'darwin' in sys.platform and args.tool == 'cwltool':
                outdir = tempfile.mkdtemp(prefix=os.path.abspath(os.path.curdir))
                test_command.extend(["--tmp-outdir-prefix={}".format(outdir), "--tmpdir-prefix={}".format(outdir)])
            else:
                outdir = tempfile.mkdtemp()
        test_command.extend(["--outdir={}".format(outdir),
                             "--quiet",
                             t["tool"]])
        if t.get("job"):
            test_command.append(t["job"])

        sys.stderr.write("%sTest [%i/%i] %s\n" % (prefix, i + 1, len(tests), suffix))
        sys.stderr.flush()

        start_time = time.time()
        stderr = subprocess.PIPE if not args.verbose else None
        process = subprocess.Popen(test_command, stdout=subprocess.PIPE, stderr=stderr)
        outstr, outerr = [var.decode('utf-8') for var in process.communicate()]
        return_code = process.poll()
        duration = time.time() - start_time
        if return_code:
            raise subprocess.CalledProcessError(return_code, " ".join(test_command))

        out = json.loads(outstr)
    except ValueError as v:
        _logger.error(str(v))
        _logger.error(outstr)
        _logger.error(outerr)
    except subprocess.CalledProcessError as err:
        if err.returncode == UNSUPPORTED_FEATURE:
            return TestResult(UNSUPPORTED_FEATURE, outstr, outerr, duration, args.classname)
        elif t.get("should_fail", False):
            return TestResult(0, outstr, outerr, duration, args.classname)
        else:
            _logger.error(u"""Test failed: %s""", " ".join([pipes.quote(tc) for tc in test_command]))
            _logger.error(t.get("doc"))
            _logger.error("Returned non-zero")
            _logger.error(outerr)
            return TestResult(1, outstr, outerr, duration, args.classname, str(err))
    except (yamlscanner.ScannerError, TypeError) as e:
        _logger.error(u"""Test failed: %s""", " ".join([pipes.quote(tc) for tc in test_command]))
        _logger.error(outstr)
        _logger.error(u"Parse error %s", str(e))
        _logger.error(outerr)
    except KeyboardInterrupt:
        _logger.error(u"""Test interrupted: %s""", " ".join([pipes.quote(tc) for tc in test_command]))
        raise

    fail_message = ''

    if t.get("should_fail", False):
        _logger.warning(u"""Test failed: %s""", " ".join([pipes.quote(tc) for tc in test_command]))
        _logger.warning(t.get("doc"))
        _logger.warning(u"Returned zero but it should be non-zero")
        return TestResult(1, outstr, outerr, duration, args.classname)

    try:
        compare(t.get("output"), out)
    except CompareFail as ex:
        _logger.warning(u"""Test failed: %s""", " ".join([pipes.quote(tc) for tc in test_command]))
        _logger.warning(t.get("doc"))
        _logger.warning(u"Compare failure %s", ex)
        fail_message = str(ex)

    if outdir:
        shutil.rmtree(outdir, True)

    return TestResult((1 if fail_message else 0), outstr, outerr, duration, args.classname, fail_message)


def main():  # type: () -> int

    parser = argparse.ArgumentParser(description='Compliance tests for cwltool')
    parser.add_argument("--test", type=str, help="YAML file describing test cases", required=True)
    parser.add_argument("--basedir", type=str, help="Basedir to use for tests", default=".")
    parser.add_argument("-l", action="store_true", help="List tests then exit")
    parser.add_argument("-n", type=str, default=None, help="Run a specific tests, format is 1,3-6,9")
    parser.add_argument("--tool", type=str, default="cwl-runner",
                        help="CWL runner executable to use (default 'cwl-runner'")
    parser.add_argument("--only-tools", action="store_true", help="Only test CommandLineTools")
    parser.add_argument("--junit-xml", type=str, default=None, help="Path to JUnit xml file")
    parser.add_argument("--test-arg", type=str, help="Additional argument given in test cases and "
                                                     "required prefix for tool runner.",
                        metavar="cache==--cache-dir", action="append", dest="testargs")
    parser.add_argument("args", help="arguments to pass first to tool runner", nargs=argparse.REMAINDER)
    parser.add_argument("-j", type=int, default=1, help="Specifies the number of tests to run simultaneously "
                                                        "(defaults to one).")
    parser.add_argument("--verbose", action="store_true", help="More verbose output during test run.")
    parser.add_argument("--classname", type=str, default="", help="Specify classname for the Test Suite.")

    args = parser.parse_args()
    if '--' in args.args:
        args.args.remove('--')

    # Remove test arguments with wrong syntax
    if args.testargs is not None:
        args.testargs = [testarg for testarg in args.testargs if testarg.count('==') == 1]

    if not args.test:
        parser.print_help()
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
            print(u"[%i] %s" % (i + 1, t["doc"].strip()))
        return 0

    if args.n is not None:
        ntest = []
        for s in args.n.split(","):
            sp = s.split("-")
            if len(sp) == 2:
                ntest.extend(list(range(int(sp[0]) - 1, int(sp[1]))))
            else:
                ntest.append(int(s) - 1)
    else:
        ntest = list(range(0, len(tests)))

    total = 0
    with ThreadPoolExecutor(max_workers=args.j) as executor:
        jobs = [executor.submit(run_test, args, i, tests)
                for i in ntest]
        try:
            for i, job in zip(ntest, jobs):
                test_result = job.result()
                test_case = test_result.create_test_case(tests[i])
                total += 1
                if test_result.return_code == 1:
                    failures += 1
                    test_case.add_failure_info(output=test_result.message)
                elif test_result.return_code == UNSUPPORTED_FEATURE:
                    unsupported += 1
                    test_case.add_skipped_info("Unsupported")
                else:
                    passed += 1
                report.test_cases.append(test_case)
        except KeyboardInterrupt:
            for job in jobs:
                job.cancel()
            _logger.error("Tests interrupted")

    if args.junit_xml:
        with open(args.junit_xml, 'w') as fp:
            junit_xml.TestSuite.to_file(fp, [report])

    if failures == 0 and unsupported == 0:
        _logger.info("All tests passed")
        return 0
    elif failures == 0 and unsupported > 0:
        _logger.warning("%i tests passed, %i unsupported features", total - unsupported, unsupported)
        return 0
    else:
        _logger.warning("%i tests passed, %i failures, %i unsupported features", total - (failures + unsupported), failures, unsupported)
        return 1


if __name__ == "__main__":
    sys.exit(main())
