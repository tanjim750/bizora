"""Strict numeric coercion helpers.

PHP's ``is_numeric`` accepts numeric strings but rejects booleans, ``null``,
arrays and ``"nan"``. Python's ``float()`` accepts ``"nan"``/``"inf"``, and
``bool`` is a subclass of ``int``. These helpers restore PHP's strictness so
that a malformed Meta payload is rejected rather than silently normalised.
"""

from __future__ import annotations

import math
import re
from typing import TypeGuard

__all__ = ["is_numeric", "to_finite_float", "to_strict_int"]

_NUMERIC_PATTERN: re.Pattern[str] = re.compile(r"\A[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def is_numeric(value: object) -> TypeGuard[str | int | float]:
    """Whether a value is numeric in PHP's sense.

    Numeric strings are accepted (with surrounding whitespace); booleans,
    ``None``, containers, and ``"nan"``/``"inf"`` are not.
    """
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return False

    if isinstance(value, str):
        return bool(_NUMERIC_PATTERN.match(value.strip()))

    return True


def to_finite_float(value: object) -> float:
    """Coerce a Meta numeric value into a finite ``float``.

    Raises:
        ValueError: when the value is not numeric or is not finite.
    """
    if not is_numeric(value):
        raise ValueError("Value must be numeric.")

    number = float(value.strip()) if isinstance(value, str) else float(value)

    if not math.isfinite(number):
        raise ValueError("Value must be finite.")

    return number


def to_strict_int(value: object) -> int:
    """Coerce a Meta integral value into an ``int``.

    PHP's ``is_int`` rejects booleans and floats; Python's ``bool`` is an
    ``int`` subclass, so booleans are rejected explicitly.

    Raises:
        ValueError: when the value is not an integer.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Value must be an integer.")

    return value
