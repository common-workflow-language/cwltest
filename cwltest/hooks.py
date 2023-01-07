"""Hooks for pytest-cwl users."""

from typing import Any, Dict, Optional, Tuple

from cwltest import utils


def pytest_cwl_execute_test(  # type: ignore[empty-body]
    config: utils.CWLTestConfig, processfile: str, jobfile: Optional[str]
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """
    Execute CWL test using a Python function instead of a command line runner.

    The return value is a tuple.
     - status code
        - 0 = success
        - :py:attr:`cwltest.UNSUPPORTED_FEATURE` for an unsupported feature
        - and any other number for failure
     - CWL output object using plain Python objects.

    :param processfile: a path to a CWL document
    :param jobfile: an optionl path to JSON/YAML input object
    """
