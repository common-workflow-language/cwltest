"""
Example configuration for pytest-cwl plugin using cwltool directly.

Calls cwltool via Python, instead of a subprocess via `--cwl-runner cwltool`.
"""
import json
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from cwltest import utils


def pytest_cwl_execute_test(
        config: utils.CWLTestConfig,
        processfile: str,
        jobfile: Optional[str]
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """Use the CWL reference runner (cwltool) to execute tests."""
    from cwltool import main
    from cwltool.errors import WorkflowException

    stdout = StringIO()
    argsl: List[str] = ["--debug", f"--outdir={config.outdir}", processfile]
    if jobfile:
        argsl.append(jobfile)
    try:
        result = main.main(argsl=argsl, stdout=stdout)
    except WorkflowException:
        return 1, {}
    out = stdout.getvalue()
    return result, json.loads(out) if out else {}
