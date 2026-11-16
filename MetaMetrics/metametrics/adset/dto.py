"""The Ad Set data transfer object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = ["AdSetDTO"]


@dataclass(frozen=True, slots=True)
class AdSetDTO:
    """Normalised Ad Set metadata."""

    id: str
    name: str
    campaign_id: str
    status: str | None = None
    configured_status: str | None = None
    effective_status: str | None = None
    optimization_goal: str | None = None
    billing_event: str | None = None
    daily_budget: str | None = None
    lifetime_budget: str | None = None
    created_time: datetime | None = None
    updated_time: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
