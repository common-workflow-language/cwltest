#!/usr/bin/env python3
"""Entry point for cwltest."""

import argparse
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set, Union

import junit_xml
import pkg_resources
import schema_salad.avro
import schema_salad.ref_resolver
import schema_salad.schema
from rdflib import Graph

from cwltest import REQUIRED, UNSUPPORTED_FEATURE, logger, utils
from cwltest.argparser import arg_parser
from cwltest.utils import TestResult

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
        timeout: int,
        junit_verbose: Optional[bool] = False,
        verbose: Optional[bool] = False,
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
    return utils.run_test_plain(args, test, test_number, timeout, junit_verbose, verbose)


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
