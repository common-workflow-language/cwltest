import os
from os import linesep as n
from pathlib import Path

from .util import run_with_mock_cwl_runner, get_data
import defusedxml.ElementTree as ET


def test_stderr_output():
    args = ["--test", get_data("tests/test-data/short-names.yml")]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert f"Test [1/1] opt-error: Test with a short name{n}" in stderr


def test_run_by_short_name():
    short_name = "opt-error"
    args = [
        "--test",
        get_data("tests/test-data/with-and-without-short-names.yml"),
        "-s",
        short_name,
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert "Test [2/2] opt-error: Test with a short name" in stderr
    assert "Test [1/2]" not in stderr


def test_list_tests():
    args = [
        "--test",
        get_data("tests/test-data/with-and-without-short-names.yml"),
        "-l",
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert (
        f"[1] Test without a short name{n}" f"[2] opt-error: Test with a short name{n}"
    ) in stdout


def test_short_name_in_junit_xml(tmp_path: Path):
    junit_xml_report = tmp_path / "junit-report.xml"
    args = [
        "--test",
        get_data("tests/test-data/short-names.yml"),
        "--junit-xml",
        str(junit_xml_report),
    ]
    run_with_mock_cwl_runner(args)
    tree = ET.parse(junit_xml_report)
    root = tree.getroot()
    category = root.find("testsuite").find("testcase").attrib["file"]
    assert category == "opt-error"
