import json
import os
import re
import shlex
import shutil
import subprocess  # nosec
import sys
import tempfile
import time
from collections import defaultdict
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    MutableMapping,
    MutableSequence,
    Optional,
    Tuple,
    Union,
    cast,
)

import junit_xml
import pkg_resources
import ruamel.yaml.scanner
import schema_salad.avro
import schema_salad.ref_resolver
import schema_salad.schema
from cwltest.compare import CompareFail, compare
from rdflib import Graph
from ruamel.yaml.scalarstring import ScalarString
from schema_salad.exceptions import ValidationException

from cwltest import REQUIRED, UNSUPPORTED_FEATURE, logger, templock


class CWLTestConfig(object):
    """Store configuration values for cwltest."""

    def __init__(
        self,
        basedir: Optional[str] = None,
        outdir: Optional[str] = None,
        classname: Optional[str] = None,
        tool: Optional[str] = None,
        args: Optional[List[str]] = None,
        testargs: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        verbose: Optional[bool] = None,
        runner_quiet: Optional[bool] = None,
    ) -> None:
        """Initialize test configuration."""
        self.basedir: str = basedir or os.getcwd()
        self.outdir: Optional[str] = outdir
        self.classname: str = classname or ""
        self.tool: str = tool or "cwl-runner"
        self.args: List[str] = args or []
        self.testargs: List[str] = testargs or []
        self.timeout: Optional[int] = timeout
        self.verbose: bool = verbose or False
        self.runner_quiet: bool = runner_quiet or True


class TestResult:
    """Encapsulate relevant test result data."""

    def __init__(
        self,
        return_code: int,
        standard_output: str,
        error_output: str,
        duration: float,
        classname: str,
        message: str = "",
    ) -> None:
        """Initialize a TestResult object."""
        self.return_code = return_code
        self.standard_output = standard_output
        self.error_output = error_output
        self.duration = duration
        self.message = message
        self.classname = classname

    def create_test_case(self, test: Dict[str, Any]) -> junit_xml.TestCase:
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
    raise Exception(f"Unsupported type {type(obj)} of '{obj}'.")


def generate_badges(
    badgedir: str, ntotal: Dict[str, int], npassed: Dict[str, int]
) -> None:
    """Generate badges with conformance levels."""
    os.mkdir(badgedir)
    for t, v in ntotal.items():
        percent = int((npassed[t] / float(v)) * 100)
        if npassed[t] == v:
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


def get_test_number_by_key(
    tests: List[Dict[str, str]], key: str, value: str
) -> Optional[int]:
    """Retrieve the test index from its name."""
    for i, test in enumerate(tests):
        if key in test and test[key] == value:
            return i
    return None


def load_and_validate_tests(path: str) -> Tuple[Any, Dict[str, Any]]:
    """
    Load and validate the given test file against the cwltest schema.

    This also processes $import directives.
    """
    schema_resource = pkg_resources.resource_stream(__name__, "cwltest-schema.yml")
    cache: Optional[Dict[str, Union[str, Graph, bool]]] = {
        "https://w3id.org/cwl/cwltest/cwltest-schema.yml": schema_resource.read().decode(
            "utf-8"
        )
    }
    (document_loader, avsc_names, _, _,) = schema_salad.schema.load_schema(
        "https://w3id.org/cwl/cwltest/cwltest-schema.yml", cache=cache
    )

    if not isinstance(avsc_names, schema_salad.avro.schema.Names):
        print(avsc_names)
        raise ValidationException(
            "Wrong instance for avsc_names: {}".format(type(avsc_names))
        )

    tests, metadata = schema_salad.schema.load_and_validate(
        document_loader, avsc_names, path, True
    )
    tests = cast(List[Dict[str, Any]], _clean_ruamel(tests))

    return tests, metadata


