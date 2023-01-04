"""Hooks for pytest-cwl users."""

from typing import Optional, Dict, Any, Tuple


def pytest_cwl_execute_test(
    description: str, outdir: str, inputs: Optional[str]
) -> None:
    """
    Execute CWL test using a Python function instead of a command line runner.

    "description" and "inputs" are both paths.

    Returns a tuple:
    - status code (0=success, cwltest.UNSUPPORTED_FEATURE, for an unsupported feature,
                   and any other number for failure)
    - CWL output object using plain Python objects.
    """
