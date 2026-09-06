import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from cwltest.argparser import arg_parser
from cwltest.main import main

if TYPE_CHECKING:
    from pathlib import Path


def test_arg() -> None:
    """Basic test of the argparse."""
    parser = arg_parser()
    parsed = parser.parse_args(
        ["--test", "test_name", "-n", "52", "--tool", "cwltool", "-j", "4"]
    )
    assert parsed.test == "test_name"
    assert parsed.n == "52"
    assert parsed.tool == "cwltool"
    assert parsed.j == 4


@pytest.mark.parametrize("verbose", [False, True])
def test_invalid_test_file(verbose: bool, tmp_path: "Path") -> None:
    argv = ["cwltest", "--test", str(tmp_path / "invalid_file.abc.txt")]
    if verbose:
        argv.append("--verbose")

    with (
        patch("cwltest.main.logger") as mocked_log,
        patch.object(sys, "argv", argv),
    ):
        assert main() == 1

    mocked_log.error.assert_called_once_with(
        f"Failed validating test file: {str(tmp_path / 'invalid_file.abc.txt')}",
        exc_info=verbose,
    )
