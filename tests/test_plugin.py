import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from .util import get_data

if TYPE_CHECKING:
    from _pytest.pytester import Pytester


def _load_v1_0_dir(path: Path) -> None:
    inner_dir = os.path.join(path.parent, "v1.0")
    os.mkdir(inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/cat1-testcli.cwl"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/cat-job.json"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/cat-n-job.json"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/hello.txt"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/args.py"), inner_dir)


def test_include(pytester: "Pytester") -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.yml")
    shutil.copy(get_data("tests/test-data/conftest.py"), path.parent)
    _load_v1_0_dir(path)
    result = pytester.runpytest(
        "-k", "conformance_test_v1.0.yml", "--cwl-include", "cl_optional_inputs_missing"
    )
    result.assert_outcomes(passed=1, skipped=1)


def test_exclude(pytester: "Pytester") -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.yml")
    shutil.copy(get_data("tests/test-data/conftest.py"), path.parent)
    _load_v1_0_dir(path)
    result = pytester.runpytest(
        "-k",
        "conformance_test_v1.0.yml",
        "--cwl-exclude",
        "cl_optional_inputs_missing,cl_optional_bindings_provided",
    )
    result.assert_outcomes(passed=0, skipped=2)


def test_tags(pytester: "Pytester") -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.yml")
    shutil.copy(get_data("tests/test-data/conftest.py"), path.parent)
    _load_v1_0_dir(path)
    result = pytester.runpytest(
        "-k", "conformance_test_v1.0.yml", "--cwl-tags", "required"
    )
    result.assert_outcomes(passed=1, skipped=1)


def test_exclude_tags(pytester: "Pytester") -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.yml")
    shutil.copy(get_data("tests/test-data/conftest.py"), path.parent)
    _load_v1_0_dir(path)
    result = pytester.runpytest(
        "-k", "conformance_test_v1.0.yml", "--cwl-exclude-tags", "command_line_tool"
    )
    result.assert_outcomes(skipped=2)


def test_cwltool_hook(pytester: "Pytester") -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.yml")
    shutil.copy(get_data("tests/test-data/conftest.py"), path.parent)
    _load_v1_0_dir(path)
    result = pytester.runpytest("-k", "conformance_test_v1.0.yml")
    result.assert_outcomes(passed=2)


def test_no_hook(pytester: "Pytester") -> None:
    """Test the pytest plugin using the default cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.yml")
    _load_v1_0_dir(path)
    result = pytester.runpytest("-k", "conformance_test_v1.0.yml")
    result.assert_outcomes(passed=2)
