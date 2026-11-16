"""Tests for the strict numeric coercion helpers."""

from __future__ import annotations

import math

import pytest

from metametrics.utils.numbers import to_finite_float, to_strict_int


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12.5", 12.5),
        ("  12.5  ", 12.5),
        ("1e3", 1000.0),
        ("-3", -3.0),
        (42, 42.0),
        (4.25, 4.25),
    ],
)
def test_it_accepts_numeric_values(value: object, expected: float) -> None:
    assert to_finite_float(value) == expected


@pytest.mark.parametrize(
    "value",
    [True, False, None, "not-a-number", "", "nan", "inf", "-inf", "1,5", [1], {"a": 1}, float("inf")],
)
def test_it_rejects_non_numeric_values(value: object) -> None:
    with pytest.raises(ValueError):
        to_finite_float(value)


def test_it_rejects_a_non_finite_result() -> None:
    with pytest.raises(ValueError):
        to_finite_float("1e400")

    assert not math.isfinite(float("1e400"))


def test_it_accepts_strict_integers() -> None:
    assert to_strict_int(42) == 42


@pytest.mark.parametrize("value", [True, False, 4.0, "42", None, [1]])
def test_it_rejects_non_integers(value: object) -> None:
    with pytest.raises(ValueError):
        to_strict_int(value)
