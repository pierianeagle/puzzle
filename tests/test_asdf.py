import pytest

from jfdi.asdf import add


@pytest.mark.parametrize(
    "test_input, expected_output",
    [
        ({"a": 1, "b": 1}, 2),
        ({"a": 1, "b": 2}, 3),
    ],
)
def test_add(test_input, expected_output):
    assert add(**test_input) == expected_output
