"""Discovers CWL test files and converts them to pytest.Items."""

import argparse
import json
import os
import pickle  # nosec
import time
import traceback
from collections.abc import Iterator
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Protocol, Union, cast
from urllib.parse import urljoin

import pytest

from cwltest import REQUIRED, UNSUPPORTED_FEATURE, logger, utils
from cwltest.compare import CompareFail, compare

if TYPE_CHECKING:
    from _pytest._code.code import TracebackStyle
    from _pytest.nodes import Node
    from pluggy import HookCaller


class TestRunner(Protocol):
    """Protocol to type-check test runner functions via the pluggy hook."""

    def __call__(
        self, config: utils.CWLTestConfig, processfile: str, jobfile: Optional[str]
    ) -> list[Optional[dict[str, Any]]]:
        """Type signature for pytest_cwl_execute_test hook results."""
        ...


def _get_comma_separated_option(config: pytest.Config, name: str) -> list[str]:
    options = config.getoption(name)
    if options is None:
        return []
    elif "," in options:
        return [opt.strip() for opt in options.split(",")]
    else:
        return [options.strip()]


def _run_test_hook_or_plain(
    test: dict[str, str],
    config: utils.CWLTestConfig,
    hook: "HookCaller",
) -> utils.TestResult:
    """Run tests using a provided pytest_cwl_execute_test hook or the --cwl-runner."""
    processfile, jobfile = utils.prepare_test_paths(test, config.basedir)
    start_time = time.time()
    reltool = os.path.relpath(test["tool"], start=config.test_basedir)
    tooluri = urljoin(config.test_baseuri, reltool)
    if test.get("job", None):
        reljob = os.path.relpath(test["job"], start=config.test_basedir)
        joburi = urljoin(config.test_baseuri, reljob)
    else:
        joburi = None
    outerr = ""
    hook_out = hook(config=config, processfile=processfile, jobfile=jobfile)
    if not hook_out:
        return utils.run_test_plain(config, test)
    returncode, out = cast(tuple[int, Optional[dict[str, Any]]], hook_out[0])
    duration = time.time() - start_time
    outstr = json.dumps(out) if out is not None else "{}"
    if returncode == UNSUPPORTED_FEATURE:
        if REQUIRED not in test.get("tags", ["required"]):
            return utils.TestResult(
                UNSUPPORTED_FEATURE,
                outstr,
                "",
                duration,
                config.classname,
                config.entry,
                tooluri,
                joburi,
            )
    elif returncode != 0:
        if not bool(test.get("should_fail", False)):
            logger.warning("Test failed unexpectedly: %s %s", processfile, jobfile)
            logger.warning(test.get("doc"))
            message = "Returned non-zero but it should be zero"
            return utils.TestResult(
                1,
                outstr,
                outerr,
                duration,
                config.classname,
                config.entry,
                tooluri,
                joburi,
                message,
            )
        return utils.TestResult(
            0,
            outstr,
            outerr,
            duration,
            config.classname,
            config.entry,
            tooluri,
            joburi,
        )
    if bool(test.get("should_fail", False)):
        return utils.TestResult(
            1,
            outstr,
            outerr,
            duration,
            config.classname,
            config.entry,
            tooluri,
            joburi,
            "Test should failed, but it did not.",
        )

    fail_message = ""

    try:
        compare(test.get("output"), out)
    except CompareFail as ex:
        logger.warning("""Test failed: %s %s""", processfile, jobfile)
        logger.warning(test.get("doc"))
        logger.warning("Compare failure %s", ex)
        fail_message = str(ex)

    return utils.TestResult(
        (1 if fail_message else 0),
        outstr,
        outerr,
        duration,
        config.classname,
        config.entry,
        tooluri,
        joburi,
        fail_message,
    )


class CWLTestException(Exception):
    """custom exception for error reporting."""


