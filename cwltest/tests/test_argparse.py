from cwltest import arg_parser


def test_arg():
    """Basic test of the argparse."""
    parser = arg_parser()
    parsed = parser.parse_args(
        ["--test", "test_name", "-n", "52", "--tool", "cwltool", "-j", "4"]
    )
    assert parsed.test == "test_name"
    assert parsed.n == "52"
    assert parsed.tool == "cwltool"
    assert parsed.j == 4
