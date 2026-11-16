"""The relative reporting periods supported by the library."""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from enum import StrEnum

from metametrics.insights.date_range.range import DateRange
from metametrics.insights.date_range.timezone import AccountTimezone

__all__ = ["DatePreset"]


class DatePreset(StrEnum):
    """A relative reporting period, resolved in the Ad Account's timezone."""

    TODAY = "today"
    YESTERDAY = "yesterday"
    CURRENT_MONTH = "current_month"
    PREVIOUS_MONTH = "previous_month"

    def resolve(self, account_timezone: AccountTimezone, now: datetime | None = None) -> DateRange:
        """Resolve the preset into a concrete reporting period."""
        timezone = account_timezone.timezone
        today = (
            (now if now is not None else datetime.now(timezone))
            .astimezone(timezone)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

        if self == DatePreset.TODAY:
            return DateRange(today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))

        if self == DatePreset.YESTERDAY:
            yesterday = today - timedelta(days=1)
            return DateRange(yesterday.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d"))

        if self == DatePreset.CURRENT_MONTH:
            first = today.replace(day=1)
            return DateRange(first.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))

        year, month = _previous_month(today.year, today.month)
        first = today.replace(year=year, month=month, day=1)
        last = today.replace(year=year, month=month, day=calendar.monthrange(year, month)[1])
        return DateRange(first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d"))


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12

    return year, month - 1