class CWLItem(pytest.Item):
    """A CWL test Item."""

    def __init__(
        self,
        name: str,
        parent: Optional["Node"],
        spec: dict[str, Any],
    ) -> None:
        """Initialize this CWLItem."""
        super().__init__(name, parent)
        self.spec = spec

    def runtest(self) -> None:
        """Execute using cwltest."""
        cwl_args = self.config.getoption("cwl_args")
        config = utils.CWLTestConfig(
            basedir=self.config.getoption("cwl_basedir"),
            test_baseuri=self.config.getoption("cwl_basedir"),
            test_basedir=self.config.getoption("cwl_basedir"),
            entry="tests.yaml",
            entry_line="0",
            outdir=str(
                self.config._tmp_path_factory.mktemp(  # type: ignore[attr-defined]
                    self.spec.get("label", "unlabled_test")
                )
            ),
            tool=self.config.getoption("cwl_runner"),
            args=cwl_args.split(" ") if cwl_args else None,
            testargs=self.config.getoption("cwl_test_arg"),
            timeout=self.config.getoption("timeout", None),
            verbose=self.config.getoption("verbose", 0) >= 1,
            runner_quiet=not self.config.getoption("cwl_runner_verbose", False),
        )
        hook = self.config.hook.pytest_cwl_execute_test
        result = _run_test_hook_or_plain(
            self.spec,
            config,
            hook,
        )
        cwl_results = self.config.cwl_results  # type: ignore[attr-defined]
        cast(list[tuple[dict[str, Any], utils.TestResult]], cwl_results).append(
            (self.spec, result)
        )
        if result.return_code != 0:
            raise CWLTestException(self, result)

    def repr_failure(
        self,
        excinfo: pytest.ExceptionInfo[BaseException],
        style: Optional["TracebackStyle"] = None,
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

    def reportinfo(self) -> tuple[Union["os.PathLike[str]", str], Optional[int], str]:
        """Status report."""
        return self.path, 0, "cwl test: %s" % self.name


class CWLYamlFile(pytest.File):
    """A CWL test file."""

    def _add_global_properties(self) -> None:
        """Nonfunctional if xdist is installed and anything besides "-n 0" is used."""
        from _pytest.junitxml import xml_key

        if xml := self.config._store.get(xml_key, None):
            xml.add_global_property("runner", self.config.getoption("cwl_runner"))
            xml.add_global_property(
                "runner_extra_args", self.config.getoption("cwl_args")
            )

    def collect(self) -> Iterator[CWLItem]:
        """Load the cwltest file and yield parsed entries."""
        include: set[str] = set(_get_comma_separated_option(self.config, "cwl_include"))
        exclude: set[str] = set(_get_comma_separated_option(self.config, "cwl_exclude"))
        tags: set[str] = set(_get_comma_separated_option(self.config, "cwl_tags"))
        exclude_tags: set[str] = set(
            _get_comma_separated_option(self.config, "cwl_exclude_tags")
        )
        tests, _ = utils.load_and_validate_tests(str(self.path))
        self._add_global_properties()
        for entry in tests:
            entry_tags = entry.get("tags", [])
            if "label" in entry:
                name = entry["label"]
            elif "id" in entry:
                name = utils.shortname(entry["id"])
            else:
                name = entry.get("doc", "")
            item = CWLItem.from_parent(self, name=name, spec=entry)
            if include and name not in include:
                item.add_marker(
                    pytest.mark.skip(
                        reason=f"Test {name!r} is not in the include list: {','.join(include)}."
                    )
                )
            elif exclude and name in exclude:
                item.add_marker(
                    pytest.mark.skip(reason=f"Test {name!r} is in the exclude list.")
                )
            elif tags and not tags.intersection(entry_tags):
                item.add_marker(
                    pytest.mark.skip(
                        reason=f"Test {name!r} with tags {','.join(entry_tags)}"
                        f" doesn't have a tag on the allowed tag list: {','.join(tags)}."
                    )
                )
            elif exclude_tags and exclude_tags.intersection(entry_tags):
                item.add_marker(
                    pytest.mark.skip(
                        reason=f"Test {name!r} has one or more tags on the exclusion "
                        f" tag list: {','.join(exclude_tags.intersection(entry_tags))}."
                    )
                )
            yield item


__OPTIONS: list[tuple[str, dict[str, Any]]] = [
    (
        "--cwl-runner",
        {
            "type": str,
            "dest": "cwl_runner",
            "default": "cwl-runner",
            "help": "Name of the CWL runner to use.",
        },
    ),
    (
        "--cwl-runner-verbose",
        {
            "dest": "cwl_runner_verbose",
            "default": False,
            "action": "store_true",
            "help": "If set, don't pass --quiet to the CWL runner.",
        },
    ),
    (
        "--cwl-badgedir",
        {
            "type": str,
            "help": "Create badge JSON files, one for each tag (plus a computed "
            "'all' tag), and store them in this directory.",
        },
    ),
    (
        "--cwl-include",
        {
            "type": str,
            "help": "Run specific CWL tests using their short names separated by comma",
        },
    ),
    (
        "--cwl-exclude",
        {
            "type": str,
            "help": "Exclude specific CWL tests using their short names separated by comma",
        },
    ),
    ("--cwl-tags", {"type": str, "help": "Tags to be tested."}),
    ("--cwl-exclude-tags", {"type": str, "help": "Tags not to be tested."}),
    (
        "--cwl-args",
        {
            "type": str,
            "help": "one or more arguments to pass first to tool runner (separated by spaces)",
        },
    ),
    (
        "--cwl-test-arg",
        {
            "type": str,
            "help": "Additional argument given in test cases and required prefix for tool runner.",
            "action": "append",
        },
    ),
    (
        "--cwl-basedir",
        {
            "help": "Basedir to use for tests",
            "default": os.getcwd(),
        },
    ),
]


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add our options to the pytest command line."""
    for entry in __OPTIONS:
        parser.addoption(entry[0], **entry[1])


def _doc_options() -> argparse.ArgumentParser:
    """Generate a stand-alone ArgumentParser to aid in documention."""
    parser = argparse.ArgumentParser("cwltest options for pytest.", add_help=False)
    for entry in __OPTIONS:
        parser.add_argument(entry[0], **entry[1])
    return parser


def pytest_collect_file(
    file_path: Path, parent: pytest.Collector
) -> Optional[pytest.Collector]:
    """Is this file for us."""
    if (
        file_path.suffix == ".yml" or file_path.suffix == ".yaml"
    ) and file_path.stem.endswith(".cwltest"):
        return cast(
            Optional[pytest.Collector],
            CWLYamlFile.from_parent(parent, path=file_path),
        )
    return None


def pytest_configure(config: pytest.Config) -> None:
    """Store the raw tests and the test results."""
    cwl_results: list[tuple[dict[str, Any], utils.TestResult]] = []
    config.cwl_results = cwl_results  # type: ignore[attr-defined]


def _zip_results(
    cwl_results: list[tuple[dict[str, Any], utils.TestResult]],
) -> tuple[list[dict[str, Any]], list[utils.TestResult]]:
    tests, results = (list(item) for item in zip(*cwl_results))
    return tests, results


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Generate badges."""
    cwl_badgedir = session.config.getoption("cwl_badgedir")
    if not cwl_badgedir:
        return

    cwl_results = cast(
        list[tuple[dict[str, Any], utils.TestResult]],
        session.config.cwl_results,  # type: ignore[attr-defined]
    )

    if session.config.pluginmanager.has_plugin("xdist"):
        import xdist  # type: ignore[import-untyped]

        directory = cast(
            pytest.TempPathFactory,
            session.config._tmp_path_factory,  # type: ignore[attr-defined]
        ).getbasetemp()
        if xdist.is_xdist_worker(session):
            if not cwl_results:
                return
            pickle_filename = f"cwltest_{xdist.get_xdist_worker_id(session)}.pickle"
            with (directory.parent / pickle_filename).open("wb") as handle:
                pickle.dump(
                    _zip_results(cwl_results), handle, protocol=pickle.HIGHEST_PROTOCOL
                )
            return

        if xdist.is_xdist_controller(session):
            tests: list[dict[str, Any]] = []
            results: list[utils.TestResult] = []
            for pickle_filepath in directory.glob("cwltest_*"):
                with pickle_filepath.open("rb") as handle:
                    new_tests, new_results = pickle.load(handle)  # nosec
                tests.extend(new_tests)
                results.extend(new_results)
        else:
            if not cwl_results:
                return
            tests, results = _zip_results(cwl_results)

    else:
        if not cwl_results:
            return
        tests, results = _zip_results(cwl_results)

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

    utils.generate_badges(cwl_badgedir, ntotal, npassed, nfailures, nunsupported)


def pytest_addhooks(pluginmanager: pytest.PytestPluginManager) -> None:
    """Register our cwl hooks."""
    from cwltest import hooks

    pluginmanager.add_hookspecs(hooks)
