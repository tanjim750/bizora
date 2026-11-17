"""The envelope of an Insights query."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from metametrics.exceptions import InvalidInputError
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.level import InsightsLevel

__all__ = ["InsightsResponse"]

_CURRENCY_PATTERN: re.Pattern[str] = re.compile(r"\A[A-Z]{3}\Z")


@dataclass(frozen=True, slots=True)
class InsightsResponse:
    """The level, currency, and rows of one Insights query."""

    level: InsightsLevel
    currency: str
    data: tuple[InsightsDTO, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not _CURRENCY_PATTERN.match(self.currency):
            raise InvalidInputError("Insights response requires a valid currency code.")

        for row in self.data:
            if not isinstance(row, InsightsDTO) or row.level != self.level or row.currency != self.currency:
                raise InvalidInputError("Insights response rows must share its level and currency.")

    def to_dict(self) -> dict[str, object]:
        """Render the envelope as a plain dictionary."""
        return {
            "level": self.level.value,
            "currency": self.currency,
            "data": [row.to_dict(include_currency=False) for row in self.data],
        }
