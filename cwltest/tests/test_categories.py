import unittest
import re
import os
from os import linesep as n
from os import sep as p

from .util import run_with_mock_cwl_runner, get_data
import xml.etree.ElementTree as ET


class TestCategories(unittest.TestCase):

    def test_unsupported_with_required_tests(self):
        args = ["--test", get_data("tests/test-data/required-unsupported.yml")]
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
        self.assertEqual(error_code, 1)
        print(stderr)
        stderr = re.sub(r" '?--outdir=[^ ]*", '', stderr)
        self.assertEqual(
            "Test [1/2] Required test that is unsupported (without tags){n}"
            "{n}"
            "Test 1 failed: mock-cwl-runner --quiet return-unsupported.cwl v1.0{p}cat-job.json{n}"
            "Required test that is unsupported (without tags){n}"
            "Does not support required feature{n}"
            "{n}"
            "Test [2/2] Required test that is unsupported (with tags){n}"
            "{n}"
            "Test 2 failed: mock-cwl-runner --quiet return-unsupported.cwl v1.0{p}cat-job.json{n}"
            "Required test that is unsupported (with tags){n}"
            "Does not support required feature{n}"
            "{n}"
            "0 tests passed, 2 failures, 0 unsupported features{n}".format(n=n, p=p), stderr)

    def test_unsupported_with_optional_tests(self):
        args = ["--test", get_data("tests/test-data/optional-unsupported.yml")]
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
        self.assertEqual(error_code, 0)
        self.assertEqual("Test [1/1] Optional test that is unsupported{n}{n}"
                         "0 tests passed, 1 unsupported "
                         "features{n}".format(n=n), stderr)

    def test_error_with_optional_tests(self):
        args = ["--test", get_data("tests/test-data/optional-error.yml")]
        error_code, stdout, stderr = run_with_mock_cwl_runner(args)
        self.assertEqual(error_code, 1)
        self.assertIn("1 failures", stderr)

    def test_category_in_junit_xml(self):
        junit_xml_report = get_data("tests/test-data/junit-report.xml")
        args = ["--test", get_data("tests/test-data/optional-error.yml"), "--junit-xml", junit_xml_report]
        run_with_mock_cwl_runner(args)
        tree = ET.parse(junit_xml_report)
        root = tree.getroot()
        category = root.find("testsuite").find("testcase").attrib['class']
        self.assertEqual(category, "js, init_work_dir")
        os.remove(junit_xml_report)
