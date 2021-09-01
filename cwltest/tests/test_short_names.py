import unittest

import os
from os import linesep as n

from .util import run_with_mock_cwl_runner, get_data
import defusedxml.ElementTree as ET


class TestShortNames(unittest.TestCase):
    def test_stderr_output(self):
        args = ["--test", get_data("tests/test-data/short-names.yml")]
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
        self.assertIn(
            "Test [1/1] opt-error: Test with a short name{n}".format(n=n), stderr
        )

    def test_run_by_short_name(self):
        short_name = "opt-error"
        args = [
            "--test",
            get_data("tests/test-data/with-and-without-short-names.yml"),
            "-s",
            short_name,
        ]
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
        self.assertIn("Test [2/2] opt-error: Test with a short name", stderr)
        self.assertNotIn("Test [1/2]", stderr)

    def test_list_tests(self):
        args = [
            "--test",
            get_data("tests/test-data/with-and-without-short-names.yml"),
            "-l",
        ]
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
        self.assertEqual(
            "[1] Test without a short name{n}"
            "[2] opt-error: Test with a short name{n}".format(n=n),
            stdout,
        )

    def test_short_name_in_junit_xml(self):
        junit_xml_report = get_data("tests/test-data/junit-report.xml")
        args = [
            "--test",
            get_data("tests/test-data/short-names.yml"),
            "--junit-xml",
            junit_xml_report,
        ]
        run_with_mock_cwl_runner(args)
        tree = ET.parse(junit_xml_report)
        root = tree.getroot()
        category = root.find("testsuite").find("testcase").attrib["file"]
        self.assertEqual(category, "opt-error")
        os.remove(junit_xml_report)
