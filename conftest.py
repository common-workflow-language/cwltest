"""Discovers CWL test files and converts them to pytest.Items."""
from typing import (
    cast,
    Any,
    Dict,
    List,
    Iterator,
    Optional,
    Union,
    Tuple,
    TYPE_CHECKING,
)

import pytest
import py

from cwltest import DEFAULT_TIMEOUT, utils
from cwltest.utils import TestResult

if TYPE_CHECKING:
    from _pytest.config import Config as PytestConfig
    from _pytest._code.code import ExceptionInfo, _TracebackStyle
    from _pytest.nodes import Node
    from _pytest.config.argparsing import Parser as PytestParser


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
            "args": {},
            "testargs": None,
            "verbose": True,
            "classname": "cwltool",
        }
        result = utils.run_test_plain(args, self.spec, DEFAULT_TIMEOUT)
        cwl_results = self.config.cwl_results  # type: ignore[attr-defined]
        cast(List[Tuple[Dict[str, Any], TestResult]], cwl_results).append(
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
            import yaml

            result = excinfo.value.args[1]
            return "\n".join(
                [
                    "CWL test execution failed. ",
                    result.message,
                    f"Test: {yaml.dump(self.spec)}",
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
        for entry, _ in utils.load_and_validate_tests(str(self.fspath)):
            name = entry.get("label", entry["doc"])
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
    cwl_results: List[Tuple[Dict[str, Any], TestResult]] = []
    config.cwl_results = cwl_results  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Generate badges."""
    cwl_results = cast(
        List[Tuple[Dict[str, Any], TestResult]],
        getattr(session.config, "cwl_results", None),
    )
    if not cwl_results:
        return
    results, tests = (list(item) for item in zip(*cwl_results))
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
