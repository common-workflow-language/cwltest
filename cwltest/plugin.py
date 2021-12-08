"""Discovers CWL test files and converts them to pytest.Items."""
import argparse
import json
import os
import time
from io import StringIO
from typing import (Any, Dict, Iterator, List, Optional, TYPE_CHECKING, Tuple, Union, cast)

import py
import pytest
from typing_extensions import Protocol

from conftest import UnsupportedCWLFeature
from cwltest import DEFAULT_TIMEOUT, REQUIRED, UNSUPPORTED_FEATURE, logger, utils

if TYPE_CHECKING:
    from _pytest.config import Config as PytestConfig
    from _pytest._code.code import ExceptionInfo, _TracebackStyle
    from _pytest.nodes import Node
    from _pytest.config.argparsing import Parser as PytestParser
    from _pytest.config import PytestPluginManager


class TestRunner(Protocol):
    """Protocol to type-check test runner functions via the pluggy hook."""

    def __call__(
            self, description: str, outdir: str, inputs: Optional[str]
    ) -> List[Optional[Dict[str, Any]]]:
        """Type signature for pytest_cwl_execute_test hook results."""
        ...


def _run_test_hook(
        args: Dict[str, Any],
        test: Dict[str, str],
        cwd: str,
        outdir: str,
        hook: TestRunner,
) -> utils.TestResult:
    """Run tests using a provided pytest_cwl_execute_test compatible runner."""
    toolpath, jobpath = utils.prepare_test_paths(test, cwd)
    start_time = time.time()
    outerr = ""
    try:
        out = hook(description=toolpath, outdir=outdir, inputs=jobpath)[0]
    except UnsupportedCWLFeature as unsup:
        duration = time.time() - start_time
        outerr = str(unsup)
        if REQUIRED not in test.get("tags", ["required"]):
            return utils.TestResult(
                UNSUPPORTED_FEATURE, "", outerr, duration, args["classname"]
            )
        if test.get("should_fail", False):
            return utils.TestResult(0, "", outerr, duration, args["classname"])
        return utils.TestResult(1, "", outerr, duration, args["classname"], outerr)
    duration = time.time() - start_time
    outstr = json.dumps(out) if out is not None else "{}"
    fail_message = ""
    if test.get("should_fail", False):
        logger.warning("""Test failed: %s %s""", toolpath, jobpath)
        logger.warning(test.get("doc"))
        logger.warning("Returned zero but it should be non-zero")
        return utils.TestResult(1, outstr, outerr, duration, args["classname"])

    try:
        utils.compare(test.get("output"), out)
    except utils.CompareFail as ex:
        logger.warning("""Test failed: %s %s""", toolpath, jobpath)
        logger.warning(test.get("doc"))
        logger.warning("Compare failure %s", ex)
        fail_message = str(ex)

    return utils.TestResult(
        (1 if fail_message else 0),
        outstr,
        outerr,
        duration,
        args["classname"],
        fail_message,
    )


def pytest_addoption(parser: "PytestParser") -> None:
    """Add our options to the pytest command line."""
    parser.addoption(
        "--cwl-runner",
        type=str,
        dest="cwl_runner",
        default="cwl-runner",
        help="Name of the CWL runner to use.",
    )
    parser.addoption(
        "--cwl-badgedir",
        type=str,
        help="Directory to store JSON file for badges.",
    )
    parser.addoption(
        "--cwl-timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Time of execution in seconds after which the test will be "
             f"skipped. Defaults to {DEFAULT_TIMEOUT} seconds "
             f"({DEFAULT_TIMEOUT / 60} minutes).",
    )
    parser.addoption("--cwl-tags", type=str, default=None, help="Tags to be tested.")
    parser.addoption(
        "--cwl-args",
        help="arguments to pass first to tool runner",
        nargs=argparse.REMAINDER,
    )
    parser.addoption(
        "--cwl-basedir", help="Basedir to use for tests", default=os.getcwd()
    )


class CWLTestException(Exception):
    """custom exception for error reporting."""


