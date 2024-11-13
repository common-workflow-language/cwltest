"""Compare utilities for CWL objects."""

import hashlib
import json
import os.path
import urllib.parse
from typing import Any, Callable, Dict, Optional, Set

arvados_exist_fun = None
arvados_open_fun = None
arvados_size_fun = None

class CompareFail(Exception):
    """Compared CWL objects are not equal."""

    @classmethod
    def format(
        cls, expected: Any, actual: Any, cause: Optional[Any] = None
    ) -> "CompareFail":
        """Load the difference details into the error message."""
        message = "expected: {}\ngot: {}".format(
            json.dumps(expected, indent=4, sort_keys=True),
            json.dumps(actual, indent=4, sort_keys=True),
        )
        if cause:
            message += "\ncaused by: %s" % cause
        return cls(message)


def _check_keys(
    keys: Set[str], expected: Dict[str, Any], actual: Dict[str, Any], skip_details: bool
) -> None:
    for k in keys:
        try:
            compare(expected.get(k), actual.get(k), skip_details)
        except CompareFail as e:
            raise CompareFail.format(
                expected, actual, f"field {k!r} failed comparison: {str(e)}"
            ) from e


def _compare_contents(expected: Dict[str, Any], actual: Dict[str, Any]) -> None:
    with open(actual["path"]) as f:
        actual_contents = f.read()
    if (expected_contents := expected["contents"]) != actual_contents:
        raise CompareFail.format(
            expected,
            actual,
            json.dumps(
                "Output file contents do not match: actual '%s' is not equal to expected '%s'"
                % (actual_contents, expected_contents)
            ),
        )


def _compare_dict(
    expected: Dict[str, Any], actual: Dict[str, Any], skip_details: bool
) -> None:
    for c in expected:
        try:
            compare(expected[c], actual.get(c), skip_details)
        except CompareFail as e:
            import traceback
            traceback.print_exc()
            raise CompareFail.format(
                expected, actual, f"failed comparison for key {c!r}: {e}"
            ) from e
    extra_keys = set(actual.keys()).difference(list(expected.keys()))
    for k in extra_keys:
        if actual[k] is not None:
            raise CompareFail.format(expected, actual, "unexpected key '%s'" % k)


def _compare_directory(
    expected: Dict[str, Any], actual: Dict[str, Any], skip_details: bool
) -> None:
    if actual.get("class") != "Directory":
        raise CompareFail.format(
            expected, actual, "expected object with a class 'Directory'"
        )
    if "listing" not in actual:
        raise CompareFail.format(
            expected, actual, "'listing' is mandatory field in Directory object"
        )
    for i in expected["listing"]:
        found = False
        for j in actual["listing"]:
            try:
                compare(i, j, skip_details)
                found = True
                break
            except CompareFail:
                pass
        if not found:
            raise CompareFail.format(
                expected,
                actual,
                "%s not found" % json.dumps(i, indent=4, sort_keys=True),
            )
    _compare_file(expected, actual, skip_details)


def _compare_file(
    expected: Dict[str, Any], actual: Dict[str, Any], skip_details: bool
) -> None:
    _compare_location(expected, actual, skip_details)
    if "contents" in expected:
        _compare_contents(expected, actual)
    if actual.get("class") == "File" and not skip_details:
        _compare_checksum(expected, actual)
        _compare_size(expected, actual)
    other_keys = set(expected.keys()) - {
        "path",
        "location",
        "listing",
        "contents",
        "checksum",
        "size",
    }
    _check_keys(other_keys, expected, actual, skip_details)


