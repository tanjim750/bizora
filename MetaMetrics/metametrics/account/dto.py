"""The Ad Account data transfer object."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["AccountDTO"]


@dataclass(frozen=True, slots=True)
class AccountDTO:
    """Normalised Ad Account metadata."""

    id: str
    name: str
    account_id: str
    account_status: int | None = None
    currency: str | None = None
    timezone_name: str | None = None
