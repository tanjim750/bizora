"""Tests for HierarchyService and HierarchyNode.

Ported from ``tests/Unit/Hierarchy/HierarchyServiceTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.client import Response
from metametrics.config import MetaConfig
from metametrics.exceptions import InvalidInputError
from metametrics.hierarchy.node import HierarchyNode
from metametrics.hierarchy.service import HierarchyService
from metametrics.historical.delivery import DeliveryEvidence
from metametrics.historical.level import HistoricalLevel
from metametrics.historical.result import HistoricalResult
from metametrics.historical.service import HistoricalService
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.raw_data import InsightsRawData
from metametrics.insights.service import InsightsService
from tests.support.fakes import FakeMetaClient
from tests.support.fixtures import load_meta_fixture


def test_it_builds_historical_hierarchy_from_independent_level_evidence() -> None:
    fixture = load_meta_fixture("historical_hierarchy")
    client = FakeMetaClient(
        Response(200, {"data": fixture["campaigns"]}),
        Response(200, {"data": fixture["adsets"]}),
        Response(200, {"data": fixture["ads"]}),
    )
    config = MetaConfig("hierarchy-secret", "act_123", "v26.0")
    service = HierarchyService(HistoricalService(InsightsService(client, config)))

    result = service.historical(DateRange("2026-09-01", "2026-09-24"))

    assert len(result.campaigns) == 1
    assert result.currency == "USD"
    serialized = result.to_dict()
    assert serialized["currency"] == "USD"
    assert "currency" not in serialized["campaigns"][0]
    assert "currency" not in serialized["campaigns"][0]["children"][0]
    assert "currency" not in serialized["campaigns"][0]["children"][0]["children"][0]
    assert serialized == result.json_serialize()

    assert result.campaigns[0].entity_id == "campaign-1"
    assert len(result.campaigns[0].children) == 1
    assert result.campaigns[0].children[0].entity_id == "adset-1"
    assert len(result.campaigns[0].children[0].children) == 1
    assert result.campaigns[0].children[0].children[0].entity_id == "ad-1"

    assert [node.entity_id for node in result.unattached_ad_sets] == [
        "adset-without-delivered-campaign"
    ]
    assert [node.entity_id for node in result.unattached_ads] == [
        "ad-without-delivered-adset"
    ]

    assert len(client.requests) == 3
    assert [req.query["level"] for req in client.requests] == ["campaign", "adset", "ad"]


def test_mixed_currencies_across_levels_are_rejected() -> None:
    fixture = load_meta_fixture("historical_hierarchy")
    # Mutate ads currency to EUR
    ads = []
    for row in fixture["ads"]:
        mutated = dict(row)
        mutated["account_currency"] = "EUR"
        ads.append(mutated)

    client = FakeMetaClient(
        Response(200, {"data": fixture["campaigns"]}),
        Response(200, {"data": fixture["adsets"]}),
        Response(200, {"data": ads}),
    )
    service = HierarchyService(
        HistoricalService(
            InsightsService(client, MetaConfig("hierarchy-secret", "act_123", "v26.0"))
        )
    )

    with pytest.raises(InvalidInputError, match="currency"):
        service.historical(DateRange("2026-09-01", "2026-09-24"))


def test_empty_hierarchy_resolves_currency_only_once() -> None:
    client = FakeMetaClient(
        Response(200, {"data": []}),
        Response(200, {"id": "act_123", "currency": "BDT"}),
        Response(200, {"data": []}),
        Response(200, {"data": []}),
    )
    service = HierarchyService(
        HistoricalService(
            InsightsService(client, MetaConfig("hierarchy-secret", "act_123", "v26.0"))
        )
    )

    response = service.historical(DateRange("2026-09-01", "2026-09-24"))

    assert response.currency == "BDT"
    assert response.campaigns == ()
    assert len(client.requests) == 4


def test_hierarchy_node_validation() -> None:
    range_ = DateRange("2026-09-01", "2026-09-24")

    def make_res(
        entity_id: str,
        level: InsightsLevel,
        campaign_id: str | None,
        ad_set_id: str | None,
    ) -> HistoricalResult:
        insights = InsightsDTO(
            entity_id=entity_id,
            entity_name=entity_id,
            level=level,
            campaign_id=campaign_id,
            ad_set_id=ad_set_id,
            ad_id=entity_id if level == InsightsLevel.AD else None,
            date_range=range_,
            metrics={Metric.SPEND.value: 10.0},
            raw_data=InsightsRawData(None, None, None, None, None),
        )
        return HistoricalResult(range_, DeliveryEvidence({"spend": 10.0}), insights)

    camp_res = make_res("camp-1", InsightsLevel.CAMPAIGN, "camp-1", None)
    adset_res = make_res("adset-1", InsightsLevel.AD_SET, "camp-1", "adset-1")
    ad_res = make_res("ad-1", InsightsLevel.AD, "camp-1", "adset-1")

    ad_node = HierarchyNode(ad_res)
    adset_node = HierarchyNode(adset_res, [ad_node])
    camp_node = HierarchyNode(camp_res, [adset_node])

    assert camp_node.entity_id == "camp-1"
    assert camp_node.level == HistoricalLevel.CAMPAIGN
    assert len(camp_node.children) == 1

    # Mismatch child parent ID
    mismatched_adset = make_res("adset-2", InsightsLevel.AD_SET, "camp-OTHER", "adset-2")
    with pytest.raises(InvalidInputError, match="reporting period"):
        HierarchyNode(camp_res, [HierarchyNode(mismatched_adset)])
