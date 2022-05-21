#!/usr/bin/env python

import argparse
import json
import logging
import os
import shutil
import subprocess  # nosec
import sys
import tempfile
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from shlex import quote
from typing import Any, Dict, List, Optional, Set, Union

import junit_xml
import pkg_resources  # part of setuptools
import ruamel.yaml.scanner as yamlscanner
import schema_salad.avro.schema
import schema_salad.ref_resolver
import schema_salad.schema
from rdflib import Graph

from cwltest.utils import (
    REQUIRED,
    CompareFail,
    TestResult,
    compare,
    get_test_number_by_key,
)

_logger = logging.getLogger("cwltest")
_logger.addHandler(logging.StreamHandler())
_logger.setLevel(logging.INFO)

UNSUPPORTED_FEATURE = 33
DEFAULT_TIMEOUT = 600  # 10 minutes

templock = threading.Lock()


def prepare_test_command(
    tool,  # type: str
    args,  # type: List[str]
    testargs,  # type: Optional[List[str]]
    test,  # type: Dict[str, str]
    cwd,  # type: str
    verbose=False,  # type: bool
):  # type: (...) -> List[str]
    """Turn the test into a command line."""
    test_command = [tool]
    test_command.extend(args)

    # Add additional arguments given in test case
    if testargs is not None:
        for testarg in testargs:
            (test_case_name, prefix) = testarg.split("==")
            if test_case_name in test:
                test_command.extend([prefix, test[test_case_name]])

    # Add prefixes if running on MacOSX so that boot2docker writes to /Users
    with templock:
        if "darwin" in sys.platform and tool.endswith("cwltool"):
            outdir = tempfile.mkdtemp(prefix=os.path.abspath(os.path.curdir))
            test_command.extend(
                [
                    f"--tmp-outdir-prefix={outdir}",
                    f"--tmpdir-prefix={outdir}",
                ]
            )
        else:
            outdir = tempfile.mkdtemp()
    test_command.extend([f"--outdir={outdir}"])
    if not verbose:
        test_command.extend(["--quiet"])

    cwd = schema_salad.ref_resolver.file_uri(cwd)
    toolpath = test["tool"]
    if toolpath.startswith(cwd):
        toolpath = toolpath[len(cwd) + 1 :]
    test_command.extend([os.path.normcase(toolpath)])

    jobpath = test.get("job")
    if jobpath:
        if jobpath.startswith(cwd):
            jobpath = jobpath[len(cwd) + 1 :]
        test_command.append(os.path.normcase(jobpath))
    return test_command