class CWLItem(pytest.Item):
    """A CWL test Item."""

    def __init__(
            self,
            name: str,
            parent: Optional["Node"],
            spec: Dict[str, Any],
    ) -> None:
        """Initialize this CWLItem."""
        super().__init__(name, parent)
        self.spec = spec

    def runtest(self) -> None:
        """Execute using cwltest."""
        args = {
            "tool": self.config.getoption("cwl_runner"),
            "args": self.config.getoption("cwl_args", default=None),
            "testargs": None,
            "verbose": True,
            "classname": "",
        }
        outdir = str(self.config._tmp_path_factory.mktemp(  # type: ignore[attr-defined]
            self.spec.get("label", "unlabled_test")))
        hook = self.config.hook.pytest_cwl_execute_test
        if hook:
            result = _run_test_hook(
                args, self.spec, self.config.getoption("cwl_basedir"), outdir, hook
            )
        else:
            result = utils.run_test_plain(
                args, self.spec, self.config.getoption("cwl_timeout")
            )
        cwl_results = self.config.cwl_results  # type: ignore[attr-defined]
        cast(List[Tuple[Dict[str, Any], utils.TestResult]], cwl_results).append(
            (self.spec, result)
        )
        if result.return_code != 0 and not self.spec.get("should_fail", False):
            # unexpected failure
            raise CWLTestException(self, result)

        if result.return_code == 0 and self.spec.get("should_fail", False):
            # missing failure
            raise CWLTestException(self, result)

    def repr_failure(
            self,
            excinfo: "ExceptionInfo[BaseException]",
            style: Optional["_TracebackStyle"] = None,
    ) -> str:
        """
        Document failure reason.

        Called when self.runtest() raises an exception.
        """
        if isinstance(excinfo.value, CWLTestException):
            from ruamel.yaml.main import YAML

            yaml = YAML()
            result = excinfo.value.args[1]
            stream = StringIO()
            yaml.dump(self.spec, stream)
            return "\n".join(
                [
                    "CWL test execution failed. ",
                    result.message,
                    f"Test: {stream.getvalue()}",
                ]
            )
        return ""

    def reportinfo(self) -> Tuple[Union[py.path.local, str], int, str]:
        """Status report."""
        return self.fspath, 0, "cwl test: %s" % self.name


class CWLYamlFile(pytest.File):
    """A CWL test file."""

    def collect(self) -> Iterator[CWLItem]:
        """Load the cwltest file and yield parsed entries."""
        tags: List[str] = self.config.getoption("cwl_tags", default=[])
        for entry, _ in utils.load_and_validate_tests(str(self.fspath)):
            name = entry.get("label", entry["doc"])
            if tags:
                found = False
                for tag in entry.get("tags", []):
                    if tag in tags:
                        found = True
            else:
                found = True
            if found:
                yield CWLItem.from_parent(self, name=name, spec=entry)


def pytest_collect_file(
        parent: pytest.Collector, path: py.path.local
) -> Optional[pytest.Collector]:
    """Is this file for us."""
    if (path.ext == ".yml" or path.ext == ".yaml") and path.basename.startswith(
            "conformance_test"
    ):
        return cast(
            Optional[pytest.Collector],
            CWLYamlFile.from_parent(  # type: ignore[no-untyped-call]
                parent, fspath=path
            ),
        )
    return None


def pytest_configure(config: "PytestConfig") -> None:
    """Store the raw tests and the test results."""
    cwl_results: List[Tuple[Dict[str, Any], utils.TestResult]] = []
    config.cwl_results = cwl_results  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Generate badges."""
    cwl_results = cast(
        List[Tuple[Dict[str, Any], utils.TestResult]],
        getattr(session.config, "cwl_results", None),
    )
    if not cwl_results:
        return
    tests, results = (list(item) for item in zip(*cwl_results))
    (
        total,
        passed,
        failures,
        unsupported,
        ntotal,
        npassed,
        nfailures,
        nunsupported,
        _,
    ) = utils.parse_results(results, tests)
    cwl_badgedir = session.config.getoption("cwl_badgedir")
    if cwl_badgedir:
        utils.generate_badges(cwl_badgedir, ntotal, npassed)


def pytest_addhooks(pluginmanager: "PytestPluginManager") -> None:
    """Register our cwl hooks."""
    from cwltest import hooks

    pluginmanager.add_hookspecs(hooks)
