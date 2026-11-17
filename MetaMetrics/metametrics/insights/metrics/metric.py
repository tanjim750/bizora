"""The metrics MetaMetrics understands."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["Metric"]


class Metric(StrEnum):
    """A performance metric that can be requested from the Meta Insights API."""

    SPEND = "spend"
    PURCHASES = "purchases"
    COST_PER_PURCHASE = "cost_per_purchase"
    PURCHASE_VALUE = "purchase_value"
    ROAS = "roas"
    IMPRESSIONS = "impressions"
    REACH = "reach"
    CLICKS = "clicks"
    LINK_CLICKS = "link_clicks"
    CPC = "cpc"
    CTR = "ctr"
    CPM = "cpm"
