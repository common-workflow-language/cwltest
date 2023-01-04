#!/usr/bin/env python3
"""Entry point for cwltest."""

import argparse
import json
import os
import shlex
import shutil
import subprocess  # nosec
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set, Union

import junit_xml
import pkg_resources
import ruamel.yaml.scanner
import schema_salad.avro
import schema_salad.ref_resolver
import schema_salad.schema
from rdflib import Graph

from cwltest import REQUIRED, UNSUPPORTED_FEATURE, logger, utils
from cwltest.argparser import arg_parser
from cwltest.utils import TestResult


def _run_test(
    args,  # type: argparse.Namespace
    test,  # type: Dict[str, str]
    test_number,  # type: int
    total_tests,  # type: int
    timeout,  # type: int
    junit_verbose=False,  # type: bool
    verbose=False,  # type: bool
):  # type: (...) -> TestResult
    out = {}  # type: Dict[str,Any]
    outdir = outstr = outerr = ""
    test_command = []  # type: List[str]
    duration = 0.0
    process = None  # type: Optional[subprocess.Popen[str]]
    prefix = ""
    suffix = ""
    if sys.stderr.isatty():
        prefix = "\r"
    else:
        suffix = "\n"
    try:
        cwd = os.getcwd()
        test_command = utils.prepare_test_command(
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
        logger.error(str(err))
        logger.error(outstr)
        logger.error(outerr)
    except subprocess.CalledProcessError as err:
        if err.returncode == UNSUPPORTED_FEATURE and REQUIRED not in test.get(
            "tags", ["required"]
        ):
            return utils.TestResult(
                UNSUPPORTED_FEATURE, outstr, outerr, duration, args.classname
            )
        if test.get("should_fail", False):
            return utils.TestResult(0, outstr, outerr, duration, args.classname)
        logger.error(
            """Test %i failed: %s""",
            test_number,
            " ".join([shlex.quote(tc) for tc in test_command]),
        )
        logger.error(test.get("doc", "").replace("\n", " ").strip())
        if err.returncode == UNSUPPORTED_FEATURE:
            logger.error("Does not support required feature")
        else:
            logger.error("Returned non-zero")
        logger.error(outerr)
        return utils.TestResult(1, outstr, outerr, duration, args.classname, str(err))
    except (ruamel.yaml.scanner.ScannerError, TypeError) as err:
        logger.error(
            """Test %i failed: %s""",
            test_number,
            " ".join([shlex.quote(tc) for tc in test_command]),
        )
        logger.error(outstr)
        logger.error("Parse error %s", str(err))
        logger.error(outerr)
    except KeyboardInterrupt:
        logger.error(
            """Test %i interrupted: %s""",
            test_number,
            " ".join([shlex.quote(tc) for tc in test_command]),
        )
        raise
    except subprocess.TimeoutExpired:
        logger.error(
            """Test %i timed out: %s""",
            test_number,
            " ".join([shlex.quote(tc) for tc in test_command]),
        )
        logger.error(test.get("doc", "").replace("\n", " ").strip())
        # Kill and re-communicate to get the logs and reap the child, as
        # instructed in the subprocess docs.
        if process:
            process.kill()
            outstr, outerr = process.communicate()
        return utils.TestResult(
            2, outstr, outerr, timeout, args.classname, "Test timed out"
        )
    finally:
        if process is not None and process.returncode is None:
            logger.error("""Terminating lingering process""")
            process.terminate()
            for _ in range(0, 3):
                time.sleep(1)
                if process.poll() is not None:
                    break
            if process.returncode is None:
                process.kill()

    fail_message = ""

    if test.get("should_fail", False):
        logger.warning(
            """Test %i failed: %s""",
            test_number,
            " ".join([shlex.quote(tc) for tc in test_command]),
        )
        logger.warning(test.get("doc", "").replace("\n", " ").strip())
        logger.warning("Returned zero but it should be non-zero")
        return utils.TestResult(1, outstr, outerr, duration, args.classname)

    try:
        utils.compare(test.get("output"), out)
    except utils.CompareFail as ex:
        logger.warning(
            """Test %i failed: %s""",
            test_number,
            " ".join([shlex.quote(tc) for tc in test_command]),
        )
        logger.warning(test.get("doc", "").replace("\n", " ").strip())
        logger.warning("Compare failure %s", ex)
        fail_message = str(ex)

    if outdir:
        shutil.rmtree(outdir, True)

    return utils.TestResult(
        (1 if fail_message else 0),
        outstr,
        outerr,
        duration,
        args.classname,
        fail_message,
    )


def _expand_number_range(nr: str) -> List[int]:
    result: List[int] = []
    for s in nr.split(","):
        sp = s.split("-")
        if len(sp) == 2:
            result.extend(range(int(sp[0]) - 1, int(sp[1])))
        else:
            result.append(int(s) - 1)
    return result


def main() -> int:
    """Run the main logic loop."""
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

    # the number of total tests, failed tests, unsupported tests and passed tests for each tag
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

    if args.exclude_tags:
        ex_tests = []
        tags = args.exclude_tags.split(",")
        for t in tests:
            ts = t.get("tags", [])
            if all(tag not in ts for tag in tags):
                ex_tests.append(t)
        tests = ex_tests

    for t in tests:
        if t.get("label"):
            logger.warning("The `label` field is deprecated. Use `id` field instead.")
            t["short_name"] = t["label"]
        elif t.get("id"):
            if isinstance(t.get("id"), str):
                t["short_name"] = utils.shortname(t["id"])
            else:
                logger.warning(
                    "The `id` field with integer is deprecated. Use string identifier instead."
                )
        else:
            logger.warning("The `id` field is missing.")

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
            ntest = _expand_number_range(args.n)
        if args.s is not None:
            for s in args.s.split(","):
                test_number = utils.get_test_number_by_key(tests, "short_name", s)
                if test_number:
                    ntest.append(test_number)
                else:
                    logger.error('Test with short name "%s" not found ', s)
                    return 1
    else:
        ntest = list(range(0, len(tests)))

    exclude_n = []
    if args.N is not None:
        exclude_n = _expand_number_range(args.N)
    if args.S is not None:
        for s in args.S.split(","):
            test_number = utils.get_test_number_by_key(tests, "short_name", s)
            if test_number:
                exclude_n.append(test_number)
            else:
                logger.error('Test with short name "%s" not found ', s)
                return 1

    ntest = list(filter(lambda x: x not in exclude_n, ntest))

    total = 0
    with ThreadPoolExecutor(max_workers=args.j) as executor:
        jobs = [
            executor.submit(
                _run_test,
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
                elif return_code != UNSUPPORTED_FEATURE:
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
            logger.error("Tests interrupted")

    if args.junit_xml:
        with open(args.junit_xml, "w") as xml:
            junit_xml.to_xml_report_file(xml, [report])

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
        logger.info("All tests passed")
        return 0
    if failures == 0 and unsupported > 0:
        logger.warning(
            "%i tests passed, %i unsupported features", total - unsupported, unsupported
        )
        return 0
    logger.warning(
        "%i tests passed, %i failures, %i unsupported features",
        total - (failures + unsupported),
        failures,
        unsupported,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
