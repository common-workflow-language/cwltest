"""Test prepare_test_command()"""

import os
from pathlib import Path

import pytest

from cwltest import utils


@pytest.mark.parametrize("use_outdir", [False, True])
def test_unix_relative_path(
    use_outdir: bool,
    tmp_path: Path,
) -> None:
    """Confirm unix style to windows style path corrections."""
    basedir = tmp_path
    outdir = str(basedir) if use_outdir else None

    command, test_outdir = utils.prepare_test_command(
        tool="cwl-runner",
        args=[],
        testargs=None,
        test={
            "doc": "General test of command line generation",
            "output": {"args": ["echo"]},
            "tool": "v1.0/bwa-mem-tool.cwl",
            "job": "v1.0/bwa-mem-job.json",
            "tags": ["required"],
        },
        cwd=os.getcwd(),
        outdir=outdir,
    )

    if os.name == "nt":
        assert command[3] == r"v1.0\bwa-mem-tool.cwl"
        assert command[4] == r"v1.0\bwa-mem-job.json"
    else:
        assert command[3] == "v1.0/bwa-mem-tool.cwl"
        assert command[4] == "v1.0/bwa-mem-job.json"

    assert test_outdir is not None
    assert Path(test_outdir).is_dir()

    if use_outdir:
        assert Path(test_outdir).parent == basedir
    else:
        assert Path(test_outdir).parent != basedir
