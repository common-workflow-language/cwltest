from typing import Callable
from unittest.mock import MagicMock, patch, sentinel

import pytest

from cwltest.utils import load_optional_fsaccess_plugin


def get_mock_entry_point(set_sentinel: bool = False) -> MagicMock:
    """Returns a mock object whose `load()` method may optionally return
    a sentinel value.
    """
    m: MagicMock = MagicMock()
    if set_sentinel:
        m.load.return_value.return_value = sentinel.custom_fs_access
    return m


def mock_entry_points(n: int = 1) -> Callable[..., MagicMock]:
    """Returns a plain function that emulates
    `importlib.metadata.entry_points`.
    """
    mock_ep_data: tuple[MagicMock, ...] = tuple(
        get_mock_entry_point(i == 0) for i in range(n)
    )
    mock_eps: MagicMock = MagicMock()
    mock_eps.__iter__ = lambda self: iter(mock_ep_data)
    mock_eps.__len__.return_value = n
    mock_eps.__getitem__.side_effect = KeyError

    def entry_points(**kwargs: str) -> MagicMock:
        return mock_eps

    return entry_points


def test_default_fsaccess_fallback() -> None:
    with patch("cwltest.utils.entry_points", mock_entry_points(0)):
        load_optional_fsaccess_plugin()

        from cwltest import compare, stdfsaccess

        assert compare.fs_access
        assert isinstance(compare.fs_access, stdfsaccess.StdFsAccess)


@pytest.mark.parametrize("n", (1, 2))
def test_load_fsaccess(n: int) -> None:
    with patch("cwltest.utils.entry_points", mock_entry_points(n)) as mfcn:
        load_optional_fsaccess_plugin()
        ep = tuple(mfcn())[0]
        ep.load.assert_called_once_with()

        import cwltest.compare

        assert cwltest.compare.fs_access is sentinel.custom_fs_access
