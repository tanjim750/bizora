"""Meta field selection."""

from __future__ import annotations

import re
from dataclasses import dataclass

from metametrics.exceptions import InvalidInputError

__all__ = ["Fields"]

_FIELD_PATTERN: re.Pattern[str] = re.compile(r"\A[a-z][a-z0-9_]*\Z")


@dataclass(frozen=True, slots=True)
class Fields:
    """An immutable, de-duplicated selection of Meta fields."""

    values: tuple[str, ...]

    def __init__(self, values: list[str] | tuple[str, ...]) -> None:
        if not values:
            raise InvalidInputError("At least one field must be selected.")

        unique: list[str] = []
        for field in values:
            if not isinstance(field, str) or not _FIELD_PATTERN.match(field):
                raise InvalidInputError("Selected fields must use valid Meta field names.")

            if field not in unique:
                unique.append(field)

        object.__setattr__(self, "values", tuple(unique))

    def with_required(self, fields: list[str] | tuple[str, ...]) -> Fields:
        """Return a copy that also contains the given required fields."""
        merged: list[str] = []
        for field in [*fields, *self.values]:
            if field not in merged:
                merged.append(field)

        return Fields(merged)

    def to_query_value(self) -> str:
        """Render the selection as a Meta ``fields`` query value."""
        return ",".join(self.values)
