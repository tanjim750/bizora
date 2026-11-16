"""Timestamp parsing helpers.

Meta returns timestamps in ISO 8601 form. The PHP original accepted anything
``DateTimeImmutable`` understood and normalised the result to UTC; the Python
port accepts ISO 8601 (with or without an offset) and Unix epoch strings, and
always returns an aware UTC ``datetime``.
"""

from __future__ import annotations

from datetime import UTC, datetime

__all__ = ["parse_date", "parse_datetime"]


def parse_datetime(value: str) -> datetime:
    """Parse a Meta timestamp into an aware UTC ``datetime``.

    Raises:
        ValueError: when the value is not a recognisable timestamp.
    """
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError("Timestamp must be a non-empty string.")

    candidate = value.strip()

    if candidate.startswith("@"):
        try:
            return datetime.fromtimestamp(int(candidate[1:]), tz=UTC)
        except (ValueError, OverflowError, OSError) as error:
            raise ValueError("Timestamp must be a valid Unix epoch value.") from error

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise ValueError("Timestamp must be a valid ISO 8601 value.") from error

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def parse_date(value: str) -> datetime:
    """Parse a strict ``YYYY-MM-DD`` date into a UTC ``datetime``.

    ``datetime.strptime`` accepts ``2026-9-1``; PHP's
    ``DateTimeImmutable::createFromFormat('!Y-m-d', ...)`` does not. The
    round-trip comparison restores that strictness.

    Raises:
        ValueError: when the value is not a valid ``YYYY-MM-DD`` date.
    """
    if not isinstance(value, str):
        raise ValueError("Date must be a YYYY-MM-DD string.")

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("Date must be a valid YYYY-MM-DD value.") from error

    if parsed.strftime("%Y-%m-%d") != value:
        raise ValueError("Date must be a valid YYYY-MM-DD value.")

    return parsed.replace(tzinfo=UTC)
