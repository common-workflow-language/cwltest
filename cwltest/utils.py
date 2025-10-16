import json
import os
import re
import shlex
import shutil
import subprocess  # nosec
import sys
import tempfile
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, MutableMapping, MutableSequence
from importlib.metadata import EntryPoint, entry_points
from importlib.resources import files
from typing import Any, Optional, Union, cast
from urllib.parse import urljoin

import junit_xml
import ruamel.yaml.scanner
import schema_salad.avro
import schema_salad.ref_resolver
import schema_salad.schema
from rdflib import Graph
from ruamel.yaml.scalarstring import ScalarString
from schema_salad.exceptions import ValidationException

import cwltest.compare
import cwltest.stdfsaccess
from cwltest import REQUIRED, UNSUPPORTED_FEATURE, logger, templock
from cwltest.compare import CompareFail, compare


class CWLTestConfig:
    """Store configuration values for cwltest."""

    def __init__(
        self,
        entry: str,
        entry_line: str,
        basedir: Optional[str] = None,
        test_baseuri: Optional[str] = None,
        test_basedir: Optional[str] = None,
        outdir: Optional[str] = None,
        classname: Optional[str] = None,
        tool: Optional[str] = None,
        args: Optional[list[str]] = None,
        testargs: Optional[list[str]] = None,
        timeout: Optional[int] = None,
        verbose: Optional[bool] = None,
        runner_quiet: Optional[bool] = None,
        parse_inputs_only: Optional[bool] = None,
    ) -> None:
        """Initialize test configuration."""
        self.basedir: str = basedir or os.getcwd()
        self.test_baseuri: str = test_baseuri or "file://" + self.basedir
        self.test_basedir: str = test_basedir or self.basedir
        self.outdir: Optional[str] = outdir
        self.classname: str = classname or ""
        self.entry = urljoin(
            self.test_baseuri, os.path.basename(entry) + f"#L{entry_line}"
        )
        self.tool: str = tool or "cwl-runner"
        self.args: list[str] = args or []
        self.testargs: list[str] = testargs or []
        self.timeout: Optional[int] = timeout
        self.verbose: bool = verbose or False
        self.runner_quiet: bool = runner_quiet or True
        self.parse_inputs_only: bool = parse_inputs_only or False


class CWLTestReport:
    """Encapsulate relevant test result data for a markdown report."""

    def __init__(
        self,
        id: Union[int, str],
        category: list[str],
        entry: str,
        tool: str,
        job: Optional[str],
    ) -> None:
        """Initialize a CWLTestReport object."""
        self.id = id
        self.category = category
        self.entry = entry
        self.tool = tool
        self.job = job


class TestResult:
    """Encapsulate relevant test result data."""

    def __init__(
        self,
        return_code: int,
        standard_output: str,
        error_output: str,
        duration: float,
        classname: str,
        entry: str,
        tool: str,
        job: Optional[str],
        message: str = "",
    ) -> None:
        """Initialize a TestResult object."""
        self.return_code = return_code
        self.standard_output = standard_output
        self.error_output = error_output
        self.duration = duration
        self.message = message
        self.classname = classname
        self.entry = entry
        self.tool = tool
        self.job = job

    def create_test_case(self, test: dict[str, Any]) -> junit_xml.TestCase:
        """Create a jUnit XML test case from this test result."""
        doc = test.get("doc", "N/A").strip()
        if test.get("tags"):
            category = ", ".join(test["tags"])
        else:
            category = REQUIRED
        short_name = test.get("short_name")
        case = junit_xml.TestCase(
            doc,
            elapsed_sec=self.duration,
            file=short_name,
            category=category,
            stdout=self.standard_output,
            stderr=self.error_output,
        )
        if self.return_code > 0:
            case.failure_message = self.message
        return case

    def create_report_entry(self, test: dict[str, Any]) -> CWLTestReport:
        """Package test result into a CWLTestReport."""
        return CWLTestReport(
            test.get("id", "no-id"),
            test.get("tags", ["required"]),
            self.entry,
            self.tool,
            self.job,
        )


def _clean_ruamel_list(obj: list[Any]) -> Any:
    """Entrypoint to transform roundtrip loaded ruamel.yaml to plain objects."""
    new_list = []
    for entry in obj:
        e: Any = _clean_ruamel(entry)
        e["line"] = str(entry.lc.line)
        new_list.append(e)
    return new_list


