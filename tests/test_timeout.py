import os
from pathlib import Path
from typing import cast
from xml.etree.ElementTree import Element

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
        root = tree.getroot()
        timeout_text = cast(
            Element,
            cast(Element, cast(Element, root.find("testsuite")).find("testcase")).find(
                "failure"
            ),
        ).text
        timeout_stderr = cast(
            Element,
            cast(Element, cast(Element, root.find("testsuite")).find("testcase")).find(
                "system-err"
            ),
        ).text
        assert timeout_text is not None and "Test timed out" in timeout_text
        assert timeout_stderr is not None and "timeout stderr" in timeout_stderr
    except AttributeError as e:
        print(junit_xml_report.read_text())
        raise e
