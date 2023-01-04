"""
Example configuration for pytest-cwl plugin using cwltool directly.

Calls cwltool via Python, instead of a subprocess via `--cwl-runner cwltool`.
"""
import json
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple


class UnsupportedCWLFeature(Exception):
    """Exception to be used by pytest_cwl_execute_test implementors."""


def pytest_cwl_execute_test(
    description: str, outdir: str, inputs: str
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """Use the CWL reference runner (cwltool) to execute tests."""
    from cwltool import main
    from cwltool.errors import WorkflowException

    stdout = StringIO()
    argsl: List[str] = ["--debug", f"--outdir={outdir}", description]
    if inputs:
        argsl.append(inputs)
    try:
        result = main.main(argsl=argsl, stdout=stdout)
    except WorkflowException:
        return 1, {}
    out = stdout.getvalue()
    return result, json.loads(out) if out else {}
