import os
import re
from os import linesep as n
from os import sep as p
from pathlib import Path

import defusedxml.ElementTree as ET
import schema_salad.ref_resolver

from .util import get_data, run_with_mock_cwl_runner


def test_unsupported_with_required_tests() -> None:
    cwl_runner = get_data("tests/test-data/mock_cwl_runner.py")
    cwd = os.getcwd()
    os.chdir(get_data("tests/test-data/"))
    args = ["--test", "required-unsupported.yml"]
    try:
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
        f"The `id` field is missing.{n}"
        f"The `id` field is missing.{n}"
        f"Test [1/2] Required test that is unsupported (without tags){n}"
        f"{n}"
        f"Test 1 failed: {cwl_runner} --quiet return-unsupported.cwl {q}v1.0{p}cat-job.json{q}{n}"
        f"Required test that is unsupported (without tags){n}"
        f"Does not support required feature{n}"
        f"Test [2/2] Required test that is unsupported (with tags){n}"
        f"{n}"
        f"Test 2 failed: {cwl_runner} --quiet return-unsupported.cwl {q}v1.0{p}cat-job.json{q}{n}"
        f"Required test that is unsupported (with tags){n}"
        f"Does not support required feature{n}"
        f"0 tests passed, 2 failures, 0 unsupported features{n}"
    ) == stderr


def test_unsupported_with_optional_tests() -> None:
    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(
            get_data("tests/test-data/optional-unsupported.yml")
        ),
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    stderr = re.sub(r" '?--outdir=[^ ]*", "", stderr)
    assert error_code == 0
    assert (
        "The `id` field is missing.{n}"
        "Test [1/1] Optional test that is unsupported{n}{n}"
        "0 tests passed, 1 unsupported "
        "features{n}".format(n=n)
    ) == stderr


def test_error_with_optional_tests() -> None:
    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(
            get_data("tests/test-data/optional-error.yml")
        ),
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert error_code == 1
    assert "1 failures" in stderr


def test_category_in_junit_xml(tmp_path: Path) -> None:
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
    assert (root := tree.getroot()) is not None
    assert (testsuite_el := root.find("testsuite")) is not None
    assert (testcase_el := testsuite_el.find("testcase")) is not None
    category = testcase_el.attrib["class"]
    assert category == "js, init_work_dir"


def test_list_all_tags() -> None:
    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(
            get_data("tests/test-data/conformance_test_v1.2.cwltest.yaml")
        ),
        "--show-tags",
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert error_code == 0, stderr
    assert stdout == """command_line_tool
expression_tool
inline_javascript
required
"""
