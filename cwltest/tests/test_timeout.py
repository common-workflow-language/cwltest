import re
import os
from os import linesep as n
from os import sep as p
from pathlib import Path

import defusedxml.ElementTree as ET

from .util import run_with_mock_cwl_runner, get_data
import schema_salad.ref_resolver


def test_timeout_stderr_stdout(tmp_path):
    junit_xml_report = tmp_path / "junit-report.xml"

    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(get_data("tests/test-data/timeout.yml")),
        "--timeout",
        "5",
        "--junit-xml",
        str(junit_xml_report),
    ]
    try:
        cwd = os.getcwd()
        os.chdir(get_data("tests/test-data/"))
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    finally:
        os.chdir(cwd)

    assert error_code == 1
    assert "Test 1 timed out" in stderr
    tree = ET.parse(junit_xml_report)
    try:
        root = tree.getroot()
        timeout_text = root.find("testsuite").find("testcase").find("failure").text
        timeout_stderr = root.find("testsuite").find("testcase").find("system-err").text
        assert "Test timed out" in timeout_text
        assert "timeout stderr" in timeout_stderr
    except AttributeError as e:
        print(junit_xml_report.read_text())
        raise e
