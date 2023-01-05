"""Discovers CWL test files and converts them to pytest.Items."""
import argparse
import json
import os
import time
import traceback
from io import StringIO
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    TYPE_CHECKING,
    Tuple,
    Union,
    cast,
)

import pytest
from typing_extensions import Protocol

from cwltest import DEFAULT_TIMEOUT, REQUIRED, UNSUPPORTED_FEATURE, logger, utils
from cwltest.compare import CompareFail, compare

if TYPE_CHECKING:
    from _pytest.config import Config as PytestConfig
    from _pytest.compat import LEGACY_PATH
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


def _run_test_hook_or_plain(
    test: Dict[str, str],
    config: utils.CWLTestConfig,
    hook: TestRunner,
) -> utils.TestResult:
    """Run tests using a provided pytest_cwl_execute_test hook or the --cwl-runner."""
    toolpath, jobpath = utils.prepare_test_paths(test, config.basedir)
    start_time = time.time()
    outerr = ""
    hook_out = hook(
        description=toolpath, outdir=cast(str, config.outdir), inputs=jobpath
    )
    if not hook_out:
        return utils.run_test_plain(config, test)
    returncode, out = cast(Tuple[int, Optional[Dict[str, Any]]], hook_out[0])
    duration = time.time() - start_time
    outstr = json.dumps(out) if out is not None else "{}"
    if returncode == UNSUPPORTED_FEATURE:
        if REQUIRED not in test.get("tags", ["required"]):
            return utils.TestResult(
                UNSUPPORTED_FEATURE, outstr, "", duration, config.classname
            )
    elif returncode != 0:
        if not bool(test.get("should_fail", False)):
            logger.warning("Test failed unexpectedly: %s %s", toolpath, jobpath)
            logger.warning(test.get("doc"))
            message = "Returned non-zero but it should be zero"
            return utils.TestResult(
                1, outstr, outerr, duration, config.classname, message
            )
        return utils.TestResult(0, outstr, outerr, duration, config.classname)
    if bool(test.get("should_fail", False)):
        return utils.TestResult(
            1,
            outstr,
            outerr,
            duration,
            config.classname,
            "Test should failed, but it did not.",
        )

    fail_message = ""

    try:
        compare(test.get("output"), out)
    except CompareFail as ex:
        logger.warning("""Test failed: %s %s""", toolpath, jobpath)
        logger.warning(test.get("doc"))
        logger.warning("Compare failure %s", ex)
        fail_message = str(ex)

    return utils.TestResult(
        (1 if fail_message else 0),
        outstr,
        outerr,
        duration,
        config.classname,
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
    parser.addoption("--cwl-tags", type=str, help="Tags to be tested.")
    parser.addoption("--cwl-exclude-tags", type=str, help="Tags not to be tested.")
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
        config = utils.CWLTestConfig(
            basedir=self.config.getoption("cwl_basedir"),
            outdir=str(
                self.config._tmp_path_factory.mktemp(  # type: ignore[attr-defined]
                    self.spec.get("label", "unlabled_test")
                )
            ),
            tool=self.config.getoption("cwl_runner"),
            args=self.config.getoption("cwl_args"),
            timeout=self.config.getoption("cwl_timeout"),
        )
        hook = self.config.hook.pytest_cwl_execute_test
        result = _run_test_hook_or_plain(
            self.spec,
            config,
            hook,
        )
        cwl_results = self.config.cwl_results  # type: ignore[attr-defined]
        cast(List[Tuple[Dict[str, Any], utils.TestResult]], cwl_results).append(
            (self.spec, result)
        )
        if result.return_code != 0:
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
        else:
            return (
                f"{excinfo.type.__name__} occurred during CWL test execution:\n"
                + "".join(
                    traceback.format_exception(
                        excinfo.type, excinfo.value, excinfo.traceback[0]._rawentry
                    )
                )
            )

    def reportinfo(self) -> Tuple[Union["os.PathLike[str]", str], Optional[int], str]:
        """Status report."""
        return self.fspath, 0, "cwl test: %s" % self.name


class CWLYamlFile(pytest.File):
    """A CWL test file."""

    def collect(self) -> Iterator[CWLItem]:
        """Load the cwltest file and yield parsed entries."""
        tags: Set[str] = set(self.config.getoption("cwl_tags") or [])
        exclude_tags: Set[str] = set(self.config.getoption("cwl_exclude_tags") or [])
        tests, _ = utils.load_and_validate_tests(str(self.path))
        for entry in tests:
            name = entry.get("label", entry["doc"])
            if (
                (tags and tags.intersection(entry.get("tags", [])))
                or (exclude_tags and not tags.intersection(entry.get("tags", [])))
                or (not tags and not exclude_tags)
            ):
                yield CWLItem.from_parent(self, name=name, spec=entry)


def pytest_collect_file(
    file_path: Path, path: "LEGACY_PATH", parent: pytest.Collector
) -> Optional[pytest.Collector]:
    """Is this file for us."""
    if (
        file_path.suffix == ".yml" or file_path.suffix == ".yaml"
    ) and file_path.stem.startswith("conformance_test"):
        return cast(
            Optional[pytest.Collector],
            CWLYamlFile.from_parent(parent, path=file_path),
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
