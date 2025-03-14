from os import linesep as n

from .util import get_data, run_with_mock_cwl_runner


def test_include_by_number() -> None:
    args = [
        "--test",
        get_data("tests/test-data/exclude-tags.yml"),
        "-n1",
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert f"[1/3] opt-error1: Test with label{n}" in stderr
    assert "opt-error2" not in stderr
    assert "opt-error3" not in stderr