def _compare_location(
    expected: Dict[str, Any], actual: Dict[str, Any], skip_details: bool
) -> None:
    if "path" in expected:
        expected_comp = "path"
        if "path" not in actual:
            actual["path"] = actual["location"]
    elif "location" in expected:
        expected_comp = "location"
    else:
        return
    if "path" in actual:
        actual_comp = "path"
    else:
        actual_comp = "location"

    path = urllib.parse.urlparse(actual[actual_comp]).path
    if actual.get("class") == "Directory":
        actual[actual_comp] = actual[actual_comp].rstrip("/")
        exist_fun: Callable[[str], bool] = os.path.isdir
    else:
        exist_fun = os.path.isfile

    if actual[actual_comp].startswith("keep:") and arvados_exist_fun is not None:
        exist_fun = arvados_exist_fun

    if not exist_fun(path) and not skip_details:
        raise CompareFail.format(
            expected,
            actual,
            f"{actual[actual_comp]} does not exist",
        )
    if expected[expected_comp] != "Any" and (
        not (
            actual[actual_comp].endswith("/" + expected[expected_comp])
            or (
                "/" not in actual[actual_comp]
                and expected[expected_comp] == actual[actual_comp]
            )
        )
    ):
        raise CompareFail.format(
            expected,
            actual,
            f"{actual[actual_comp]} does not end with {expected[expected_comp]}",
        )


def _compare_checksum(expected: Dict[str, Any], actual: Dict[str, Any]) -> None:
    if "path" in actual:
        path = urllib.parse.urlparse(actual["path"]).path
    else:
        path = urllib.parse.urlparse(actual["location"]).path
    checksum = hashlib.sha1()  # nosec

    if arvados_open_fun is not None:
        f = arvados_open_fun(path, "rb")
    else:
        f = open(path, "rb")

    print("got", f)
    contents = f.read(1024 * 1024)
    while contents != b"":
        checksum.update(contents)
        contents = f.read(1024 * 1024)
    f.close()

    actual_checksum_on_disk = f"sha1${checksum.hexdigest()}"
    if "checksum" in actual:
        actual_checksum_declared = actual["checksum"]
        if actual_checksum_on_disk != actual_checksum_declared:
            raise CompareFail.format(
                expected,
                actual,
                "Output file checksums do not match: actual "
                f"{actual_checksum_on_disk!r} on disk is not equal to actual "
                f"{actual_checksum_declared!r} in the output object",
            )
    if "checksum" in expected:
        expected_checksum = expected["checksum"]
        if expected_checksum != actual_checksum_on_disk:
            raise CompareFail.format(
                expected,
                actual,
                "Output file checksums do not match: actual "
                f"{actual_checksum_on_disk!r} is not equal to expected {expected_checksum!r}",
            )


def _compare_size(expected: Dict[str, Any], actual: Dict[str, Any]) -> None:
    if "path" in actual:
        path = urllib.parse.urlparse(actual["path"]).path
    else:
        path = urllib.parse.urlparse(actual["location"]).path

    if arvados_size_fun is not None:
        actual_size_on_disk = arvados_size_fun(path)
    else:
        actual_size_on_disk = os.path.getsize(path)

    if "size" in actual:
        actual_size_declared = actual["size"]
        if actual_size_on_disk != actual_size_declared:
            raise CompareFail.format(
                expected,
                actual,
                "Output file sizes do not match: actual "
                f"{actual_size_on_disk!r} on disk is not equal to actual "
                f"{actual_size_declared!r}' in the output object",
            )
    if "size" in expected:
        expected_size = expected["size"]
        if expected_size != actual_size_on_disk:
            raise CompareFail.format(
                expected,
                actual,
                "Output file sizes do not match: actual "
                f"{actual_size_on_disk!r} is not equal to expected {expected_size!r}",
            )


def compare(expected: Any, actual: Any, skip_details: bool = False) -> None:
    """Compare two CWL objects."""
    if expected == "Any":
        return
    if expected is not None and actual is None:
        raise CompareFail.format(expected, actual)

    try:
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                raise CompareFail.format(expected, actual)

            if expected.get("class") == "File":
                _compare_file(expected, actual, skip_details)
            elif expected.get("class") == "Directory":
                _compare_directory(expected, actual, skip_details)
            else:
                _compare_dict(expected, actual, skip_details)

        elif isinstance(expected, list):
            if not isinstance(actual, list):
                raise CompareFail.format(expected, actual)

            if len(expected) != len(actual):
                raise CompareFail.format(expected, actual, "lengths don't match")
            for c in range(0, len(expected)):
                try:
                    compare(expected[c], actual[c], skip_details)
                except CompareFail as e:
                    raise CompareFail.format(expected, actual, e) from e
        else:
            if expected != actual:
                raise CompareFail.format(expected, actual)

    except Exception as e:
        raise CompareFail(str(e)) from e
