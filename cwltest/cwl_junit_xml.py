import xml.etree.ElementTree as ET

from junit_xml import TestCase, TestSuite, decode
from typing import Any


class CWLTestCase(TestCase):

    def __init__(self, name, classname=None, elapsed_sec=None, stdout=None,
                 stderr=None, assertions=None, timestamp=None, status=None,
                 category=None, file=None, line=None, log=None, group=None,
                 url=None, short_name=None):
        # type: (Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any) -> None
        super(CWLTestCase, self).__init__(name, classname=classname, elapsed_sec=elapsed_sec, stdout=stdout,
                 stderr=stderr, assertions=assertions, timestamp=timestamp, status=status,
                 category=category, file=file, line=line, log=log, group=group,
                 url=url)
        self.short_name = short_name


class CWLTestSuite(TestSuite):
    def build_xml_doc(self, encoding=None):
        """
        This code duplicates the code in junit_xml.TestSuite.build_xml_doc
        but allows to add `short_name` attribute from TestCase
        """

        # build the test suite element
        test_suite_attributes = dict()
        test_suite_attributes['name'] = decode(self.name, encoding)
        if any(c.assertions for c in self.test_cases):
            test_suite_attributes['assertions'] = \
                str(sum([int(c.assertions) for c in self.test_cases if c.assertions]))
        test_suite_attributes['disabled'] = \
            str(len([c for c in self.test_cases if not c.is_enabled]))
        test_suite_attributes['failures'] = \
            str(len([c for c in self.test_cases if c.is_failure()]))
        test_suite_attributes['errors'] = \
            str(len([c for c in self.test_cases if c.is_error()]))
        test_suite_attributes['skipped'] = \
            str(len([c for c in self.test_cases if c.is_skipped()]))
        test_suite_attributes['time'] = \
            str(sum(c.elapsed_sec for c in self.test_cases if c.elapsed_sec))
        test_suite_attributes['tests'] = str(len(self.test_cases))

        if self.hostname:
            test_suite_attributes['hostname'] = decode(self.hostname, encoding)
        if self.id:
            test_suite_attributes['id'] = decode(self.id, encoding)
        if self.package:
            test_suite_attributes['package'] = decode(self.package, encoding)
        if self.timestamp:
            test_suite_attributes['timestamp'] = decode(self.timestamp, encoding)
        if self.timestamp:
            test_suite_attributes['file'] = decode(self.file, encoding)
        if self.timestamp:
            test_suite_attributes['log'] = decode(self.log, encoding)
        if self.timestamp:
            test_suite_attributes['url'] = decode(self.url, encoding)

        xml_element = ET.Element("testsuite", test_suite_attributes)

        # add any properties
        if self.properties:
            props_element = ET.SubElement(xml_element, "properties")
            for k, v in self.properties.items():
                attrs = {'name': decode(k, encoding), 'value': decode(v, encoding)}
                ET.SubElement(props_element, "property", attrs)

        # add test suite stdout
        if self.stdout:
            stdout_element = ET.SubElement(xml_element, "system-out")
            stdout_element.text = decode(self.stdout, encoding)

        # add test suite stderr
        if self.stderr:
            stderr_element = ET.SubElement(xml_element, "system-err")
            stderr_element.text = decode(self.stderr, encoding)

        # test cases
        for case in self.test_cases:
            test_case_attributes = dict()
            test_case_attributes['name'] = decode(case.name, encoding)
            if case.assertions:
                # Number of assertions in the test case
                test_case_attributes['assertions'] = "%d" % case.assertions
            if case.elapsed_sec:
                test_case_attributes['time'] = "%f" % case.elapsed_sec
            if case.timestamp:
                test_case_attributes['timestamp'] = decode(case.timestamp, encoding)
            if case.classname:
                test_case_attributes['classname'] = decode(case.classname, encoding)
            if case.status:
                test_case_attributes['status'] = decode(case.status, encoding)
            if case.category:
                test_case_attributes['class'] = decode(case.category, encoding)
            if case.file:
                test_case_attributes['file'] = decode(case.file, encoding)
            if case.line:
                test_case_attributes['line'] = decode(case.line, encoding)
            if case.log:
                test_case_attributes['log'] = decode(case.log, encoding)
            if case.url:
                test_case_attributes['url'] = decode(case.url, encoding)
            if case.short_name:
                test_case_attributes['short_name'] = decode(case.short_name, encoding)

            test_case_element = ET.SubElement(
                xml_element, "testcase", test_case_attributes)

            # failures
            if case.is_failure():
                attrs = {'type': 'failure'}
                if case.failure_message:
                    attrs['message'] = decode(case.failure_message, encoding)
                if case.failure_type:
                    attrs['type'] = decode(case.failure_type, encoding)
                failure_element = ET.Element("failure", attrs)
                if case.failure_output:
                    failure_element.text = decode(case.failure_output, encoding)
                test_case_element.append(failure_element)

            # errors
            if case.is_error():
                attrs = {'type': 'error'}
                if case.error_message:
                    attrs['message'] = decode(case.error_message, encoding)
                if case.error_type:
                    attrs['type'] = decode(case.error_type, encoding)
                error_element = ET.Element("error", attrs)
                if case.error_output:
                    error_element.text = decode(case.error_output, encoding)
                test_case_element.append(error_element)

            # skippeds
            if case.is_skipped():
                attrs = {'type': 'skipped'}
                if case.skipped_message:
                    attrs['message'] = decode(case.skipped_message, encoding)
                skipped_element = ET.Element("skipped", attrs)
                if case.skipped_output:
                    skipped_element.text = decode(case.skipped_output, encoding)
                test_case_element.append(skipped_element)

            # test stdout
            if case.stdout:
                stdout_element = ET.Element("system-out")
                stdout_element.text = decode(case.stdout, encoding)
                test_case_element.append(stdout_element)

            # test stderr
            if case.stderr:
                stderr_element = ET.Element("system-err")
                stderr_element.text = decode(case.stderr, encoding)
                test_case_element.append(stderr_element)

        return xml_element