def parse_results(
    results: Iterable[TestResult],
    tests: List[Dict[str, Any]],
    suite_name: Optional[str] = None,
    report: Optional[junit_xml.TestSuite] = None,
) -> Tuple[
    int,  # total
    int,  # passed
    int,  # failures
    int,  # unsupported
    Dict[str, int],
    Dict[str, int],
    Dict[str, int],
    Dict[str, int],
    Optional[junit_xml.TestSuite],
]:
    """
    Parse the results and return statistics and an optional report.

    Returns the total number of tests, dictionary of test counts
    (total, passed, failed, unsupported) by tag, and a jUnit XML report.
    """
    total = 0
    passed = 0
    failures = 0
    unsupported = 0
    ntotal: Dict[str, int] = defaultdict(int)
    nfailures: Dict[str, int] = defaultdict(int)
    nunsupported: Dict[str, int] = defaultdict(int)
    npassed: Dict[str, int] = defaultdict(int)

    for i, test_result in enumerate(results):
        test_case = test_result.create_test_case(tests[i])
        test_case.url = (
            f"cwltest:{suite_name}#{i + 1}"
            if suite_name is not None
            else "cwltest:#{i + 1}"
        )
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
    args: List[str],
    testargs: Optional[List[str]],
    test: Dict[str, Any],
    cwd: str,
    quiet: Optional[bool] = True,
) -> List[str]:
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
    test: Dict[str, str],
    cwd: str,
) -> Tuple[str, Optional[str]]:
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
    test: Dict[str, str],
    test_number: Optional[int] = None,
) -> TestResult:
    """Plain test runner."""
    out: Dict[str, Any] = {}
    outstr = outerr = ""
    test_command: List[str] = []
    duration = 0.0
    number = "?"
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
        out = json.loads(outstr) if outstr else {}
    except subprocess.CalledProcessError as err:
        if err.returncode == UNSUPPORTED_FEATURE and REQUIRED not in test.get(
            "tags", ["required"]
        ):
            return TestResult(
                UNSUPPORTED_FEATURE, outstr, outerr, duration, config.classname
            )
        if test.get("should_fail", False):
            return TestResult(0, outstr, outerr, duration, config.classname)
        if test_number:
            logger.error(
                """Test %i failed: %s""",
                test_number,
                " ".join([shlex.quote(tc) for tc in test_command]),
            )
        else:
            logger.error(
                """Test failed: %s""",
                " ".join([shlex.quote(tc) for tc in test_command]),
            )
        logger.error(test.get("doc", "").replace("\n", " ").strip())
        if err.returncode == UNSUPPORTED_FEATURE:
            logger.error("Does not support required feature")
        else:
            logger.error("Returned non-zero")
        return TestResult(1, outstr, outerr, duration, config.classname, str(err))
    except (ruamel.yaml.scanner.ScannerError, TypeError) as err:
        logger.error(
            """Test %s failed: %s""",
            number,
            " ".join([shlex.quote(tc) for tc in test_command]),
        )
        logger.error(outstr)
        logger.error("Parse error %s", str(err))
        logger.error(outerr)
    except KeyboardInterrupt:
        logger.error(
            """Test %s interrupted: %s""",
            number,
            " ".join([shlex.quote(tc) for tc in test_command]),
        )
        raise
    except subprocess.TimeoutExpired:
        logger.error(
            """Test %s timed out: %s""",
            number,
            " ".join([shlex.quote(tc) for tc in test_command]),
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

    if test.get("should_fail", False):
        logger.warning(
            """Test %s failed: %s""",
            number,
            " ".join([shlex.quote(tc) for tc in test_command]),
        )
        logger.warning(test.get("doc", "").replace("\n", " ").strip())
        logger.warning("Returned zero but it should be non-zero")
        return TestResult(1, outstr, outerr, duration, config.classname)

    try:
        compare(test.get("output"), out)
    except CompareFail as ex:
        logger.warning(
            """Test %s failed: %s""",
            number,
            " ".join([shlex.quote(tc) for tc in test_command]),
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
        fail_message,
    )


def shortname(name: str) -> str:
    """
    Return the short name of a given name.

    It is a workaround of https://github.com/common-workflow-language/schema_salad/issues/511.
    """
    return [n for n in re.split("[/#]", name) if len(n)][-1]
