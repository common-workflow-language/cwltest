import os
from os import linesep as n
from pathlib import Path

from .util import run_with_mock_cwl_runner, get_data
import defusedxml.ElementTree as ET


def test_list():
    args = ["--test", get_data("tests/test-data/string-id.yml"), "-l"]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert f"[1] test-string-id: Test with a string label{n}" in stdout
