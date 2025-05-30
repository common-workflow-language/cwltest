import os
from pathlib import Path

import defusedxml.ElementTree as ET
import schema_salad.ref_resolver

from .util import get_data, run_with_mock_cwl_runner


def test_timeout_stderr_stdout(tmp_path: Path) -> None:
    junit_xml_report = tmp_path / "junit-report.xml"

    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(get_data("tests/test-data/timeout.yml")),
        "--timeout",
        "5",
        "--junit-xml",
        str(junit_xml_report),
    ]
    cwd = os.getcwd()
    try:
        os.chdir(get_data("tests/test-data/"))
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    finally:
        os.chdir(cwd)

    assert error_code == 1
    assert "Test 1 timed out" in stderr
    tree = ET.parse(junit_xml_report)
    try:
        assert (root := tree.getroot()) is not None
        assert (testsuite_el := root.find("testsuite")) is not None
        assert (testcase_el := testsuite_el.find("testcase")) is not None
        assert (failure_el := testcase_el.find("failure")) is not None
        timeout_text = failure_el.text
        assert timeout_text is not None and "Test timed out" in timeout_text
        assert (system_err_el := testcase_el.find("system-err")) is not None
        timeout_stderr = system_err_el.text
        assert timeout_stderr is not None and "timeout stderr" in timeout_stderr
    except AttributeError as e:
        print(junit_xml_report.read_text())
        raise e
