import json
import os
from pathlib import Path
from textwrap import dedent

import schema_salad.ref_resolver

from .util import get_data, run_with_mock_cwl_runner


def test_badgedir(tmp_path: Path) -> None:
    badgedir = tmp_path / "badgedir"

    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(
            get_data("tests/test-data/conformance_test_v1.2.cwltest.yaml")
        ),
        "--badgedir",
        str(badgedir),
    ]
    cwd = os.getcwd()
    try:
        os.chdir(get_data("tests/test-data/"))
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    finally:
        os.chdir(cwd)

    assert error_code == 1
    required_json = badgedir / "required.json"
    assert required_json.exists()
    with open(required_json) as file:
        obj = json.load(file)
        assert obj.get("subject", "") == "required"
        assert obj.get("status", "") == "0%"
        assert obj.get("color", "") == "red"

    required_md = badgedir / "required.md"
    assert required_md.exists()
    with open(required_md) as file:
        s = file.read()
        assert "file://" in s
        assert "tests/test-data/conformance_test_v1.2.cwltest.yaml" in s
        assert "v1.0/cat-job.json" in s
        assert "v1.0/cat1-testcli.cwl" in s

    clt = badgedir / "command_line_tool.json"
    assert clt.exists()
    with open(clt) as file:
        obj = json.load(file)
        assert obj.get("subject", "") == "command_line_tool"
        assert obj.get("status", "") == "0%"
        assert obj.get("color", "") == "yellow"
    assert (badgedir / "command_line_tool.md").exists()

    all_tests = badgedir / "all.json"
    assert all_tests.exists()
    with open(all_tests) as file:
        obj = json.load(file)
        assert obj.get("subject", "") == "all"
        assert obj.get("status", "") == "0%"
        assert obj.get("color", "") == "yellow"
    assert (badgedir / "all.md").exists()


def test_badgedir_report_with_baseuri(tmp_path: Path) -> None:
    badgedir = tmp_path / "badgedir"

    baseuri = "https://example.com/specified/uri"

    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(get_data("tests/test-data/badgedir.yaml")),
        "--badgedir",
        str(badgedir),
        "--baseuri",
        baseuri,
    ]
    cwd = os.getcwd()
    try:
        os.chdir(get_data("tests/test-data/"))
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    finally:
        os.chdir(cwd)

    clt_md = badgedir / "command_line_tool.md"
    assert clt_md.exists()
    with open(clt_md) as file:
        contents = file.read()
        assert contents == markdown_report_with(baseuri)


def markdown_report_with(baseuri: str) -> str:
    return dedent(
        f"""
        # `command_line_tool` tests
        ## List of passed tests
        - [success_w_job]({baseuri}/badgedir.yaml#L0) ([tool]({baseuri}/return-0.cwl), [job]({baseuri}/empty.yml))
        - [success_wo_job]({baseuri}/badgedir.yaml#L7) ([tool]({baseuri}/return-0.cwl))
        ## List of failed tests
        - [failure_w_job]({baseuri}/badgedir.yaml#L13) ([tool]({baseuri}/return-1.cwl), [job]({baseuri}/empty.yml))
        - [failure_wo_job]({baseuri}/badgedir.yaml#L20) ([tool]({baseuri}/return-1.cwl))
        ## List of unsupported tests
        - [unsupported_w_job]({baseuri}/badgedir.yaml#L26) ([tool]({baseuri}/return-unsupported.cwl), [job]({baseuri}/empty.yml))
        - [unsupported_wo_job]({baseuri}/badgedir.yaml#L33) ([tool]({baseuri}/return-unsupported.cwl))
        """
    )[1:]
