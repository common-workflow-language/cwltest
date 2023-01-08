#!/usr/bin/env python3
"""Entry point for cwltest."""

import argparse
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set, cast

import junit_xml
import schema_salad.avro
import schema_salad.ref_resolver
import schema_salad.schema
from cwltest.argparser import arg_parser
from cwltest.utils import CWLTestConfig, TestResult
from schema_salad.exceptions import ValidationException

from cwltest import logger, utils

if sys.stderr.isatty():
    PREFIX = "\r"
    SUFFIX = ""
else:
    PREFIX = ""
    SUFFIX = "\n"


def _run_test(
    args: argparse.Namespace,
    test: Dict[str, str],
    test_number: int,
    total_tests: int,
) -> TestResult:
    if test.get("short_name"):
        sys.stderr.write(
            "%sTest [%i/%i] %s: %s%s\n"
            % (
                PREFIX,
                test_number,
                total_tests,
                test.get("short_name"),
                test.get("doc", "").replace("\n", " ").strip(),
                SUFFIX,
            )
        )
    else:
        sys.stderr.write(
            "%sTest [%i/%i] %s%s\n"
            % (
                PREFIX,
                test_number,
                total_tests,
                test.get("doc", "").replace("\n", " ").strip(),
                SUFFIX,
            )
        )
    sys.stderr.flush()
    config = CWLTestConfig(
        basedir=args.basedir,
        classname=args.classname,
        tool=args.tool,
        args=args.args,
        testargs=args.testargs,
        timeout=args.timeout,
        verbose=args.verbose,
        runner_quiet=not args.junit_verbose,
    )
    return utils.run_test_plain(config, test, test_number)


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

    try:
        tests, metadata = utils.load_and_validate_tests(args.test)
    except ValidationException:
        return 1

    failures = 0
    unsupported = 0
    suite_name, _ = os.path.splitext(os.path.basename(args.test))
    report: Optional[junit_xml.TestSuite] = junit_xml.TestSuite(suite_name, [])

    ntotal = defaultdict(int)  # type: Dict[str, int]
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
        tags = set(args.tags.split(","))
        tests = [t for t in tests if tags.intersection(t.get("tags", []))]

    if args.exclude_tags:
        tags = set(args.exclude_tags.split(","))
        tests = [t for t in tests if not tags.intersection(t.get("tags", []))]

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
            )
            for i in ntest
        ]
        try:
            (
                total,
                passed,
                failures,
                unsupported,
                ntotal,
                npassed,
                nfailures,
                nunsupported,
                report,
            ) = utils.parse_results(
                (job.result() for job in jobs), tests, suite_name, report
            )
        except KeyboardInterrupt:
            for job in jobs:
                job.cancel()
            logger.error("Tests interrupted")

    if args.junit_xml:
        with open(args.junit_xml, "w") as xml:
            junit_xml.to_xml_report_file(xml, [cast(junit_xml.TestSuite, report)])

    if args.badgedir:
        utils.generate_badges(args.badgedir, ntotal, npassed)

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
