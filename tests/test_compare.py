import unittest
from cwltest import CompareFail
from cwltest.utils import compare_file, compare


class TestCompare(unittest.TestCase):

    def compare_success(self, expected, actual):
        try:
            compare(expected, actual)
        except CompareFail:
            self.fail("Comparison failed unexpectedly")


class TestCompareFile(TestCompare):

    def test_compare_file(self):
        expected = {
            "location": "cores.txt",
            "size": 2,
            "class": "File",
            "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a"
         }

        actual = {
            "basename": "cores.txt",
            "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
            "class": "File",
            "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
            "path": "/var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
            "size": 2
        }
        try:
            compare_file(expected, actual)
        except CompareFail:
            self.fail("File comparison failed unexpectedly")

    def test_compare_contents_success(self):
        expected = {
            "location": "cores.txt",
            "size": 2,
            "class": "File",
            "contents": "2\n"
        }

        actual = {
            "basename": "cores.txt",
            "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
            "class": "File",
            "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
            "path": "tests/test-data/cores.txt",
            "size": 2
        }
        self.compare_success(expected, actual)

    def test_compare_contents_failure(self):
        expected = {
            "location": "cores.txt",
            "size": 2,
            "class": "File",
            "contents": "2"
        }

        actual = {
            "basename": "cores.txt",
            "checksum": "sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a",
            "class": "File",
            "location": "file:///var/folders/8x/2df05_7j20j6r8y81w4qf43r0000gn/T/tmpG0EkrS/cores.txt",
            "path": "tests/test-data/cores.txt",
            "size": 2
        }
        with self.assertRaises(CompareFail):
            compare_file(expected, actual)
