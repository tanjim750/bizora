"""The reporting period of an Insights query."""

from __future__ import annotations

from dataclasses import dataclass

from metametrics.exceptions import InvalidInputError
from metametrics.utils.dates import parse_date

__all__ = ["DateRange"]


@dataclass(frozen=True, slots=True)
class DateRange:
    """An inclusive ``YYYY-MM-DD`` reporting period."""

    since: str
    until: str

    def __init__(self, since: str, until: str) -> None:
        try:
            start = parse_date(since)
            end = parse_date(until)
        except ValueError as error:
            raise InvalidInputError(str(error)) from error

        if start > end:
            raise InvalidInputError("Insights date range since must be before or equal to until.")

        object.__setattr__(self, "since", since)
        object.__setattr__(self, "until", until)

    def to_dict(self) -> dict[str, str]:
        """Render the period as a Meta ``time_range`` payload."""
        return {"since": self.since, "until": self.until}
