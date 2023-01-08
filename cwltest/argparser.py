"""Command line argument parsing for cwltest."""
import argparse
import sys

import pkg_resources

from cwltest import DEFAULT_TIMEOUT


def arg_parser() -> argparse.ArgumentParser:
    """Generate a command Line argument parser for cwltest."""
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
    parser.add_argument(
        "--exclude-tags", type=str, default=None, help="Tags not to be tested"
    )
    parser.add_argument("--show-tags", action="store_true", help="Show all Tags.")
    parser.add_argument(
        "--junit-xml", type=str, default=None, help="Path to JUnit xml file"
    )
    parser.add_argument(
        "--junit-verbose",
        action="store_true",
        help="Store more verbose output to JUnit XML file by not passing "
        "'--quiet' to the CWL runner.",
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
        "--badgedir",
        type=str,
        help="Create JSON badges and store them in this directory.",
    )

    pkg = pkg_resources.require("cwltest")
    if pkg:
        ver = f"{sys.argv[0]} {pkg[0].version}"
    else:
        ver = "{} {}".format(sys.argv[0], "unknown version")
    parser.add_argument("--version", action="version", version=ver)

    return parser
