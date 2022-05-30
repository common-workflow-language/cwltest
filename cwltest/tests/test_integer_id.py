import os
from os import linesep as n
from pathlib import Path

from .util import run_with_mock_cwl_runner, get_data
import defusedxml.ElementTree as ET


def test_warning_with_integer_id():
    args = [
        "--test",
        get_data("tests/test-data/integer-id.yml"),
        "-l",
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert (
        "The `id` field with integer is deprecated. Use string identifier instead."
        in stderr
    )