def run_test(
    args,  # type: argparse.Namespace
    test,  # type: Dict[str, str]
    test_number,  # type: int
    total_tests,  # type: int
    timeout,  # type: int
    junit_verbose=False,  # type: bool
    verbose=False,  # type: bool
):  # type: (...) -> TestResult

    global templock

    out = {}  # type: Dict[str,Any]
    outdir = outstr = outerr = ""
    test_command = []  # type: List[str]
    duration = 0.0
    prefix = ""
    suffix = ""
    if sys.stderr.isatty():
        prefix = "\r"
    else:
        suffix = "\n"
    try:
        process = None  # type: Optional[subprocess.Popen[str]]
        cwd = os.getcwd()
        test_command = prepare_test_command(
            args.tool, args.args, args.testargs, test, cwd, junit_verbose
        )

        if test.get("short_name"):
            sys.stderr.write(
                "%sTest [%i/%i] %s: %s%s\n"
                % (
                    prefix,
                    test_number,
                    total_tests,
                    test.get("short_name"),
                    test.get("doc", "").replace("\n", " ").strip(),
                    suffix,
                )
            )
        else:
            sys.stderr.write(
                "%sTest [%i/%i] %s%s\n"
                % (
                    prefix,
                    test_number,
                    total_tests,
                    test.get("doc", "").replace("\n", " ").strip(),
                    suffix,
                )
            )
        if verbose:
            sys.stderr.write(f"Running: {' '.join(test_command)}\n")
        sys.stderr.flush()

        start_time = time.time()
        stderr = subprocess.PIPE if not args.verbose else None
        process = subprocess.Popen(  # nosec
            test_command,
            stdout=subprocess.PIPE,
            stderr=stderr,
            universal_newlines=True,
            cwd=cwd,
        )
        outstr, outerr = process.communicate(timeout=timeout)
        return_code = process.poll()
        duration = time.time() - start_time
        if return_code:
            raise subprocess.CalledProcessError(return_code, " ".join(test_command))

        out = json.loads(outstr)
    except ValueError as err:
        _logger.error(str(err))
        _logger.error(outstr)
        _logger.error(outerr)
    except subprocess.CalledProcessError as err:
        if err.returncode == UNSUPPORTED_FEATURE and REQUIRED not in test.get(
            "tags", ["required"]
        ):
            return TestResult(
                UNSUPPORTED_FEATURE, outstr, outerr, duration, args.classname
            )
        if test.get("should_fail", False):
            return TestResult(0, outstr, outerr, duration, args.classname)
        _logger.error(
            """Test %i failed: %s""",
            test_number,
            " ".join([quote(tc) for tc in test_command]),
        )
        _logger.error(test.get("doc", "").replace("\n", " ").strip())
        if err.returncode == UNSUPPORTED_FEATURE:
            _logger.error("Does not support required feature")
        else:
            _logger.error("Returned non-zero")
        _logger.error(outerr)
        return TestResult(1, outstr, outerr, duration, args.classname, str(err))
    except (yamlscanner.ScannerError, TypeError) as err:
        _logger.error(
            """Test %i failed: %s""",
            test_number,
            " ".join([quote(tc) for tc in test_command]),
        )
        _logger.error(outstr)
        _logger.error("Parse error %s", str(err))
        _logger.error(outerr)
    except KeyboardInterrupt:
        _logger.error(
            """Test %i interrupted: %s""",
            test_number,
            " ".join([quote(tc) for tc in test_command]),
        )
        raise
    except subprocess.TimeoutExpired:
        _logger.error(
            """Test %i timed out: %s""",
            test_number,
            " ".join([quote(tc) for tc in test_command]),
        )
        _logger.error(test.get("doc", "").replace("\n", " ").strip())
        # Kill and re-communicate to get the logs and reap the child, as
        # instructed in the subprocess docs.
        if process:
            process.kill()
            outstr, outerr = process.communicate()
        return TestResult(2, outstr, outerr, timeout, args.classname, "Test timed out")
    finally:
        if process is not None and process.returncode is None:
            _logger.error("""Terminating lingering process""")
            process.terminate()
            for _ in range(0, 3):
                time.sleep(1)
                if process.poll() is not None:
                    break
            if process.returncode is None:
                process.kill()

    fail_message = ""

    if test.get("should_fail", False):
        _logger.warning(
            """Test %i failed: %s""",
            test_number,
            " ".join([quote(tc) for tc in test_command]),
        )
        _logger.warning(test.get("doc", "").replace("\n", " ").strip())
        _logger.warning("Returned zero but it should be non-zero")
        return TestResult(1, outstr, outerr, duration, args.classname)

    try:
        compare(test.get("output"), out)
    except CompareFail as ex:
        _logger.warning(
            """Test %i failed: %s""",
            test_number,
            " ".join([quote(tc) for tc in test_command]),
        )
        _logger.warning(test.get("doc", "").replace("\n", " ").strip())
        _logger.warning("Compare failure %s", ex)
        fail_message = str(ex)

    if outdir:
        shutil.rmtree(outdir, True)

    return TestResult(
        (1 if fail_message else 0),
        outstr,
        outerr,
        duration,
        args.classname,
        fail_message,
    )


