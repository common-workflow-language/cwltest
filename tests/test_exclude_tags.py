from os import linesep as n

from .util import get_data, run_with_mock_cwl_runner


def test_list_only_exclude() -> None:
    args = [
        "--test",
        get_data("tests/test-data/exclude-tags.yml"),
        "-l",
        "--exclude-tags=workflow",
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert f"[1] opt-error1: Test with label{n}" in stdout
    assert "opt-error2" not in stdout
    assert "opt-error3" not in stdout


def test_list_include_and_exclude() -> None:
    args = [
        "--test",
        get_data("tests/test-data/exclude-tags.yml"),
        "-l",
        "--tags=command_line_tool",
        "--exclude-tags=workflow",
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert f"[1] opt-error1: Test with label{n}" in stdout
    assert "opt-error2" not in stdout
    assert "opt-error3" not in stdout
