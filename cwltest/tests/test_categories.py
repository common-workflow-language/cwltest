import re
import os
from os import linesep as n
from os import sep as p
from pathlib import Path

from .util import run_with_mock_cwl_runner, get_data
import defusedxml.ElementTree as ET
import schema_salad.ref_resolver


def test_unsupported_with_required_tests():
    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(
            get_data("tests/test-data/required-unsupported.yml")
        ),
    ]
    try:
        cwd = os.getcwd()
        os.chdir(get_data("tests/test-data/"))
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    finally:
        os.chdir(cwd)

    assert error_code == 1
    print(stderr)
    stderr = re.sub(r" '?--outdir=[^ ]*", "", stderr)
    if os.name == "nt":
        q = "'"
    else:
        q = ""
    assert (
        "Test [1/2] Required test that is unsupported (without tags){n}"
        "{n}"
        "Test 1 failed: mock-cwl-runner --quiet return-unsupported.cwl {q}v1.0{p}cat-job.json{q}{n}"
        "Required test that is unsupported (without tags){n}"
        "Does not support required feature{n}"
        "{n}"
        "Test [2/2] Required test that is unsupported (with tags){n}"
        "{n}"
        "Test 2 failed: mock-cwl-runner --quiet return-unsupported.cwl {q}v1.0{p}cat-job.json{q}{n}"
        "Required test that is unsupported (with tags){n}"
        "Does not support required feature{n}"
        "{n}"
        "0 tests passed, 2 failures, 0 unsupported features{n}".format(n=n, p=p, q=q)
    ) == stderr


def test_unsupported_with_optional_tests():
    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(
            get_data("tests/test-data/optional-unsupported.yml")
        ),
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert error_code == 0
    assert (
        "Test [1/1] Optional test that is unsupported{n}{n}"
        "0 tests passed, 1 unsupported "
        "features{n}".format(n=n)
    ) == stderr


def test_error_with_optional_tests():
    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(
            get_data("tests/test-data/optional-error.yml")
        ),
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert error_code == 1
    assert "1 failures" in stderr


def test_category_in_junit_xml(tmp_path: Path):
    junit_xml_report = tmp_path / "junit-report.xml"
    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(
            get_data("tests/test-data/optional-error.yml")
        ),
        "--junit-xml",
        str(junit_xml_report),
    ]
    run_with_mock_cwl_runner(args)
    tree = ET.parse(junit_xml_report)
    root = tree.getroot()
    category = root.find("testsuite").find("testcase").attrib["class"]
    assert category == "js, init_work_dir"