def arg_parser():  # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(
        description="Common Workflow Language testing framework"
    )
    parser.add_argument(
        "--test", type=str, help="YAML file describing test cases", required=True
    )
    parser.add_argument(
        "--basedir", type=str, help="Basedir to use for tests", default="."
    )
    parser.add_argument("-l", action="store_true", help="List tests then exit")
    parser.add_argument(
        "-n", type=str, default=None, help="Run specific tests, format is 1,3-6,9"
    )
    parser.add_argument(
        "-s",
        type=str,
        default=None,
        help="Run specific tests using their short names separated by comma",
    )
    parser.add_argument(
        "-N",
        type=str,
        default=None,
        help="Exclude specific tests by number, format is 1,3-6,9",
    )
    parser.add_argument(
        "-S",
        type=str,
        default=None,
        help="Exclude specific tests by short names separated by comma",
    )
    parser.add_argument(
        "--tool",
        type=str,
        default="cwl-runner",
        help="CWL runner executable to use (default 'cwl-runner'",
    )
    parser.add_argument(
        "--only-tools", action="store_true", help="Only test CommandLineTools"
    )
    parser.add_argument("--tags", type=str, default=None, help="Tags to be tested")
    parser.add_argument("--show-tags", action="store_true", help="Show all Tags.")
    parser.add_argument(
        "--junit-xml", type=str, default=None, help="Path to JUnit xml file"
    )
    parser.add_argument(
        "--junit-verbose",
        action="store_true",
        help="Store more verbose output to JUnit xml file",
    )
    parser.add_argument(
        "--test-arg",
        type=str,
        help="Additional argument "
        "given in test cases and required prefix for tool runner.",
        default=None,
        metavar="cache==--cache-dir",
        action="append",
        dest="testargs",
    )
    parser.add_argument(
        "args", help="arguments to pass first to tool runner", nargs=argparse.REMAINDER
    )
    parser.add_argument(
        "-j",
        type=int,
        default=1,
        help="Specifies the number of tests to run simultaneously "
        "(defaults to one).",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="More verbose output during test run."
    )
    parser.add_argument(
        "--classname",
        type=str,
        default="",
        help="Specify classname for the Test Suite.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Time of execution in seconds after which the test will be "
        "skipped. Defaults to {} seconds ({} minutes).".format(
            DEFAULT_TIMEOUT, DEFAULT_TIMEOUT / 60
        ),
    )
    parser.add_argument(
        "--badgedir", type=str, help="Directory that stores JSON files for badges."
    )

    pkg = pkg_resources.require("cwltest")
    if pkg:
        ver = f"{sys.argv[0]} {pkg[0].version}"
    else:
        ver = "{} {}".format(sys.argv[0], "unknown version")
    parser.add_argument("--version", action="version", version=ver)

    return parser


def expand_number_range(nr: str) -> List[int]:
    ans: List[int] = []
    for s in nr.split(","):
        sp = s.split("-")
        if len(sp) == 2:
            ans.extend(range(int(sp[0]) - 1, int(sp[1])))
        else:
            ans.append(int(s) - 1)
    return ans


