import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

import junit_xml
import pkg_resources
import ruamel.yaml.scanner
import schema_salad.avro
import schema_salad.ref_resolver
import schema_salad.schema
from rdflib import Graph
from schema_salad.exceptions import ValidationException

from cwltest import REQUIRED, UNSUPPORTED_FEATURE, logger, templock


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


class CompareFail(Exception):
    @classmethod
    def format(cls, expected, actual, cause=None):
        # type: (Any, Any, Any) -> CompareFail
        message = "expected: {}\ngot: {}".format(
            json.dumps(expected, indent=4, sort_keys=True),
            json.dumps(actual, indent=4, sort_keys=True),
        )
        if cause:
            message += "\ncaused by: %s" % cause
        return cls(message)


def compare_location(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    if "path" in expected:
        comp = "path"
        if "path" not in actual:
            actual["path"] = actual["location"]
    elif "location" in expected:
        comp = "location"
    else:
        return
    if actual.get("class") == "Directory":
        actual[comp] = actual[comp].rstrip("/")

    if expected[comp] != "Any" and (
            not (
                    actual[comp].endswith("/" + expected[comp])
                    or ("/" not in actual[comp] and expected[comp] == actual[comp])
            )
    ):
        raise CompareFail.format(
            expected,
            actual,
            f"{actual[comp]} does not end with {expected[comp]}",
        )


def compare_contents(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    expected_contents = expected["contents"]
    with open(actual["path"]) as f:
        actual_contents = f.read()
    if expected_contents != actual_contents:
        raise CompareFail.format(
            expected,
            actual,
            json.dumps(
                "Output file contents do not match: actual '%s' is not equal to expected '%s'"
                % (actual_contents, expected_contents)
            ),
        )


def check_keys(keys, expected, actual):
    # type: (Set[str], Dict[str,Any], Dict[str,Any]) -> None
    for k in keys:
        try:
            compare(expected.get(k), actual.get(k))
        except CompareFail as e:
            raise CompareFail.format(
                expected, actual, f"field '{k}' failed comparison: {str(e)}"
            ) from e


def compare_file(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    compare_location(expected, actual)
    if "contents" in expected:
        compare_contents(expected, actual)
    other_keys = set(expected.keys()) - {"path", "location", "listing", "contents"}
    check_keys(other_keys, expected, actual)


def compare_directory(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    if actual.get("class") != "Directory":
        raise CompareFail.format(
            expected, actual, "expected object with a class 'Directory'"
        )
    if "listing" not in actual:
        raise CompareFail.format(
            expected, actual, "'listing' is mandatory field in Directory object"
        )
    for i in expected["listing"]:
        found = False
        for j in actual["listing"]:
            try:
                compare(i, j)
                found = True
                break
            except CompareFail:
                pass
        if not found:
            raise CompareFail.format(
                expected,
                actual,
                "%s not found" % json.dumps(i, indent=4, sort_keys=True),
            )
    compare_file(expected, actual)


def compare_dict(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    for c in expected:
        try:
            compare(expected[c], actual.get(c))
        except CompareFail as e:
            raise CompareFail.format(
                expected, actual, f"failed comparison for key '{c}': {e}"
            ) from e
    extra_keys = set(actual.keys()).difference(list(expected.keys()))
    for k in extra_keys:
        if actual[k] is not None:
            raise CompareFail.format(expected, actual, "unexpected key '%s'" % k)


def compare(expected, actual):  # type: (Any, Any) -> None
    if expected == "Any":
        return
    if expected is not None and actual is None:
        raise CompareFail.format(expected, actual)

    try:
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                raise CompareFail.format(expected, actual)

            if expected.get("class") == "File":
                compare_file(expected, actual)
            elif expected.get("class") == "Directory":
                compare_directory(expected, actual)
            else:
                compare_dict(expected, actual)

        elif isinstance(expected, list):
            if not isinstance(actual, list):
                raise CompareFail.format(expected, actual)

            if len(expected) != len(actual):
                raise CompareFail.format(expected, actual, "lengths don't match")
            for c in range(0, len(expected)):
                try:
                    compare(expected[c], actual[c])
                except CompareFail as e:
                    raise CompareFail.format(expected, actual, e) from e
        else:
            if expected != actual:
                raise CompareFail.format(expected, actual)

    except Exception as e:
        raise CompareFail(str(e)) from e


def generate_badges(badgedir: str, ntotal: Dict[str, int], npassed: Dict[str, int]) -> None:
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


def get_test_number_by_key(tests, key, value):
    # type: (List[Dict[str, str]], str, str) -> Optional[int]
    for i, test in enumerate(tests):
        if key in test and test[key] == value:
            return i
    return None


def load_and_validate_tests(path: str) -> Tuple[Any, Dict[str, Any]]:
    """Load and validate the given tests against the cwltest schema."""
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
        raise ValidationException

    return schema_salad.schema.load_and_validate(
        document_loader, avsc_names, path, True
    )


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
    Optional[junit_xml.TestSuite]
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
        test_case.url = f"cwltest:{suite_name}#{i + 1}" if suite_name is not None else "cwltest:#{i + 1}"
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
        verbose: Optional[bool] = False,
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
    if not verbose:
        test_command.extend(["--quiet"])
    toolpath, jobpath = prepare_test_paths(test, cwd)
    test_command.extend([os.path.normcase(toolpath)])
    if jobpath:
        test_command.append(os.path.normcase(jobpath))
    return test_command


def prepare_test_paths(
        test: Dict[str, str],
        cwd: str,
) -> Tuple[str, Optional[str]]:
    """Determine the test path and the tool path."""
    cwd = schema_salad.ref_resolver.file_uri(cwd)
    toolpath = test["tool"]
    if toolpath.startswith(cwd):
        toolpath = toolpath[len(cwd) + 1:]

    jobpath = test.get("job")
    if jobpath:
        if jobpath.startswith(cwd):
            jobpath = jobpath[len(cwd) + 1:]
    return toolpath, jobpath


def run_test_plain(
        args: Dict[str, Any],
        test: Dict[str, str],
        timeout: int,
        test_number: Optional[int] = None,
        junit_verbose: Optional[bool] = False,
        verbose: Optional[bool] = False,
) -> TestResult:
    """Plain test runner."""
    out: Dict[str, Any] = {}
    outdir = outstr = outerr = ""
    test_command: List[str] = []
    duration = 0.0
    process: Optional[subprocess.Popen[str]] = None
    try:
        cwd = os.getcwd()
        test_command = prepare_test_command(
            args['tool'], args['args'], args['testargs'], test, cwd, junit_verbose
        )
        if verbose:
            sys.stderr.write(f"Running: {' '.join(test_command)}\n")
        sys.stderr.flush()
        start_time = time.time()
        stderr = subprocess.PIPE if not args['verbose'] else None
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

        logger.debug('outstr: "%s".', outstr)
        out = json.loads(outstr) if outstr else {}
    except subprocess.CalledProcessError as err:
        if err.returncode == UNSUPPORTED_FEATURE and REQUIRED not in test.get(
                "tags", ["required"]
        ):
            return TestResult(
                UNSUPPORTED_FEATURE, outstr, outerr, duration, args["classname"]
            )
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
        logger.error(outerr)
        if test.get("should_fail", False):
            return TestResult(0, outstr, outerr, duration, args["classname"])
        return TestResult(1, outstr, outerr, duration, args["classname"], str(err))
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
        return TestResult(
            2, outstr, outerr, timeout, args["classname"], "Test timed out"
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
        return TestResult(1, outstr, outerr, duration, args["classname"])

    try:
        compare(test.get("output"), out)
    except CompareFail as ex:
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

    return TestResult(
        (1 if fail_message else 0),
        outstr,
        outerr,
        duration,
        args["classname"],
        fail_message,
    )


def shortname(
        name,  # type: str
):  # type: (...) -> str
    """
    Return the short name of a given name.

    It is a workaround of https://github.com/common-workflow-language/schema_salad/issues/511.
    """
    return [n for n in re.split("[/#]", name) if len(n)][-1]
