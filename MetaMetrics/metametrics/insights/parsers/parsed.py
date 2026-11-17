"""The parsed form of one raw Meta Insights row."""

from __future__ import annotations

from dataclasses import dataclass

from metametrics.insights.date_range.range import DateRange
from metametrics.insights.raw_data import InsightsRawData

__all__ = ["ParsedInsights"]


@dataclass(frozen=True, slots=True)
class ParsedInsights:
    """One raw Insights row after parsing but before metric computation."""

    entity_id: str
    entity_name: str | None
    campaign_id: str | None
    ad_set_id: str | None
    ad_id: str | None
    date_range: DateRange
    foundational: dict[str, float | None]
    raw_data: InsightsRawData
    currency: str | None = None
