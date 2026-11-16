"""The envelope of a Historical analysis query."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from metametrics.exceptions import InvalidInputError
from metametrics.historical.level import HistoricalLevel
from metametrics.historical.result import HistoricalResult

__all__ = ["HistoricalResponse"]

_CURRENCY_PATTERN: re.Pattern[str] = re.compile(r"\A[A-Z]{3}\Z")


@dataclass(frozen=True, slots=True)
class HistoricalResponse:
    """The level, currency, and rows of one Historical analysis query."""

    level: HistoricalLevel
    currency: str
    data: tuple[HistoricalResult, ...] = field(default_factory=tuple)

    def __init__(
        self,
        level: HistoricalLevel,
        currency: str,
        data: Sequence[HistoricalResult] = (),
    ) -> None:
        if not _CURRENCY_PATTERN.match(currency):
            raise InvalidInputError("Historical response requires a valid currency code.")

        data_tuple = tuple(data)
        for row in data_tuple:
            if not isinstance(row, HistoricalResult) or row.level != level or row.currency != currency:
                raise InvalidInputError("Historical response rows must share its level and currency.")

        object.__setattr__(self, "level", level)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "data", data_tuple)

    def to_dict(self) -> dict[str, Any]:
        """Render the envelope as a plain dictionary."""
        return {
            "level": self.level.value,
            "currency": self.currency,
            "data": [row.to_dict(include_currency=False) for row in self.data],
        }
