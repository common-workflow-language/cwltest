"""Compare utilities for CWL objects."""

import json
from typing import Any, Dict, Set


class CompareFail(Exception):
    """Compared CWL objects are not equal."""

    @classmethod
    def format(cls, expected, actual, cause=None):
        # type: (Any, Any, Any) -> CompareFail
        """Load the difference details into the error message."""
        message = "expected: {}\ngot: {}".format(
            json.dumps(expected, indent=4, sort_keys=True),
            json.dumps(actual, indent=4, sort_keys=True),
        )
        if cause:
            message += "\ncaused by: %s" % cause
        return cls(message)


def _check_keys(keys, expected, actual):
    # type: (Set[str], Dict[str,Any], Dict[str,Any]) -> None
    for k in keys:
        try:
            compare(expected.get(k), actual.get(k))
        except CompareFail as e:
            raise CompareFail.format(
                expected, actual, f"field '{k}' failed comparison: {str(e)}"
            ) from e


def _compare_contents(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    expected_contents = expected["contents"]
    with open(actual["path"]) as f:
        actual_contents = f.read()
    if expected_contents != actual_contents:
        raise CompareFail.format(
            expected,
            actual,
            json.dumps(
                "Output file contents do not match: actual '%s' is not equal to expected '%s'"
                % (actual_contents, expected_contents)
            ),
        )


def _compare_dict(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    for c in expected:
        try:
            compare(expected[c], actual.get(c))
        except CompareFail as e:
            raise CompareFail.format(
                expected, actual, f"failed comparison for key '{c}': {e}"
            ) from e
    extra_keys = set(actual.keys()).difference(list(expected.keys()))
    for k in extra_keys:
        if actual[k] is not None:
            raise CompareFail.format(expected, actual, "unexpected key '%s'" % k)


def _compare_directory(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
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
                compare(i, j)
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
    _compare_file(expected, actual)


def _compare_file(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    _compare_location(expected, actual)
    if "contents" in expected:
        _compare_contents(expected, actual)
    other_keys = set(expected.keys()) - {"path", "location", "listing", "contents"}
    _check_keys(other_keys, expected, actual)
    _check_keys(other_keys, expected, actual)


def _compare_location(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    if "path" in expected:
        comp = "path"
        if "path" not in actual:
            actual["path"] = actual["location"]
    elif "location" in expected:
        comp = "location"
    else:
        return
    if actual.get("class") == "Directory":
        actual[comp] = actual[comp].rstrip("/")

    if expected[comp] != "Any" and (
        not (
            actual[comp].endswith("/" + expected[comp])
            or ("/" not in actual[comp] and expected[comp] == actual[comp])
        )
    ):
        raise CompareFail.format(
            expected,
            actual,
            f"{actual[comp]} does not end with {expected[comp]}",
        )


def compare(expected, actual):  # type: (Any, Any) -> None
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
                _compare_file(expected, actual)
            elif expected.get("class") == "Directory":
                _compare_directory(expected, actual)
            else:
                _compare_dict(expected, actual)

        elif isinstance(expected, list):
            if not isinstance(actual, list):
                raise CompareFail.format(expected, actual)

            if len(expected) != len(actual):
                raise CompareFail.format(expected, actual, "lengths don't match")
            for c in range(0, len(expected)):
                try:
                    compare(expected[c], actual[c])
                except CompareFail as e:
                    raise CompareFail.format(expected, actual, e) from e
        else:
            if expected != actual:
                raise CompareFail.format(expected, actual)

    except Exception as e:
        raise CompareFail(str(e)) from e
