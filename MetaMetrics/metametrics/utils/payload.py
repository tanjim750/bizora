"""Strict extraction of typed fields from raw Meta payloads.

Each PHP normalizer repeats the same handful of checks with an entity-specific
message. This reader centralises the checks while keeping the original
messages, so a ported payload produces the same error text as the PHP library.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from metametrics.exceptions import UnexpectedResponseError
from metametrics.utils.dates import parse_datetime

__all__ = ["PayloadReader"]


class PayloadReader:
    """Reads strictly typed fields out of a decoded Meta payload."""

    def __init__(self, label: str, *, optional_string_message: str | None = None) -> None:
        self.label = label
        self._optional_string_message = optional_string_message

    def required_string(self, data: Mapping[str, Any], field: str) -> str:
        value = data.get(field)

        if not isinstance(value, str) or value == "":
            raise UnexpectedResponseError(f'Meta {self.label} response requires a valid "{field}" field.')

        return value

    def optional_string(self, data: Mapping[str, Any], field: str) -> str | None:
        if field not in data or data[field] is None:
            return None

        value = data[field]
        if not isinstance(value, str) or value == "":
            message = self._optional_string_message or f'Meta {self.label} field "{field}" must be a string.'
            raise UnexpectedResponseError(message)

        return value

    def optional_int(self, data: Mapping[str, Any], field: str) -> int | None:
        if field not in data or data[field] is None:
            return None

        value = data[field]
        if isinstance(value, bool) or not isinstance(value, int):
            raise UnexpectedResponseError(f'Meta {self.label} field "{field}" must be an integer.')

        return value

    def optional_datetime(self, data: Mapping[str, Any], field: str) -> datetime | None:
        value = self.optional_string(data, field)

        if value is None:
            return None

        try:
            return parse_datetime(value)
        except ValueError as error:
            raise UnexpectedResponseError(
                f'Meta {self.label} field "{field}" must be a valid timestamp.'
            ) from error
