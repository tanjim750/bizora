"""Tests for the reporting period and its presets.

Ported from ``tests/Unit/Insights/DateRangeTest.php``.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from metametrics.exceptions import InvalidInputError
from metametrics.insights.date_range.preset import DatePreset
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.date_range.timezone import AccountTimezone


def test_it_preserves_an_explicit_valid_range() -> None:
    period = DateRange("2026-09-01", "2026-09-24")

    assert period.since == "2026-09-01"
    assert period.until == "2026-09-24"
    assert period.to_dict() == {"since": "2026-09-01", "until": "2026-09-24"}


@pytest.mark.parametrize(
    ("since", "until"),
    [
        ("2026-09-24", "2026-09-01"),
        ("2026-02-30", "2026-03-01"),
        ("09/01/2026", "2026-09-24"),
        ("", "2026-09-24"),
    ],
    ids=["reversed", "impossible date", "wrong format", "missing boundary"],
)
def test_it_rejects_invalid_ranges(since: str, until: str) -> None:
    with pytest.raises(InvalidInputError):
        DateRange(since, until)


def test_presets_use_the_ad_account_timezone() -> None:
    account_timezone = AccountTimezone("Europe/London")
    now_in_dhaka = datetime.fromisoformat("2026-10-01T00:30:00+06:00")

    today = DatePreset.TODAY.resolve(account_timezone, now_in_dhaka)
    current_month = DatePreset.CURRENT_MONTH.resolve(account_timezone, now_in_dhaka)
    previous_month = DatePreset.PREVIOUS_MONTH.resolve(account_timezone, now_in_dhaka)

    assert today.to_dict() == {"since": "2026-09-30", "until": "2026-09-30"}
    assert current_month.to_dict() == {"since": "2026-09-01", "until": "2026-09-30"}
    assert previous_month.to_dict() == {"since": "2026-08-01", "until": "2026-08-31"}


def test_the_yesterday_preset_uses_the_ad_account_timezone() -> None:
    account_timezone = AccountTimezone("Europe/London")
    now_in_dhaka = datetime.fromisoformat("2026-10-01T00:30:00+06:00")

    yesterday = DatePreset.YESTERDAY.resolve(account_timezone, now_in_dhaka)

    assert yesterday.to_dict() == {"since": "2026-09-29", "until": "2026-09-29"}


def test_it_rejects_an_invalid_account_timezone() -> None:
    with pytest.raises(InvalidInputError, match="valid timezone name"):
        AccountTimezone("Not/A-Timezone")