def _clean_ruamel(obj: Any) -> Any:
    """Transform roundtrip loaded ruamel.yaml to plain objects."""
    if isinstance(obj, MutableMapping):
        new_dict = {}
        for k, v in obj.items():
            new_dict[str(k)] = _clean_ruamel(v)
        return new_dict
    if isinstance(obj, MutableSequence):
        new_list = []
        for entry in obj:
            new_list.append(_clean_ruamel(entry))
        return new_list
    if isinstance(obj, ScalarString):
        return str(obj)
    for typ in int, float, bool, str:
        if isinstance(obj, typ):
            return typ(obj)
    if obj is None:
        return None
    raise Exception(f"Unsupported type {type(obj)} of {obj!r}.")


def generate_badges(
    badgedir: str,
    ntotal: dict[str, int],
    npassed: dict[str, list[CWLTestReport]],
    nfailures: dict[str, list[CWLTestReport]],
    nunsupported: dict[str, list[CWLTestReport]],
) -> None:
    """Generate badges with conformance levels."""
    os.mkdir(badgedir)
    for t, v in ntotal.items():
        percent = int((len(npassed[t]) / float(v)) * 100)
        if len(npassed[t]) == v:
            color = "green"
        elif t == "required":
            color = "red"
        else:
            color = "yellow"

        with open(f"{badgedir}/{t}.json", "w") as out:
            out.write(
                json.dumps(
                    {
                        "subject": f"{t}",
                        "status": f"{percent}%",
                        "color": color,
                    }
                )
            )

        with open(f"{badgedir}/{t}.md", "w") as out:
            print(f"# `{t}` tests", file=out)
            print("## List of passed tests", file=out)
            for e in npassed[t]:
                base = f"[{shortname(str(e.id))}]({e.entry})"
                tool = f"[tool]({e.tool})"
                if e.job:
                    arr = [tool, f"[job]({e.job})"]
                else:
                    arr = [tool]
                args = ", ".join(arr)
                print(f"- {base} ({args})", file=out)

            print("## List of failed tests", file=out)
            for e in nfailures[t]:
                base = f"[{shortname(str(e.id))}]({e.entry})"
                tool = f"[tool]({e.tool})"
                if e.job:
                    arr = [tool, f"[job]({e.job})"]
                else:
                    arr = [tool]
                args = ", ".join(arr)
                print(f"- {base} ({args})", file=out)

            print("## List of unsupported tests", file=out)
            for e in nunsupported[t]:
                base = f"[{shortname(str(e.id))}]({e.entry})"
                tool = f"[tool]({e.tool})"
                if e.job:
                    arr = [tool, f"[job]({e.job})"]
                else:
                    arr = [tool]
                args = ", ".join(arr)
                print(f"- {base} ({args})", file=out)


def get_test_number_by_key(
    tests: list[dict[str, str]], key: str, value: str
) -> Optional[int]:
    """Retrieve the test index from its name."""
    for i, test in enumerate(tests):
        if key in test and test[key] == value:
            return i
    return None


def load_and_validate_tests(path: str) -> tuple[Any, dict[str, Any]]:
    """
    Load and validate the given test file against the cwltest schema.

    This also processes $import directives.
    """
    schema_resource = files("cwltest").joinpath("cwltest-schema.yml")
    with schema_resource.open("r", encoding="utf-8") as fp:
        cache: Optional[dict[str, Union[str, Graph, bool]]] = {
            "https://w3id.org/cwl/cwltest/cwltest-schema.yml": fp.read()
        }
    (
        document_loader,
        avsc_names,
        _,
        _,
    ) = schema_salad.schema.load_schema(
        "https://w3id.org/cwl/cwltest/cwltest-schema.yml", cache=cache
    )

    if not isinstance(avsc_names, schema_salad.avro.schema.Names):
        print(avsc_names)
        raise ValidationException(f"Wrong instance for avsc_names: {type(avsc_names)}")

    tests, metadata = schema_salad.schema.load_and_validate(
        document_loader, avsc_names, path, True
    )
    tests = cast(list[dict[str, Any]], _clean_ruamel_list(tests))

    return tests, metadata


