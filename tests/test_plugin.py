import os
import shutil
from typing import TYPE_CHECKING

from .util import get_data

if TYPE_CHECKING:
    from _pytest.pytester import Pytester


def test_plugin(pytester: "Pytester") -> None:
    """Test the pytest plugin."""
    path = pytester.copy_example("conftest.py")
    shutil.copy(get_data("tests/test-data/conformance_test_v1.0.yml"), path.parent)
    inner_dir = os.path.join(path.parent, "v1.0")
    os.mkdir(inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/cat1-testcli.cwl"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/cat-job.json"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/cat-n-job.json"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/hello.txt"), inner_dir)
    shutil.copy(get_data("tests/test-data/v1.0/args.py"), inner_dir)
    result = pytester.runpytest("-k", "conformance_test_v1.0.yml")
    result.assert_outcomes(passed=2)
