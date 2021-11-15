import os

import subprocess  # nosec

from pkg_resources import (
    Requirement,
    ResolutionError,  # type: ignore
    resource_filename,
)


def get_data(filename):
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


def run_with_mock_cwl_runner(args):
    process = subprocess.Popen(  # nosec
        ["cwltest", "--tool", "mock-cwl-runner"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()
