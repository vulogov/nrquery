"""Tests for sample"""
import pytest

import module_example


def test_main() -> None:
    """Main test"""
    assert module_example.main()


@pytest.mark.parametrize(
    ("value_in", "expected"),
    (
        (2, 4),
        (4, 16),
        (16, 256),
    ),
)
def test_squared(value_in: int, expected: int) -> None:
    assert module_example.squared(value_in) == expected