def main():  # type: () -> int

    args = arg_parser().parse_args(sys.argv[1:])
    if "--" in args.args:
        args.args.remove("--")

    # Remove test arguments with wrong syntax
    if args.testargs is not None:
        args.testargs = [
            testarg for testarg in args.testargs if testarg.count("==") == 1
        ]

    if not args.test:
        arg_parser().print_help()
        return 1

    schema_resource = pkg_resources.resource_stream(__name__, "cwltest-schema.yml")
    cache = {
        "https://w3id.org/cwl/cwltest/cwltest-schema.yml": schema_resource.read().decode(
            "utf-8"
        )
    }  # type: Optional[Dict[str, Union[str, Graph, bool]]]
    (document_loader, avsc_names, _, _,) = schema_salad.schema.load_schema(
        "https://w3id.org/cwl/cwltest/cwltest-schema.yml", cache=cache
    )

    if not isinstance(avsc_names, schema_salad.avro.schema.Names):
        print(avsc_names)
        return 1

    tests, metadata = schema_salad.schema.load_and_validate(
        document_loader, avsc_names, args.test, True
    )

    failures = 0
    unsupported = 0
    passed = 0
    suite_name, _ = os.path.splitext(os.path.basename(args.test))
    report = junit_xml.TestSuite(suite_name, [])

    # the number of total tests, failured tests, unsupported tests and passed tests for each tag
    ntotal = defaultdict(int)  # type: Dict[str, int]
    nfailures = defaultdict(int)  # type: Dict[str, int]
    nunsupported = defaultdict(int)  # type: Dict[str, int]
    npassed = defaultdict(int)  # type: Dict[str, int]

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

    if args.tags:
        alltests = tests
        tests = []
        tags = args.tags.split(",")
        for t in alltests:
            ts = t.get("tags", [])
            if any(tag in ts for tag in tags):
                tests.append(t)

    for t in tests:
        if t.get("label"):
            t["short_name"] = t["label"]

    if args.show_tags:
        alltags = set()  # type: Set[str]
        for t in tests:
            ts = t.get("tags", [])
            alltags |= set(ts)
        for tag in alltags:
            print(tag)
        return 0

    if args.l:
        for i, t in enumerate(tests):
            if t.get("short_name"):
                print(
                    "[%i] %s: %s"
                    % (
                        i + 1,
                        t["short_name"],
                        t.get("doc", "").replace("\n", " ").strip(),
                    )
                )
            else:
                print("[%i] %s" % (i + 1, t.get("doc", "").replace("\n", " ").strip()))

        return 0

    if args.n is not None or args.s is not None:
        ntest = []
        if args.n is not None:
            ntest = expand_number_range(args.n)
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

    exclude_n = []
    if args.N is not None:
        exclude_n = expand_number_range(args.N)
    if args.S is not None:
        for s in args.S.split(","):
            test_number = get_test_number_by_key(tests, "short_name", s)
            if test_number:
                exclude_n.append(test_number)
            else:
                _logger.error('Test with short name "%s" not found ', s)
                return 1

    ntest = list(filter(lambda x: x not in exclude_n, ntest))

    total = 0
    with ThreadPoolExecutor(max_workers=args.j) as executor:
        jobs = [
            executor.submit(
                run_test,
                args,
                tests[i],
                i + 1,
                len(tests),
                args.timeout,
                args.junit_verbose,
                args.verbose,
            )
            for i in ntest
        ]
        try:
            for i, job in zip(ntest, jobs):
                test_result = job.result()
                test_case = test_result.create_test_case(tests[i])
                test_case.url = f"cwltest:{suite_name}#{i + 1}"
                total += 1
                tags = tests[i].get("tags", [])
                for t in tags:
                    ntotal[t] += 1

                return_code = test_result.return_code
                category = test_case.category
                if return_code == 0:
                    passed += 1
                    for t in tags:
                        npassed[t] += 1
                elif return_code != 0 and return_code != UNSUPPORTED_FEATURE:
                    failures += 1
                    for t in tags:
                        nfailures[t] += 1
                    test_case.add_failure_info(output=test_result.message)
                elif return_code == UNSUPPORTED_FEATURE and category == REQUIRED:
                    failures += 1
                    for t in tags:
                        nfailures[t] += 1
                    test_case.add_failure_info(output=test_result.message)
                elif category != REQUIRED and return_code == UNSUPPORTED_FEATURE:
                    unsupported += 1
                    for t in tags:
                        nunsupported[t] += 1
                    test_case.add_skipped_info("Unsupported")
                else:
                    raise Exception(
                        "This is impossible, return_code: {}, category: "
                        "{}".format(return_code, category)
                    )
                report.test_cases.append(test_case)
        except KeyboardInterrupt:
            for job in jobs:
                job.cancel()
            _logger.error("Tests interrupted")

    if args.junit_xml:
        with open(args.junit_xml, "w") as xml:
            junit_xml.TestSuite.to_file(xml, [report])

    if args.badgedir:
        os.mkdir(args.badgedir)
        for t, v in ntotal.items():
            percent = int((npassed[t] / float(v)) * 100)
            if npassed[t] == v:
                color = "green"
            elif t == "required":
                color = "red"
            else:
                color = "yellow"

            with open(f"{args.badgedir}/{t}.json", "w") as out:
                out.write(
                    json.dumps(
                        {
                            "subject": f"{t}",
                            "status": f"{percent}%",
                            "color": color,
                        }
                    )
                )

    if failures == 0 and unsupported == 0:
        _logger.info("All tests passed")
        return 0
    if failures == 0 and unsupported > 0:
        _logger.warning(
            "%i tests passed, %i unsupported features", total - unsupported, unsupported
        )
        return 0
    _logger.warning(
        "%i tests passed, %i failures, %i unsupported features",
        total - (failures + unsupported),
        failures,
        unsupported,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
