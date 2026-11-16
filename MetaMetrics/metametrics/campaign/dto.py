"""The Campaign data transfer object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = ["CampaignDTO"]


@dataclass(frozen=True, slots=True)
class CampaignDTO:
    """Normalised Campaign metadata."""

    id: str
    name: str
    status: str | None = None
    configured_status: str | None = None
    effective_status: str | None = None
    objective: str | None = None
    created_time: datetime | None = None
    updated_time: datetime | None = None
