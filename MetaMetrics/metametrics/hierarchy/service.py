"""Hierarchy assembly service for Meta advertising entities."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from metametrics.hierarchy.node import HierarchyNode
from metametrics.hierarchy.result import HierarchyResult
from metametrics.historical.level import HistoricalLevel
from metametrics.historical.query import HistoricalQuery
from metametrics.historical.result import HistoricalResult
from metametrics.historical.service import HistoricalService
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.metrics.metric import Metric

__all__ = ["HierarchyService"]


class HierarchyService:
    """Builds a connected tree of Campaign -> AdSet -> Ad entities."""

    def __init__(self, historical_service: HistoricalService) -> None:
        self._historical_service = historical_service

    def historical(
        self,
        date_range: DateRange,
        metrics: Sequence[Metric] = (),
        daily: bool = False,
    ) -> HierarchyResult:
        """Fetch historical performance and reconstruct the hierarchy tree."""
        campaign_response = self._historical_service.get_response(
            HistoricalQuery(
                level=HistoricalLevel.CAMPAIGN,
                date_range=date_range,
                metrics=metrics,
                daily=daily,
            )
        )
        ad_sets = self._historical_service.get(
            HistoricalQuery(
                level=HistoricalLevel.AD_SET,
                date_range=date_range,
                metrics=metrics,
                daily=daily,
            )
        )
        ads = self._historical_service.get(
            HistoricalQuery(
                level=HistoricalLevel.AD,
                date_range=date_range,
                metrics=metrics,
                daily=daily,
            )
        )

        return self._build(
            date_range=date_range,
            campaigns=list(campaign_response.data),
            ad_sets=ad_sets,
            ads=ads,
            currency=campaign_response.currency,
        )

    def _build(
        self,
        date_range: DateRange,
        campaigns: Sequence[HistoricalResult],
        ad_sets: Sequence[HistoricalResult],
        ads: Sequence[HistoricalResult],
        currency: str,
    ) -> HierarchyResult:
        ads_by_ad_set: dict[str, list[HierarchyNode]] = defaultdict(list)
        for ad in ads:
            ads_by_ad_set[self._parent_key(ad.ad_set_id, ad)].append(HierarchyNode(ad))

        ad_set_nodes: dict[str, HierarchyNode] = {}
        ad_sets_by_campaign: dict[str, list[HierarchyNode]] = defaultdict(list)
        attached_ad_keys: set[str] = set()

        for ad_set in ad_sets:
            key = self._result_key(ad_set)
            child_key = self._parent_key(ad_set.ad_set_id, ad_set)
            children = ads_by_ad_set.get(child_key, [])
            node = HierarchyNode(ad_set, children)
            ad_set_nodes[key] = node
            ad_sets_by_campaign[self._parent_key(ad_set.campaign_id, ad_set)].append(node)

            if children:
                attached_ad_keys.add(child_key)

        campaign_nodes: list[HierarchyNode] = []
        attached_ad_set_keys: set[str] = set()

        for campaign in campaigns:
            child_key = self._parent_key(campaign.campaign_id, campaign)
            children = ad_sets_by_campaign.get(child_key, [])
            campaign_nodes.append(HierarchyNode(campaign, children))

            for child in children:
                attached_ad_set_keys.add(self._result_key(child.historical_result))

        unattached_ad_sets = [
            node
            for key, node in ad_set_nodes.items()
            if key not in attached_ad_set_keys
        ]

        unattached_ads: list[HierarchyNode] = []
        for key, nodes in ads_by_ad_set.items():
            if key not in attached_ad_keys:
                unattached_ads.extend(nodes)

        return HierarchyResult(
            requested_period=date_range,
            campaigns=campaign_nodes,
            unattached_ad_sets=unattached_ad_sets,
            unattached_ads=unattached_ads,
            currency=currency,
        )

    def _result_key(self, result: HistoricalResult) -> str:
        return f"{result.entity_id}:{result.insights.date_start}:{result.insights.date_stop}"

    def _parent_key(self, parent_id: str | None, result: HistoricalResult) -> str:
        p = parent_id or ""
        return f"{p}:{result.insights.date_start}:{result.insights.date_stop}"
