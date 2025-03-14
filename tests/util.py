"""Test functions."""

import atexit
import os
import subprocess  # nosec
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path
from typing import Optional


def get_data(filename: str) -> str:
    """Return the absolute path starting from a file name."""
    filename = os.path.normpath(filename)
    # normalizing path depending on OS or else it will cause problem when
    # joining path
    filepath = None
    try:
        file_manager = ExitStack()
        atexit.register(file_manager.close)
        traversable = files("cwltest") / filename
        filepath = file_manager.enter_context(as_file(traversable))
    except ModuleNotFoundError:
        pass
    if not filepath or not os.path.isfile(filepath):
        filepath = Path(os.path.dirname(__file__)) / ".." / filename
    return str(filepath.resolve())


def run_with_mock_cwl_runner(
    args: list[str], cwl_runner: Optional[str] = None
) -> tuple[int, str, str]:
    """Bind a mock cwlref-runner implementation to cwltest."""
    if cwl_runner is None:
        cwl_runner = get_data("tests/test-data/mock_cwl_runner.py")
    process = subprocess.Popen(  # nosec
        ["cwltest", "--tool", cwl_runner] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()
