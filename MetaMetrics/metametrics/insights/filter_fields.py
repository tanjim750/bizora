"""The filter fields supported by the Meta Insights API."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["InsightsFilterField"]


class InsightsFilterField(StrEnum):
    """The Insights filter fields MetaMetrics allows."""

    CAMPAIGN_ID = "campaign.id"
    CAMPAIGN_NAME = "campaign.name"
    CAMPAIGN_EFFECTIVE_STATUS = "campaign.effective_status"
    AD_SET_ID = "adset.id"
    AD_SET_NAME = "adset.name"
    AD_SET_EFFECTIVE_STATUS = "adset.effective_status"
    AD_ID = "ad.id"
    AD_NAME = "ad.name"
    AD_EFFECTIVE_STATUS = "ad.effective_status"

    @classmethod
    def values(cls) -> list[str]:
        """Return every allowed filter field."""
        return [field.value for field in cls]
