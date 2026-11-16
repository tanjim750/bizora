"""The reporting levels supported by the Meta Insights API."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["InsightsLevel"]


class InsightsLevel(StrEnum):
    """The entity level an Insights query is reported at."""

    ACCOUNT = "account"
    CAMPAIGN = "campaign"
    AD_SET = "adset"
    AD = "ad"
