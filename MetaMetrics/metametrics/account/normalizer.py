"""Normalisation of raw Ad Account payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from metametrics.account.dto import AccountDTO
from metametrics.utils.payload import PayloadReader

__all__ = ["AccountNormalizer"]


class AccountNormalizer:
    """Turns a raw Ad Account payload into an :class:`AccountDTO`."""

    def __init__(self) -> None:
        self.reader = PayloadReader(
            "Ad Account",
            optional_string_message='Meta Ad Account field "{field}" must be a non-empty string.',
        )

    def normalize(self, account: Mapping[str, Any]) -> AccountDTO:
        """Normalise a decoded Ad Account payload."""
        return AccountDTO(
            id=self.reader.required_string(account, "id"),
            name=self.reader.required_string(account, "name"),
            account_id=self.reader.required_string(account, "account_id"),
            account_status=self.reader.optional_int(account, "account_status"),
            currency=self.reader.optional_string(account, "currency"),
            timezone_name=self.reader.optional_string(account, "timezone_name"),
        )
