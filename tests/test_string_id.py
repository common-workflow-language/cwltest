from os import linesep as n

from .util import get_data, run_with_mock_cwl_runner


def test_list() -> None:
    args = ["--test", get_data("tests/test-data/string-id.yml"), "-l"]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert f"[1] test-string-id: Test with a string label{n}" in stdout
