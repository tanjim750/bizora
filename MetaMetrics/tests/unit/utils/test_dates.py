"""Tests for the strict timestamp and date helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from metametrics.utils.dates import parse_date, parse_datetime


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-08-10T00:00:00+0000", datetime(2026, 8, 10, tzinfo=UTC)),
        ("2026-08-10T00:00:00Z", datetime(2026, 8, 10, tzinfo=UTC)),
        ("2026-08-10T02:00:00+02:00", datetime(2026, 8, 10, tzinfo=UTC)),
        ("2026-08-10T00:00:00", datetime(2026, 8, 10, tzinfo=UTC)),
        ("2026-08-10", datetime(2026, 8, 10, tzinfo=UTC)),
        ("@1754870400", datetime(2025, 8, 11, tzinfo=UTC)),
    ],
)
def test_it_parses_supported_timestamps(value: str, expected: datetime) -> None:
    assert parse_datetime(value) == expected


@pytest.mark.parametrize("value", ["", "   ", "not-a-date", "@not-an-epoch", "2026-13-45"])
def test_it_rejects_malformed_timestamps(value: str) -> None:
    with pytest.raises(ValueError):
        parse_datetime(value)


def test_it_parses_a_strict_date() -> None:
    assert parse_date("2026-09-01") == datetime(2026, 9, 1, tzinfo=UTC)


@pytest.mark.parametrize("value", ["2026-9-1", "2026-02-30", "01-09-2026", "", "not-a-date"])
def test_it_rejects_non_canonical_dates(value: str) -> None:
    with pytest.raises(ValueError):
        parse_date(value)
