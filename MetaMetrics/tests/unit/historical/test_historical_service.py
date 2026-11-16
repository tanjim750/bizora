"""Tests for the HistoricalService.

Ported from ``tests/Unit/Historical/HistoricalServiceTest.php``.
"""

from __future__ import annotations

from typing import Any

import pytest

from metametrics.client import Response
from metametrics.config import MetaConfig
from metametrics.exceptions import (
    AuthenticationError,
    InvalidInputError,
    NetworkError,
    PermissionDeniedError,
    RateLimitError,
    UnexpectedResponseError,
)
from metametrics.historical.level import HistoricalLevel
from metametrics.historical.query import HistoricalQuery
from metametrics.historical.service import HistoricalService
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.filter_fields import InsightsFilterField
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.service import InsightsService
from metametrics.query.filters import Filter, FilterOperator
from tests.support.fakes import FakeMetaClient
from tests.support.fixtures import load_meta_fixture


def _range() -> DateRange:
    return DateRange("2026-09-01", "2026-09-24")


def _service(client: FakeMetaClient) -> HistoricalService:
    config = MetaConfig("historical-secret", "act_123", "v26.0")
    return HistoricalService(InsightsService(client, config))


def _campaign_row(
    date: str,
    spend: str,
    impressions: str,
    id: str = "campaign-1",
) -> dict[str, Any]:
    return {
        "campaign_id": id,
        "campaign_name": "Campaign",
        "account_currency": "USD",
        "date_start": date,
        "date_stop": date,
        "spend": spend,
        "impressions": impressions,
        "reach": impressions,
    }


def test_aggregate_discovery_uses_insights_evidence_and_requested_metrics() -> None:
    rows = load_meta_fixture("historical_campaigns")
    client = FakeMetaClient(Response(200, {"data": rows}))
    query = HistoricalQuery(
        level=HistoricalLevel.CAMPAIGN,
        date_range=_range(),
        metrics=[Metric.ROAS],
        filters=[
            Filter(
                InsightsFilterField.CAMPAIGN_ID.value,
                FilterOperator.IN,
                ("campaign-before-range", "campaign-created-in-range"),
            )
        ],
        limit=100,
    )

    results = _service(client).get(query)

    assert [r.entity_id for r in results] == ["campaign-before-range", "campaign-created-in-range"]
    assert results[0].insights.roas == 2.0
    assert results[0].currency == "USD"
    assert results[0].requested_since == "2026-09-01"
    assert results[0].requested_until == "2026-09-24"
    assert results[0].delivery_evidence.indicators() == {
        "impressions": 10000.0,
        "spend": 500.0,
        "reach": 8000.0,
    }

    assert len(client.requests) == 1
    req = client.last_request
    assert req.path == "/v26.0/act_123/insights"
    assert req.query["level"] == "campaign"
    expected_fields = (
        "campaign_id,campaign_name,date_start,date_stop,account_currency,spend,"
        "actions,cost_per_action_type,impressions,reach,action_values"
    )
    assert req.query["fields"] == expected_fields
    assert "time_increment" not in req.query
    assert req.query["limit"] == 100
    assert "status" not in str(req.query["fields"])
    assert "created_time" not in str(req.query["fields"])


def test_empty_insights_are_a_valid_empty_historical_result() -> None:
    client = FakeMetaClient(Response(200, {"data": []}))
    assert _service(client).campaigns(_range()) == []


def test_daily_discovery_does_not_fill_gaps_or_infer_continuous_delivery() -> None:
    client = FakeMetaClient(
        Response(
            200,
            {
                "data": [
                    _campaign_row("2026-09-01", "10", "100"),
                    _campaign_row("2026-09-03", "0", "0"),
                ]
            },
        )
    )
    query = HistoricalQuery(
        HistoricalLevel.CAMPAIGN,
        DateRange("2026-09-01", "2026-09-03"),
        daily=True,
    )

    results = _service(client).get(query)

    assert len(results) == 1
    assert results[0].insights.date_start == "2026-09-01"
    assert results[0].requested_until == "2026-09-03"
    assert client.last_request.query["time_increment"] == 1


def test_ad_set_discovery_preserves_campaign_relationship_and_uses_parent_scope() -> None:
    client = FakeMetaClient(
        Response(
            200,
            {
                "data": [
                    {
                        "campaign_id": "campaign-1",
                        "adset_id": "adset-1",
                        "adset_name": "Ad Set",
                        "account_currency": "USD",
                        "date_start": "2026-09-01",
                        "date_stop": "2026-09-24",
                        "spend": "5",
                        "impressions": "50",
                        "reach": "40",
                    }
                ]
            },
        )
    )

    results = _service(client).ad_sets(_range(), "campaign-1")

    assert len(results) == 1
    assert results[0].campaign_id == "campaign-1"
    assert results[0].ad_set_id == "adset-1"
    assert client.last_request.path == "/v26.0/campaign-1/insights"
    assert len(client.requests) == 1
    assert results[0].insights.raw_data.optimization_goal is None


