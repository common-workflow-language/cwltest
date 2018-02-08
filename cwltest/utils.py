import json

import junit_xml
from typing import Any, Dict, Set, Text

from six.moves import range


class TestResult(object):

    """Encapsulate relevant test result data."""

    def __init__(self, return_code, standard_output, error_output, duration, classname, message=''):
        # type: (int, Text, Text, float, Text, str) -> None
        self.return_code = return_code
        self.standard_output = standard_output
        self.error_output = error_output
        self.duration = duration
        self.message = message
        self.classname = classname

    def create_test_case(self, test):
        # type: (Dict[Text, Any]) -> junit_xml.TestCase
        doc = test.get(u'doc', 'N/A').strip()
        case = junit_xml.TestCase(
            doc, elapsed_sec=self.duration, classname=self.classname,
            stdout=self.standard_output, stderr=self.error_output,
        )
        if self.return_code > 0:
            case.failure_message = self.message
        return case


class CompareFail(Exception):

    @classmethod
    def format(cls, expected, actual, cause=None):
        # type: (Any, Any, Any) -> CompareFail
        message = u"expected: %s\ngot: %s" % (
            json.dumps(expected, indent=4, sort_keys=True),
            json.dumps(actual, indent=4, sort_keys=True))
        if cause:
            message += u"\ncaused by: %s" % cause
        return cls(message)


def compare_location(expected, actual):
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

    if expected[comp] != "Any" and (not (actual[comp].endswith("/" + expected[comp]) or
                                    ("/" not in actual[comp] and expected[comp] == actual[comp]))):
        raise CompareFail.format(expected, actual, u"%s does not end with %s" % (actual[comp], expected[comp]))


def check_keys(keys, expected, actual):
    # type: (Set[str], Dict[str,Any], Dict[str,Any]) -> None
    for k in keys:
        try:
            compare(expected.get(k), actual.get(k))
        except CompareFail as e:
            raise CompareFail.format(expected, actual, u"field '%s' failed comparison: %s" %(
                k, str(e)
            ))


def compare_file(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    compare_location(expected, actual)
    other_keys = set(expected.keys()) - {'path', 'location', 'listing'}
    check_keys(other_keys, expected, actual)


def compare_directory(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    if actual.get("class") != 'Directory':
        raise CompareFail.format(expected, actual, u"expected object with a class 'Directory'")
    if "listing" not in actual:
        raise CompareFail.format(expected, actual, u"'listing' is mandatory field in Directory object")
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
            raise CompareFail.format(expected, actual, u"%s not found" % json.dumps(i, indent=4, sort_keys=True))
    compare_file(expected, actual)


def compare_dict(expected, actual):
    # type: (Dict[str,Any], Dict[str,Any]) -> None
    for c in expected:
        try:
            compare(expected[c], actual.get(c))
        except CompareFail as e:
            raise CompareFail.format(expected, actual, u"failed comparison for key '%s': %s" % (c, e))
    extra_keys = set(actual.keys()).difference(list(expected.keys()))
    for k in extra_keys:
        if actual[k] is not None:
            raise CompareFail.format(expected, actual, u"unexpected key '%s'" % k)


def compare(expected, actual):  # type: (Any, Any) -> None
    if expected == "Any":
        return
    if expected is not None and actual is None:
        raise CompareFail.format(expected, actual)

    try:
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                raise CompareFail.format(expected, actual)

            if expected.get("class") == "File":
                compare_file(expected, actual)
            elif expected.get("class") == "Directory":
                compare_directory(expected, actual)
            else:
                compare_dict(expected, actual)

        elif isinstance(expected, list):
            if not isinstance(actual, list):
                raise CompareFail.format(expected, actual)

            if len(expected) != len(actual):
                raise CompareFail.format(expected, actual, u"lengths don't match")
            for c in range(0, len(expected)):
                try:
                    compare(expected[c], actual[c])
                except CompareFail as e:
                    raise CompareFail.format(expected, actual, e)
        else:
            if expected != actual:
                raise CompareFail.format(expected, actual)

    except Exception as e:
        raise CompareFail(str(e))
