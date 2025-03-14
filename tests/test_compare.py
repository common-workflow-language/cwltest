import os
from pathlib import Path
from typing import Any

import pytest

from cwltest.compare import CompareFail, _compare_directory, _compare_file, compare

from .util import get_data


def test_compare_any_success() -> None:
    expected = "Any"
    actual: dict[str, Any] = {}
    compare(expected, actual)


def test_compare_contents_failure() -> None:
    expected = {
        "location": "cores.txt",
        "size": 2,
        "class": "File",
        "contents": "2",
    }
    actual = {
        "basename": "cores.txt",
        "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
        "class": "File",
        "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
        "path": get_data("tests/test-data/cores.txt"),
        "size": 2,
    }
    with pytest.raises(CompareFail):
        compare(expected, actual)


def test_compare_contents_success() -> None:
    expected = {
        "location": "cores.txt",
        "size": 2,
        "class": "File",
        "contents": "2\n",
        "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
    }
    actual = {
        "basename": "cores.txt",
        "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
        "class": "File",
        "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
        "path": get_data("tests/test-data/cores.txt"),
        "size": 2,
    }
    compare(expected, actual)


def test_compare_contents_not_exist() -> None:
    expected = {
        "location": "cores.txt",
        "class": "File",
    }
    actual = {
        "basename": "cores.txt",
        "class": "File",
        "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
        "path": "/none/exist/path/to/cores.txt",
        "size": 2,
    }
    with pytest.raises(CompareFail):
        _compare_file(expected, actual, False)


def test_compare_file_different_size(tmp_path: Path) -> None:
    expected = {
        "location": "cores.txt",
        "size": 2,
        "class": "File",
    }

    path = tmp_path / "cores.txt"
    with open(path, "w") as f:
        f.write("hello")

    actual = {
        "basename": "cores.txt",
        "class": "File",
        "location": path.as_uri(),
    }
    with pytest.raises(CompareFail):
        _compare_file(expected, actual, False)


def test_compare_file_different_checksum(tmp_path: Path) -> None:
    expected = {
        "location": "cores.txt",
        "class": "File",
        "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
    }

    path = tmp_path / "cores.txt"
    with open(path, "w") as f:
        f.write("hello")

    actual = {
        "basename": "cores.txt",
        "class": "File",
        "location": path.as_uri(),
    }
    with pytest.raises(CompareFail):
        _compare_file(expected, actual, False)


def test_compare_file_inconsistent_size(tmp_path: Path) -> None:
    expected = {
        "location": "cores.txt",
        "class": "File",
    }

    path = tmp_path / "cores.txt"
    with open(path, "w") as f:
        f.write("hello")

    actual = {
        "basename": "cores.txt",
        "class": "File",
        "location": path.as_uri(),
        "size": 65535,
    }
    with pytest.raises(CompareFail):
        _compare_file(expected, actual, False)


def test_compare_file_inconsistent_checksum(tmp_path: Path) -> None:
    expected = {
        "location": "cores.txt",
        "class": "File",
    }

    path = tmp_path / "cores.txt"
    with open(path, "w") as f:
        f.write("hello")

    actual = {
        "basename": "cores.txt",
        "checksum": "inconsistent-checksum",
        "class": "File",
        "location": path.as_uri(),
    }
    with pytest.raises(CompareFail):
        _compare_file(expected, actual, False)


def test_compare_directory(tmp_path: Path) -> None:
    expected = {
        "location": "dir",
        "class": "Directory",
        "listing": [],
    }

    path = tmp_path / "dir"
    os.makedirs(path)

    actual = {
        "class": "Directory",
        "location": path.as_uri(),
        "listing": [],
    }
    _compare_directory(expected, actual, False)


def test_compare_directory_path(tmp_path: Path) -> None:
    expected = {
        "location": "dir",
        "class": "Directory",
        "listing": [],
    }

    path = tmp_path / "dir"
    os.makedirs(path)

    actual = {
        "class": "Directory",
        "path": str(path),
        "listing": [],
    }
    _compare_directory(expected, actual, False)


def test_compare_directory_success() -> None:
    expected = {
        "stuff": {
            "class": "Directory",
            "listing": [
                {
                    "basename": "baz.txt",
                    "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                    "class": "File",
                    "size": 0,
                },
                {
                    "basename": "foo",
                    "class": "Directory",
                    "listing": [
                        {
                            "basename": "bar.txt",
                            "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                            "class": "File",
                            "size": 0,
                        }
                    ],
                },
            ],
        }
    }
    actual = {
        "stuff": {
            "class": "Directory",
            "listing": [
                {
                    "basename": "baz.txt",
                    "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                    "class": "File",
                    "size": 0,
                },
                {
                    "basename": "foo",
                    "class": "Directory",
                    "listing": [
                        {
                            "basename": "bar.txt",
                            "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                            "class": "File",
                            "size": 0,
                        }
                    ],
                },
            ],
        }
    }
    compare(expected, actual, skip_details=True)