def test_ad_discovery_preserves_all_relationships() -> None:
    client = FakeMetaClient(
        Response(
            200,
            {
                "data": [
                    {
                        "campaign_id": "campaign-1",
                        "adset_id": "adset-1",
                        "ad_id": "ad-1",
                        "ad_name": "Ad",
                        "account_currency": "USD",
                        "date_start": "2026-09-01",
                        "date_stop": "2026-09-24",
                        "spend": "2",
                        "impressions": "20",
                        "reach": "15",
                    }
                ]
            },
        )
    )

    results = _service(client).ads(_range(), "adset-1")

    assert results[0].campaign_id == "campaign-1"
    assert results[0].ad_set_id == "adset-1"
    assert results[0].ad_id == "ad-1"
    assert client.last_request.path == "/v26.0/adset-1/insights"


def test_all_paginated_rows_are_evaluated() -> None:
    client = FakeMetaClient(
        Response(
            200,
            {
                "data": [_campaign_row("2026-09-01", "1", "10", "campaign-1")],
                "paging": {
                    "cursors": {"after": "page-2"},
                    "next": "https://graph.facebook.com/next",
                },
            },
        ),
        Response(
            200,
            {
                "data": [_campaign_row("2026-09-01", "2", "20", "campaign-2")],
            },
        ),
    )

    results = _service(client).campaigns(_range())

    assert [r.entity_id for r in results] == ["campaign-1", "campaign-2"]
    assert client.requests[1].query["after"] == "page-2"


@pytest.mark.parametrize(
    ("status", "code", "expected_exception"),
    [
        (401, 190, AuthenticationError),
        (403, 200, PermissionDeniedError),
        (429, 4, RateLimitError),
    ],
)
def test_api_failures_are_not_reinterpreted_as_empty_history(
    status: int,
    code: int,
    expected_exception: type[Exception],
) -> None:
    token = "historical-secret"
    client = FakeMetaClient(
        Response(
            status,
            {"error": {"message": f"Unsafe upstream message {token}", "code": code}},
        )
    )

    with pytest.raises(expected_exception) as exc_info:
        _service(client).campaigns(_range())

    assert token not in str(exc_info.value)


def test_mid_pagination_failure_does_not_return_partial_results() -> None:
    client = FakeMetaClient(
        Response(
            200,
            {
                "data": [_campaign_row("2026-09-01", "1", "10")],
                "paging": {
                    "cursors": {"after": "page-2"},
                    "next": "https://graph.facebook.com/next",
                },
            },
        ),
        NetworkError("Request failed."),
    )

    with pytest.raises(NetworkError):
        _service(client).campaigns(_range())


def test_invalid_parent_scope_fails_before_any_request() -> None:
    client = FakeMetaClient()

    with pytest.raises(InvalidInputError):
        _service(client).get(
            HistoricalQuery(
                HistoricalLevel.AD_SET,
                _range(),
                parent_id=" ",
            )
        )

    assert client.requests == []


def test_invalid_date_range_fails_before_any_request() -> None:
    client = FakeMetaClient()

    with pytest.raises(InvalidInputError):
        _service(client).campaigns(DateRange("2026-09-24", "2026-09-01"))

    assert client.requests == []


def test_missing_delivery_metrics_are_reported_as_insufficient_evidence() -> None:
    client = FakeMetaClient(
        Response(
            200,
            {
                "data": [
                    {
                        "campaign_id": "campaign-1",
                        "campaign_name": "Campaign",
                        "account_currency": "USD",
                        "date_start": "2026-09-01",
                        "date_stop": "2026-09-24",
                    }
                ]
            },
        )
    )

    with pytest.raises(UnexpectedResponseError, match="insufficient delivery evidence"):
        _service(client).campaigns(_range())


def test_daily_response_keeps_currency_outside_its_rows() -> None:
    client = FakeMetaClient(
        Response(
            200,
            {
                "data": [
                    _campaign_row("2026-09-01", "10", "100"),
                    _campaign_row("2026-09-02", "20", "200"),
                ]
            },
        )
    )
    response = _service(client).get_response(
        HistoricalQuery(HistoricalLevel.CAMPAIGN, _range(), daily=True)
    )
    dumped = response.to_dict()

    assert response.currency == "USD"
    assert dumped["level"] == "campaign"
    assert dumped["currency"] == "USD"
    assert len(dumped["data"]) == 2
    assert "currency" not in dumped["data"][0]
    assert "currency" not in dumped["data"][1]
    assert dumped["data"][0]["spend"] == 10.0
    assert len(client.requests) == 1


def test_filtered_out_delivery_still_preserves_insights_currency() -> None:
    row = _campaign_row("2026-09-01", "0", "0")
    row["account_currency"] = "BDT"
    client = FakeMetaClient(Response(200, {"data": [row]}))
    response = _service(client).get_response(HistoricalQuery(HistoricalLevel.CAMPAIGN, _range()))

    assert response.currency == "BDT"
    assert response.data == ()
    assert len(client.requests) == 1


def test_empty_response_resolves_currency_once() -> None:
    client = FakeMetaClient(
        Response(200, {"data": []}),
        Response(200, {"id": "act_123", "currency": "EUR"}),
    )

    response = _service(client).get_response(HistoricalQuery(HistoricalLevel.CAMPAIGN, _range()))

    assert response.to_dict() == {"level": "campaign", "currency": "EUR", "data": []}
    assert len(client.requests) == 2
