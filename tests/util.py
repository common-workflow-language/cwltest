import os
import subprocess  # nosec
from typing import List, Tuple

from pkg_resources import Requirement, ResolutionError, resource_filename


def get_data(filename: str) -> str:
    """Return the absolute path starting from a file name."""
    filename = os.path.normpath(filename)
    # normalizing path depending on OS or else it will cause problem when
    # joining path
    filepath = None
    try:
        filepath = resource_filename(Requirement.parse("cwltest"), filename)
    except ResolutionError:
        pass
    if not filepath or not os.path.isfile(filepath):
        filepath = os.path.join(os.path.dirname(__file__), os.pardir, filename)
    return filepath


def run_with_mock_cwl_runner(args: List[str]) -> Tuple[int, str, str]:
    """Bind a mock cwlref-runner implementation to cwltest."""
    cwl_runner = get_data("tests/test-data/mock_cwl_runner.py")
    process = subprocess.Popen(  # nosec
        ["cwltest", "--tool", cwl_runner] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()
