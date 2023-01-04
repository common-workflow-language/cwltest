from os import linesep as n

from .util import get_data, run_with_mock_cwl_runner


def test_run() -> None:
    args = ["--test", get_data("tests/test-data/multi-lined-doc.yml")]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert "The `label` field is deprecated. Use `id` field instead." in stderr
    assert f"Test [1/2] opt-error: Test with label{n}" in stderr
    assert f"Test [2/2] Test without label{n}" in stderr


def test_list() -> None:
    args = ["--test", get_data("tests/test-data/multi-lined-doc.yml"), "-l"]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert f"[1] opt-error: Test with label{n}" in stdout
    assert f"[2] Test without label{n}" in stdout
