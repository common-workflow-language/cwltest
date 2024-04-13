from pathlib import Path

import schema_salad.ref_resolver

from .util import get_data, run_with_mock_cwl_runner


def test_invalid_outputs(tmp_path: Path) -> None:
    args = [
        "--test",
        schema_salad.ref_resolver.file_uri(get_data("tests/test-data/nothing.yml")),
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(
        args, get_data("tests/test-data/dummy-executor.sh")
    )
    assert error_code == 1
    assert "0 tests passed, 2 failures, 0 unsupported features" in stderr
