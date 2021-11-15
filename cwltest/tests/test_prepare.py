"""Test prepare_test_command()"""
import os
from cwltest import prepare_test_command


def test_unix_relative_path():
    """Confirm unix style to windows style path corrections."""
    command = prepare_test_command(
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
    )
    if os.name == "nt":
        assert command[3] == "v1.0\\bwa-mem-tool.cwl"
        assert command[4] == "v1.0\\bwa-mem-job.json"
    else:
        assert command[3] == "v1.0/bwa-mem-tool.cwl"
        assert command[4] == "v1.0/bwa-mem-job.json"
