from .util import get_data, run_with_mock_cwl_runner


def test_warning_with_integer_id() -> None:
    args = [
        "--test",
        get_data("tests/test-data/integer-id.yml"),
        "-l",
    ]
    error_code, stdout, stderr = run_with_mock_cwl_runner(args)
    assert (
        "The `id` field with integer is deprecated. Use string identifier instead."
        in stderr
    )
