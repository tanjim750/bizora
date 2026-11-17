"""Meta query filters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from metametrics.exceptions import InvalidInputError

__all__ = ["Filter", "FilterOperator"]

_FILTER_FIELD_PATTERN: re.Pattern[str] = re.compile(r"\A[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)?\Z")


class FilterOperator(StrEnum):
    """The comparison operators supported by the Meta ``filtering`` parameter."""

    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAIN = "CONTAIN"
    NOT_CONTAIN = "NOT_CONTAIN"


_LIST_OPERATORS: frozenset[FilterOperator] = frozenset({FilterOperator.IN, FilterOperator.NOT_IN})

FilterValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class Filter:
    """A single Meta Insights filter."""

    field: str
    operator: FilterOperator
    value: FilterValue | tuple[FilterValue, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.field, str) or not _FILTER_FIELD_PATTERN.match(self.field):
            raise InvalidInputError("Filter field must use a valid Meta field name.")

        if isinstance(self.value, (list, tuple)):
            for item in self.value:
                if not isinstance(item, (str, int, float, bool)):
                    raise InvalidInputError("Filter list values must be scalar.")

            object.__setattr__(self, "value", tuple(self.value))

        if self.operator in _LIST_OPERATORS:
            if not isinstance(self.value, tuple) or len(self.value) == 0:
                raise InvalidInputError(f"{self.operator.value} filters require a non-empty value list.")
        elif isinstance(self.value, tuple):
            raise InvalidInputError(f"{self.operator.value} filters require a scalar value.")

    def to_dict(self) -> dict[str, Any]:
        """Render the filter as a Meta ``filtering`` entry."""
        value: Any = list(self.value) if isinstance(self.value, tuple) else self.value

        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": value,
        }
