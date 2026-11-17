"""The Ad data transfer object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = ["AdDTO"]


@dataclass(frozen=True, slots=True)
class AdDTO:
    """Normalised Ad metadata."""

    id: str
    name: str
    ad_set_id: str
    campaign_id: str
    status: str | None = None
    configured_status: str | None = None
    effective_status: str | None = None
    created_time: datetime | None = None
    updated_time: datetime | None = None
