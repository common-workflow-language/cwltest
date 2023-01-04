import os

import defusedxml.ElementTree as ET
import schema_salad.ref_resolver

from .util import get_data, run_with_mock_cwl_runner


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
        root = tree.getroot()
        timeout_text = root.find("testsuite").find("testcase").find("failure").text
        timeout_stderr = root.find("testsuite").find("testcase").find("system-err").text
        assert "Test timed out" in timeout_text
        assert "timeout stderr" in timeout_stderr
    except AttributeError as e:
        print(junit_xml_report.read_text())
        raise e
