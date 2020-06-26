import unittest
from cwltest import arg_parser


class TestArgparse(unittest.TestCase):
    def setUp(self):
        self.parser = arg_parser()

    def test_arg(self):
        parsed = self.parser.parse_args(
            ["--test", "test_name", "-n", "52", "--tool", "cwltool", "-j", "4"]
        )
        self.assertEqual(parsed.test, "test_name")
        self.assertEqual(parsed.n, "52")
        self.assertEqual(parsed.tool, "cwltool")
        self.assertEqual(parsed.j, 4)


if __name__ == "__main__":
    unittest.main()
