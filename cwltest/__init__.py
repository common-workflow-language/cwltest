#!/usr/bin/env python

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
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Text

_logger = logging.getLogger("cwltest")
_logger.addHandler(logging.StreamHandler())
_logger.setLevel(logging.INFO)

UNSUPPORTED_FEATURE = 33


class CompareFail(Exception):

    @classmethod
    def format(cls, expected, actual, cause=None):
        # type: (Any, Any, Any) -> CompareFail
        message = u"expected: %s\ngot: %s" % (
            json.dumps(expected, indent=4, sort_keys=True),
            json.dumps(actual, indent=4, sort_keys=True))
        if cause:
            message += u"\ncaused by: %s" % cause
        return cls(message)


class TestResult(object):

    """Encapsulate relevant test result data."""

    def __init__(self, return_code, standard_output, error_output):
        # type: (int, str, str) -> None
        self.return_code = return_code
        self.standard_output = standard_output
        self.error_output = error_output

    def create_test_case(self, test):
        # type: (Dict[Text, Any]) -> junit_xml.TestCase
        doc = test.get(u'doc', 'N/A').strip()
        return junit_xml.TestCase(doc, stdout=self.standard_output, stderr=self.error_output)


def compare_file(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    if "path" in expected:
        comp = "path"
        if "path" not in actual:
            actual["path"] = actual["location"]
    else:
        comp = "location"
    if expected[comp] != "Any" and (not (actual[comp].endswith("/" + expected[comp]) or
                                    ("/" not in actual[comp] and expected[comp] == actual[comp]))):
        raise CompareFail.format(expected, actual, u"%s does not end with %s" % (actual[comp], expected[comp]))

    check_keys = set(expected.keys()) - {'path', 'location'}

    for k in check_keys:
        try:
            compare(expected.get(k), actual.get(k))
        except CompareFail as e:
            raise CompareFail.format(expected, actual, u"field '%s' failed comparison: %s" %(
                k, e.message
            ))


def compare_directory(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    if actual.get("class") != 'Directory':
        raise CompareFail.format(expected, actual, u"expected object with a class 'Directory'")
    if "listing" not in actual:
        raise CompareFail.format(expected, actual, u"'listing' is mandatory field in Directory object")
    for i in expected["listing"]:
        found = False
        for j in actual["listing"]:
            try:
                compare(i, j)
                found = True
                break
            except CompareFail:
                pass
        if not found:
            raise CompareFail.format(expected, actual, u"%s not found" % json.dumps(i, indent=4, sort_keys=True))


def compare_dict(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    for c in expected:
        try:
            compare(expected[c], actual.get(c))
        except CompareFail as e:
            raise CompareFail.format(expected, actual, u"failed comparison for key '%s': %s" % (c, e))
    extra_keys = set(actual.keys()).difference(expected.keys())
    for k in extra_keys:
        if actual[k] is not None:
            raise CompareFail.format(expected, actual, u"unexpected key '%s'" % k)


def compare(expected, actual):  # type: (Any, Any) -> None
    if expected == "Any":
        return
    if expected is not None and actual is None:
        raise CompareFail.format(expected, actual)

    try:
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                raise CompareFail.format(expected, actual)

            if expected.get("class") == "File":
                compare_file(expected, actual)
            elif expected.get("class") == "Directory":
                compare_directory(expected, actual)
            else:
                compare_dict(expected, actual)

        elif isinstance(expected, list):
            if not isinstance(actual, list):
                raise CompareFail.format(expected, actual)

            if len(expected) != len(actual):
                raise CompareFail.format(expected, actual, u"lengths don't match")
            for c in xrange(0, len(expected)):
                try:
                    compare(expected[c], actual[c])
                except CompareFail as e:
                    raise CompareFail.format(expected, actual, e)
        else:
            if expected != actual:
                raise CompareFail.format(expected, actual)

    except Exception as e:
        raise CompareFail(str(e))


def run_test(args, i, tests):  # type: (argparse.Namespace, int, List[Dict[str, str]]) -> TestResult
    out = {}  # type: Dict[str,Any]
    outdir = outstr = outerr = test_command = None
    t = tests[i]
    try:
        test_command = [args.tool]
        test_command.extend(args.args)
        # Add prefixes if running on MacOSX so that boot2docker writes to /Users
        if 'darwin' in sys.platform:
            outdir = tempfile.mkdtemp(prefix=os.path.abspath(os.path.curdir))
            test_command.extend(["--tmp-outdir-prefix={}".format(outdir), "--tmpdir-prefix={}".format(outdir)])
        else:
            outdir = tempfile.mkdtemp()
        test_command.extend(["--outdir={}".format(outdir),
                             "--quiet",
                             t["tool"]])
        if t.get("job"):
            test_command.append(t["job"])

        sys.stderr.write("\rTest [%i/%i] " % (i + 1, len(tests)))
        sys.stderr.flush()

        process = subprocess.Popen(test_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outstr, outerr = process.communicate()
        return_code = process.poll()
        if return_code:
            raise subprocess.CalledProcessError(return_code, " ".join(test_command))

        out = json.loads(outstr)
    except ValueError as v:
        _logger.error(str(v))
        _logger.error(outstr)
        _logger.error(outerr)
    except subprocess.CalledProcessError as err:
        if err.returncode == UNSUPPORTED_FEATURE:
            return TestResult(UNSUPPORTED_FEATURE, outstr, outerr)
        else:
            _logger.error(u"""Test failed: %s""", " ".join([pipes.quote(tc) for tc in test_command]))
            _logger.error(t.get("doc"))
            _logger.error("Returned non-zero")
            _logger.error(outerr)
            return TestResult(1, outstr, outerr)
    except (yamlscanner.ScannerError, TypeError) as e:
        _logger.error(u"""Test failed: %s""", " ".join([pipes.quote(tc) for tc in test_command]))
        _logger.error(outstr)
        _logger.error(u"Parse error %s", str(e))
        _logger.error(outerr)
    except KeyboardInterrupt:
        _logger.error(u"""Test interrupted: %s""", " ".join([pipes.quote(tc) for tc in test_command]))
        raise

    failed = False

    try:
        compare(t.get("output"), out)
    except CompareFail as ex:
        _logger.warn(u"""Test failed: %s""", " ".join([pipes.quote(tc) for tc in test_command]))
        _logger.warn(t.get("doc"))
        _logger.warn(u"Compare failure %s", ex)
        failed = True

    if outdir:
        shutil.rmtree(outdir, True)

    return TestResult((1 if failed else 0), outstr, outerr)


def main():  # type: () -> int
    parser = argparse.ArgumentParser(description='Compliance tests for cwltool')
    parser.add_argument("--test", type=str, help="YAML file describing test cases", required=True)
    parser.add_argument("--basedir", type=str, help="Basedir to use for tests", default=".")
    parser.add_argument("-l", action="store_true", help="List tests then exit")
    parser.add_argument("-n", type=str, default=None, help="Run a specific tests, format is 1,3-6,9")
    parser.add_argument("--tool", type=str, default="cwl-runner",
                        help="CWL runner executable to use (default 'cwl-runner'")
    parser.add_argument("--only-tools", action="store_true", help="Only test tools")
    parser.add_argument("--junit-xml", type=str, default=None, help="Path to JUnit xml file")
    parser.add_argument("args", help="arguments to pass first to tool runner", nargs=argparse.REMAINDER)
    parser.add_argument("-j", type=int, default=1, help="Specifies the number of tests to run simultaneously (defaults to one).")

    args = parser.parse_args()
    if '--' in args.args:
        args.args.remove('--')

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
            print u"[%i] %s" % (i + 1, t["doc"].strip())
        return 0

    if args.n is not None:
        ntest = []
        for s in args.n.split(","):
            sp = s.split("-")
            if len(sp) == 2:
                ntest.extend(range(int(sp[0]) - 1, int(sp[1])))
            else:
                ntest.append(int(s) - 1)
    else:
        ntest = range(0, len(tests))

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
                    test_case.add_failure_info("N/A")
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
        _logger.warn("%i tests passed, %i unsupported features", total - unsupported, unsupported)
        return 0
    else:
        _logger.warn("%i tests passed, %i failures, %i unsupported features", total - (failures + unsupported), failures, unsupported)
        return 1


if __name__ == "__main__":
    sys.exit(main())
