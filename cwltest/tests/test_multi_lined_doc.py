import os
from os import linesep as n
from pathlib import Path

from .util import run_with_mock_cwl_runner, get_data
import defusedxml.ElementTree as ET


def test_run():
    args = ["--test", get_data("tests/test-data/multi-lined-doc.yml")]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert f"Test [1/2] opt-error: Test with label{n}" in stderr
    assert f"Test [2/2] Test without label{n}" in stderr


def test_list():
    args = ["--test", get_data("tests/test-data/multi-lined-doc.yml"), "-l"]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert f"[1] opt-error: Test with label{n}" in stdout
    assert f"[2] Test without label{n}" in stdout