def test_compare_directory_failure_different_listing() -> None:
    expected = {
        "stuff": {
            "class": "Directory",
            "listing": [
                {
                    "basename": "baz.txt",
                    "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                    "class": "File",
                    "size": 0,
                },
                {
                    "basename": "foo",
                    "class": "Directory",
                    "listing": [
                        {
                            "basename": "bar.txt",
                            "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                            "class": "File",
                            "size": 0,
                        }
                    ],
                },
            ],
        }
    }
    actual = {
        "stuff": {
            "class": "Directory",
            "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff",
            "path": "/var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff",
            "listing": [
                {
                    "basename": "baz.txt",
                    "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                    "class": "File",
                    "location": "file:///var/folders/8x/"
                    "2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/baz.txt",
                    "path": "/var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/baz.txt",
                    "size": 0,
                },
                {
                    "basename": "foo",
                    "class": "Directory",
                    "location": "file:///var/folders/8x/"
                    "2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/foo",
                    "path": "/var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/foo",
                    "listing": [
                        {
                            "basename": "bar.txt",
                            "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80775",
                            "class": "File",
                            "location": "file:///var/folders/8x/"
                            "2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/foo/bar.txt",
                            "path": "/var/folders/8x/"
                            "2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/foo/bar.txt",
                            "size": 0,
                        }
                    ],
                },
            ],
        }
    }
    with pytest.raises(CompareFail):
        compare(expected, actual)


def test_compare_directory_failure_no_listing() -> None:
    expected = {
        "stuff": {
            "class": "Directory",
            "listing": [
                {
                    "basename": "baz.txt",
                    "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                    "class": "File",
                    "size": 0,
                },
                {
                    "basename": "foo",
                    "class": "Directory",
                    "listing": [
                        {
                            "basename": "bar.txt",
                            "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                            "class": "File",
                            "size": 0,
                        }
                    ],
                },
            ],
        }
    }
    actual = {
        "stuff": {
            "class": "Directory",
            "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff",
            "path": "/var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff",
            "listing": [
                {
                    "basename": "baz.txt",
                    "checksum": "sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709",
                    "class": "File",
                    "location": "file:///var/folders/8x/"
                    "2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/baz.txt",
                    "path": "/var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/baz.txt",
                    "size": 0,
                },
                {
                    "basename": "foo",
                    "class": "Directory",
                    "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/foo",
                    "path": "/var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/stuff/foo",
                },
            ],
        }
    }
    with pytest.raises(CompareFail):
        compare(expected, actual)


def test_compare_file_failure_different() -> None:
    expected = {
        "location": "cores.txt",
        "size": 2,
        "class": "File",
        "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7b",
    }
    actual = {
        "basename": "cores.txt",
        "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
        "class": "File",
        "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
        "path": "/var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
        "size": 2,
    }
    with pytest.raises(CompareFail):
        compare(expected, actual)


def test_compare_file_failure_none() -> None:
    expected = {
        "location": "cores.txt",
        "size": 2,
        "class": "File",
        "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7b",
    }
    actual: dict[str, Any] = {}
    with pytest.raises(CompareFail):
        compare(expected, actual)


def test_compare_file_success() -> None:
    expected = {
        "location": "cores.txt",
        "size": 2,
        "class": "File",
        "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
    }
    actual = {
        "basename": "cores.txt",
        "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
        "class": "File",
        "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
        "path": "/var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
        "size": 2,
    }
    compare(expected, actual, skip_details=True)


def test_compare_list_failure_missing() -> None:
    expected = {
        "args": [
            "tmap",
            "mapall",
            "stage1",
            "map1",
            "--min-seq-length",
            "20",
            "map2",
            "--min-seq-length",
            "20",
            "stage2",
            "map1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
            "--seed-length",
            "16",
            "map2",
            "--max-seed-hits",
            "-1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
        ]
    }
    actual = {
        "args": [
            "tmap",
            "mapall",
            "stage1",
            "map1",
            "stage2",
            "map1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
            "--seed-length",
            "16",
            "map2",
            "--max-seed-hits",
            "-1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
        ]
    }
    with pytest.raises(CompareFail):
        compare(expected, actual)


def test_compare_list_failure_order() -> None:
    expected = {
        "args": [
            "tmap",
            "mapall",
            "stage1",
            "map1",
            "--min-seq-length",
            "20",
            "map2",
            "--min-seq-length",
            "20",
            "stage2",
            "map1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
            "--seed-length",
            "16",
            "map2",
            "--max-seed-hits",
            "-1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
        ]
    }
    actual = {
        "args": [
            "tmap",
            "mapall",
            "stage1",
            "map1",
            "--min-seq-length",
            "20",
            "map2",
            "--min-seq-length",
            "20",
            "stage2",
            "map2",
            "--max-seed-hits",
            "-1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
            "map1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
            "--seed-length",
            "16",
        ]
    }
    with pytest.raises(CompareFail):
        compare(expected, actual)


def test_compare_list_failure_type() -> None:
    expected = {
        "args": [
            "tmap",
            "mapall",
            "stage1",
            "map1",
            "--min-seq-length",
            "20",
            "map2",
            "--min-seq-length",
            "20",
            "stage2",
            "map1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
            "--seed-length",
            "16",
            "map2",
            "--max-seed-hits",
            "-1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
        ]
    }
    actual: dict[str, Any] = {"args": {}}
    with pytest.raises(CompareFail):
        compare(expected, actual)


def test_compare_list_success() -> None:
    expected = {
        "args": [
            "tmap",
            "mapall",
            "stage1",
            "map1",
            "--min-seq-length",
            "20",
            "map2",
            "--min-seq-length",
            "20",
            "stage2",
            "map1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
            "--seed-length",
            "16",
            "map2",
            "--max-seed-hits",
            "-1",
            "--max-seq-length",
            "20",
            "--min-seq-length",
            "10",
        ]
    }
    compare(expected, expected)
