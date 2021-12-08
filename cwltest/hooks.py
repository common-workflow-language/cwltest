"""Hooks for pytest-cwl users."""

from typing import Optional, Dict, Any


def pytest_cwl_execute_test(
    description: str, outdir: str, inputs: Optional[str]
) -> Optional[Dict[str, Any]]:
    """
    Execute CWL test using a Python function instead of a command line runner.

    "description" and "inputs" are both paths.

    Should return the CWL output object using plain Python objects.

    Raises cwtest.UnsupportedCWLFeature if an unsupported feature is encountered.
    """