def parse_results(
    results: Iterable[TestResult],
    tests: list[dict[str, Any]],
    suite_name: Optional[str] = None,
    report: Optional[junit_xml.TestSuite] = None,
) -> tuple[
    int,  # total
    int,  # passed
    int,  # failures
    int,  # unsupported
    dict[str, int],  # total for each tag
    dict[str, list[CWLTestReport]],  # passed for each tag
    dict[str, list[CWLTestReport]],  # failures for each tag
    dict[str, list[CWLTestReport]],  # unsupported for each tag
    Optional[junit_xml.TestSuite],
]:
    """
    Parse the results and return statistics and an optional report.

    An additional tag named "all" will be computed, containing all the test
    results.

    Returns the total number of tests, dictionary of test counts
    (total, passed, failed, unsupported) by tag, and a jUnit XML report.
    """
    total = 0
    passed = 0
    failures = 0
    unsupported = 0
    ntotal: dict[str, int] = Counter()
    nfailures: dict[str, list[CWLTestReport]] = defaultdict(list)
    nunsupported: dict[str, list[CWLTestReport]] = defaultdict(list)
    npassed: dict[str, list[CWLTestReport]] = defaultdict(list)

    for i, test_result in enumerate(results):
        test_case = test_result.create_test_case(tests[i])
        test_report = test_result.create_report_entry(tests[i])
        test_case.url = (
            f"cwltest:{suite_name}#{i + 1}"
            if suite_name is not None
            else "cwltest:#{i + 1}"
        )
        total += 1
        tags = tests[i].get("tags", []) + ["all"]
        for t in tags:
            ntotal[t] += 1

        return_code = test_result.return_code
        category = test_case.category
        if return_code == 0:
            passed += 1
            for t in tags:
                npassed[t].append(test_report)
        elif return_code != 0 and return_code != UNSUPPORTED_FEATURE:
            failures += 1
            for t in tags:
                nfailures[t].append(test_report)
            test_case.add_failure_info(output=test_result.message)
        elif category != REQUIRED and return_code == UNSUPPORTED_FEATURE:
            unsupported += 1
            for t in tags:
                nunsupported[t].append(test_report)
            test_case.add_skipped_info("Unsupported")
        else:
            raise Exception(
                "This is impossible, return_code: {}, category: "
                "{}".format(return_code, category)
            )
        if report:
            report.test_cases.append(test_case)
    return (
        total,
        passed,
        failures,
        unsupported,
        ntotal,
        npassed,
        nfailures,
        nunsupported,
        report,
    )


def prepare_test_command(
    tool: str,
    args: list[str],
    testargs: Optional[list[str]],
    test: dict[str, Any],
    cwd: str,
    quiet: Optional[bool] = True,
) -> list[str]:
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
    if quiet:
        test_command.extend(["--quiet"])
    processfile, jobfile = prepare_test_paths(test, cwd)
    test_command.extend([os.path.normcase(processfile)])
    if jobfile:
        test_command.append(os.path.normcase(jobfile))
    return test_command


def prepare_test_paths(
    test: dict[str, str],
    cwd: str,
) -> tuple[str, Optional[str]]:
    """Determine the test path and the tool path."""
    cwd = schema_salad.ref_resolver.file_uri(cwd)
    processfile = test["tool"]
    if processfile.startswith(cwd):
        processfile = processfile[len(cwd) + 1 :]

    jobfile = test.get("job")
    if jobfile:
        if jobfile.startswith(cwd):
            jobfile = jobfile[len(cwd) + 1 :]
    return processfile, jobfile


