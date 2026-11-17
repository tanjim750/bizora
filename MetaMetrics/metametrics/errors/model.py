"""Parsing and mapping of Meta API error payloads."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["MetaError"]


@dataclass(frozen=True, slots=True)
class MetaError:
    """The diagnostic fields extracted from a Meta API error payload."""

    http_status: int
    message: str | None
    type: str | None
    code: int | None
    subcode: int | None
    trace_id: str | None
    transient: bool | None
