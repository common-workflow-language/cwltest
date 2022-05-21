import os
from os import linesep as n
from pathlib import Path

from .util import run_with_mock_cwl_runner, get_data
import defusedxml.ElementTree as ET


def test_list_only_exclude():
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


def test_list_include_and_exclude():
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
