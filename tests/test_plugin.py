import os
import shutil
from pathlib import Path

import pytest

from .util import get_data


def _load_v1_0_dir(path: Path) -> None:
    inner_dir = os.path.join(path.parent, "v1.0")
    os.mkdir(inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/cat1-testcli.cwl"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/null-expression2-tool.cwl"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/cat-job.json"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/cat-n-job.json"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/hello.txt"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/args.py"), inner_dir)


def test_include(pytester: pytest.Pytester) -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.cwltest.yml")
    shutil.copy(
        get_data("tests/test-data/cwltool-conftest.py"), path.parent / "conftest.py"
    )
    _load_v1_0_dir(path)
    result = pytester.runpytest(
        "-k",
        "conformance_test_v1.0.cwltest.yml",
        "--cwl-include",
        "cl_optional_inputs_missing",
    )
    result.assert_outcomes(passed=1, skipped=1)


def test_exclude(pytester: pytest.Pytester) -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.cwltest.yml")
    shutil.copy(
        get_data("tests/test-data/cwltool-conftest.py"), path.parent / "conftest.py"
    )
    _load_v1_0_dir(path)
    result = pytester.runpytest(
        "-k",
        "conformance_test_v1.0.cwltest.yml",
        "--cwl-exclude",
        "cl_optional_inputs_missing,cl_optional_bindings_provided",
    )
    result.assert_outcomes(passed=0, skipped=2)


def test_tags(pytester: pytest.Pytester) -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.cwltest.yml")
    shutil.copy(
        get_data("tests/test-data/cwltool-conftest.py"), path.parent / "conftest.py"
    )
    _load_v1_0_dir(path)
    result = pytester.runpytest(
        "-k", "conformance_test_v1.0.cwltest.yml", "--cwl-tags", "required"
    )
    result.assert_outcomes(passed=1, skipped=1)


def test_exclude_tags(pytester: pytest.Pytester) -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.cwltest.yml")
    shutil.copy(
        get_data("tests/test-data/cwltool-conftest.py"), path.parent / "conftest.py"
    )
    _load_v1_0_dir(path)
    result = pytester.runpytest(
        "-k",
        "conformance_test_v1.0.cwltest.yml",
        "--cwl-exclude-tags",
        "command_line_tool",
    )
    result.assert_outcomes(skipped=2)


def test_badgedir(pytester: pytest.Pytester) -> None:
    """Test the pytest plugin creates the badges directory."""
    path = pytester.copy_example("conformance_test_v1.0.cwltest.yml")
    shutil.copy(
        get_data("tests/test-data/cwltool-conftest.py"), path.parent / "conftest.py"
    )
    _load_v1_0_dir(path)
    badge_path = path.parent / "cwl-badges"
    assert not badge_path.exists()
    result = pytester.runpytest_inprocess(
        "-k", "conformance_test_v1.0.cwltest.yml", "--cwl-badgedir", str(badge_path)
    )
    result.assert_outcomes(passed=2)
    assert badge_path.exists()
    assert (badge_path / "command_line_tool.json").exists()
    assert (badge_path / "command_line_tool.md").exists()
    assert (badge_path / "required.json").exists()
    assert (badge_path / "required.md").exists()


def test_badgedir_xdist(pytester: pytest.Pytester) -> None:
    """Test the pytest plugin creates the badges directory even with xdist."""
    path = pytester.copy_example("conformance_test_v1.0.cwltest.yml")
    shutil.copy(
        get_data("tests/test-data/cwltool-conftest.py"), path.parent / "conftest.py"
    )
    _load_v1_0_dir(path)
    badge_path = path.parent / "cwl-badges"
    assert not badge_path.exists()
    result = pytester.runpytest_inprocess(
        "-n",
        "2",
        "-k",
        "conformance_test_v1.0.cwltest.yml",
        "--cwl-badgedir",
        str(badge_path),
    )
    result.assert_outcomes(passed=2)
    assert badge_path.exists()
    assert (badge_path / "command_line_tool.json").exists()
    assert (badge_path / "command_line_tool.md").exists()
    assert (badge_path / "required.json").exists()
    assert (badge_path / "required.md").exists()


def test_no_label(pytester: pytest.Pytester) -> None:
    """Test the pytest plugin correctly extracts test names from the id field when label is missing."""
    path = pytester.copy_example("conformance_test_v1.2.cwltest.yaml")
    shutil.copy(
        get_data("tests/test-data/cwltool-conftest.py"), path.parent / "conftest.py"
    )
    _load_v1_0_dir(path)
    result = pytester.runpytest(
        "-k", "conformance_test_v1.2.cwltest.yaml", "--cwl-tags", "required"
    )
    result.assert_outcomes(passed=2, skipped=1)


def test_cwltool_hook(pytester: pytest.Pytester) -> None:
    """Test the pytest plugin using cwltool as cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.cwltest.yml")
    shutil.copy(
        get_data("tests/test-data/cwltool-conftest.py"), path.parent / "conftest.py"
    )
    _load_v1_0_dir(path)
    result = pytester.runpytest("-k", "conformance_test_v1.0.cwltest.yml")
    result.assert_outcomes(passed=2)


def test_no_hook(pytester: pytest.Pytester) -> None:
    """Test the pytest plugin using the default cwl-runner."""
    path = pytester.copy_example("conformance_test_v1.0.cwltest.yml")
    _load_v1_0_dir(path)
    result = pytester.runpytest("-k", "conformance_test_v1.0.cwltest.yml")
    result.assert_outcomes(passed=2)