def run_test_plain(
    config: CWLTestConfig,
    test: dict[str, str],
    test_number: Optional[int] = None,
) -> TestResult:
    """Plain test runner."""
    out: dict[str, Any] = {}
    outstr = outerr = ""
    test_command: list[str] = []
    duration = 0.0
    number = "?"

    reltool = os.path.relpath(test["tool"], start=config.test_basedir)
    tooluri = urljoin(config.test_baseuri, reltool)
    if test.get("job", None):
        reljob = os.path.relpath(test["job"], start=config.test_basedir)
        joburi = urljoin(config.test_baseuri, reljob)
    else:
        joburi = None

    if test_number is not None:
        number = str(test_number)
    process: Optional[subprocess.Popen[str]] = None
    try:
        cwd = os.getcwd()
        test_command = prepare_test_command(
            config.tool, config.args, config.testargs, test, cwd, config.runner_quiet
        )
        if config.verbose:
            sys.stderr.write(f"Running: {' '.join(test_command)}\n")
        sys.stderr.flush()
        start_time = time.time()
        stderr = subprocess.PIPE if not config.verbose else None
        process = subprocess.Popen(  # nosec
            test_command,
            stdout=subprocess.PIPE,
            stderr=stderr,
            universal_newlines=True,
            cwd=cwd,
        )
        outstr, outerr = process.communicate(timeout=config.timeout)
        return_code = process.poll()
        duration = time.time() - start_time
        if return_code:
            raise subprocess.CalledProcessError(return_code, " ".join(test_command))

        logger.debug('outstr: "%s".', outstr)
        out = json.loads(outstr) if not config.parse_inputs_only and outstr else {}
    except subprocess.CalledProcessError as err:
        if err.returncode == UNSUPPORTED_FEATURE and REQUIRED not in test.get(
            "tags", ["required"]
        ):
            return TestResult(
                UNSUPPORTED_FEATURE,
                outstr,
                outerr,
                duration,
                config.classname,
                config.entry,
                tooluri,
                joburi,
            )
        if test.get("should_fail", False):
            return TestResult(
                0,
                outstr,
                outerr,
                duration,
                config.classname,
                config.entry,
                tooluri,
                joburi,
            )
        if test_number:
            logger.error(
                """Test %i failed: %s""",
                test_number,
                shlex.join(test_command),
            )
        else:
            logger.error(
                """Test failed: %s""",
                shlex.join(test_command),
            )
        logger.error(test.get("doc", "").replace("\n", " ").strip())
        if err.returncode == UNSUPPORTED_FEATURE:
            logger.error("Does not support required feature")
        else:
            logger.error("Returned non-zero")
        return TestResult(
            1,
            outstr,
            outerr,
            duration,
            config.classname,
            config.entry,
            tooluri,
            joburi,
            str(err),
        )
    except (ruamel.yaml.scanner.ScannerError, TypeError) as err:
        logger.error(
            """Test %s failed: %s""",
            number,
            shlex.join(test_command),
        )
        logger.error(outstr)
        logger.error("Parse error %s", str(err))
        logger.error(outerr)
    except KeyboardInterrupt:
        logger.error(
            """Test %s interrupted: %s""",
            number,
            shlex.join(test_command),
        )
        raise
    except json.JSONDecodeError:
        logger.error(
            """Test %s failed: %s""",
            number,
            shlex.join(test_command),
        )
        logger.error(test.get("doc", "").replace("\n", " ").strip())
        invalid_json_msg = "Output is not a valid JSON document: '%s'" % outstr
        logger.error(invalid_json_msg)
        return TestResult(
            1,
            outstr,
            outerr,
            duration,
            config.classname,
            config.entry,
            tooluri,
            joburi,
            invalid_json_msg,
        )
    except subprocess.TimeoutExpired:
        logger.error(
            """Test %s timed out: %s""",
            number,
            shlex.join(test_command),
        )
        logger.error(test.get("doc", "").replace("\n", " ").strip())
        # Kill and re-communicate to get the logs and reap the child, as
        # instructed in the subprocess docs.
        if process:
            process.kill()
            outstr, outerr = process.communicate()
        return TestResult(
            2,
            outstr,
            outerr,
            float(cast(int, config.timeout)),
            config.classname,
            config.entry,
            tooluri,
            joburi,
            "Test timed out",
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

    if test.get("should_fail", False) and not (
        config.parse_inputs_only and "inputs_should_parse" in test.get("tags", [])
    ):
        logger.warning(
            """Test %s failed: %s""",
            number,
            shlex.join(test_command),
        )
        logger.warning(test.get("doc", "").replace("\n", " ").strip())
        logger.warning("Returned zero but it should be non-zero")
        return TestResult(
            1,
            outstr,
            outerr,
            duration,
            config.classname,
            config.entry,
            tooluri,
            joburi,
        )

    if not config.parse_inputs_only:
        try:
            compare(test.get("output"), out)
        except CompareFail as ex:
            logger.warning(
                """Test %s failed: %s""",
                number,
                shlex.join(test_command),
            )
            logger.warning(test.get("doc", "").replace("\n", " ").strip())
            logger.warning("Compare failure %s", ex)
            fail_message = str(ex)

    if config.outdir:
        shutil.rmtree(config.outdir, True)

    return TestResult(
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


def shortname(name: str) -> str:
    """
    Return the short name of a given name.

    It is a workaround of https://github.com/common-workflow-language/schema_salad/issues/511.
    """
    return [n for n in re.split("[/#]", name) if len(n)][-1]


def absuri(path: str) -> str:
    """Return an absolute URI."""
    if "://" in path:
        return path
    return "file://" + os.path.abspath(path)


def load_optional_fsaccess_plugin() -> None:
    """
    Load optional fsaccess plugin.

    Looks for a package with cwltest.fsaccess entry point and if so,
    use that to get a filesystem access object that will be used for
    checking test output.
    """
    fsaccess_eps: list[EntryPoint]

    try:
        # The interface to importlib.metadata.entry_points() changed
        # several times between Python 3.9 and 3.13; the code below
        # actually works fine on all of them but there's no single
        # mypy annotation that works across of them.  Explicitly cast
        # it to a consistent type to make mypy shut up.
        fsaccess_eps = cast(list[EntryPoint], entry_points()["cwltest.fsaccess"])  # type: ignore [redundant-cast, unused-ignore]
    except KeyError:
        return

    if len(fsaccess_eps) == 0:
        return

    if len(fsaccess_eps) > 1:
        logger.warn(
            "More than one cwltest.fsaccess entry point found, selected %s",
            fsaccess_eps[0],
        )

    cwltest.compare.fs_access = fsaccess_eps[0].load()()
