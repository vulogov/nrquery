"""Tests for sample"""
import pytest

import nrquery


def test_main() -> None:
    """Main test"""
    assert nrquery.main()


@pytest.mark.parametrize(
    ("value_in", "expected"),
    (
        (2, 4),
        (4, 16),
        (16, 256),
    ),
)
def test_squared(value_in: int, expected: int) -> None:
    assert nrquery.squared(value_in) == expected
