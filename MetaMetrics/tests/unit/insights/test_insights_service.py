"""Tests for the Insights service.

Ported from ``tests/Unit/Insights/InsightsServiceTest.php``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from metametrics.client import Response
from metametrics.config import MetaConfig
from metametrics.exceptions import (
    AuthenticationError,
    InvalidInputError,
    PermissionDeniedError,
    RateLimitError,
    ResourceNotFoundError,
    UnexpectedResponseError,
    UnsupportedMetricError,
)
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.filter_fields import InsightsFilterField
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.query import InsightsQuery
from metametrics.insights.service import InsightsService
from metametrics.query.filters import Filter, FilterOperator
from tests.support.fakes import FakeMetaClient

TOKEN = "insights-secret-token"


def make_service(client: FakeMetaClient) -> InsightsService:
    config = MetaConfig(access_token=TOKEN, ad_account_id="act_123456789", api_version="v26.0")

    return InsightsService(client, config)


def account_query(daily: bool = False) -> InsightsQuery:
    return InsightsQuery(
        level=InsightsLevel.ACCOUNT,
        date_range=DateRange("2026-09-01", "2026-09-24"),
        metrics=[Metric.SPEND],
        daily=daily,
    )


def account_row(date: str, spend: str) -> dict[str, Any]:
    return {
        "account_id": "123456789",
        "account_name": "Test Account",
        "account_currency": "USD",
        "date_start": date,
        "date_stop": date,
        "spend": spend,
    }


def collection(*rows: dict[str, Any]) -> Response:
    return Response(status_code=200, body={"data": list(rows)})


def test_it_builds_one_paginated_daily_campaign_request() -> None:
    client = FakeMetaClient(
        collection(
            {
                "campaign_id": "campaign-1",
                "campaign_name": "September Sales",
                "account_currency": "USD",
                "date_start": "2026-09-01",
                "date_stop": "2026-09-01",
                "spend": "100",
                "actions": [{"action_type": "link_click", "value": "20"}],
                "cost_per_action_type": [{"action_type": "link_click", "value": "5"}],
                "action_values": [{"action_type": "omni_purchase", "value": "300"}],
                "clicks": "20",
                "impressions": "1000",
            }
        )
    )
    query = InsightsQuery(
        level=InsightsLevel.CAMPAIGN,
        date_range=DateRange("2026-09-01", "2026-09-24"),
        metrics=[Metric.ROAS, Metric.CTR],
        daily=True,
        filters=[Filter(InsightsFilterField.CAMPAIGN_ID.value, FilterOperator.IN, ("campaign-1",))],
        limit=50,
    )

    results = make_service(client).get(query)

    assert len(results) == 1
    assert results[0].currency == "USD"
    assert results[0].to_dict()["currency"] == "USD"
    assert client.request_count == 1
    assert results[0].roas == 3.0
    assert results[0].ctr == 2.0
    assert results[0].has_metric(Metric.SPEND) is False
    assert results[0].raw_data.spend == "100"
    assert results[0].raw_data.actions == [{"action_type": "link_click", "value": "20"}]
    assert results[0].raw_data.cost_per_action_type == [{"action_type": "link_click", "value": "5"}]

    request = client.last_request
    assert request.path == "/v26.0/act_123456789/insights"
    assert request.query == {
        "fields": (
            "campaign_id,campaign_name,date_start,date_stop,account_currency,"
            "spend,actions,cost_per_action_type,action_values,clicks,impressions"
        ),
        "level": "campaign",
        "time_range": '{"since":"2026-09-01","until":"2026-09-24"}',
        "time_increment": 1,
        "filtering": '[{"field":"campaign.id","operator":"IN","value":["campaign-1"]}]',
        "limit": 50,
    }


def test_it_uses_an_explicit_entity_scope_without_changing_the_level() -> None:
    client = FakeMetaClient(collection())
    query = InsightsQuery(
        level=InsightsLevel.AD_SET,
        date_range=DateRange("2026-09-01", "2026-09-24"),
        metrics=[Metric.SPEND],
        entity_id="campaign-1",
    )

    make_service(client).get(query)

    request = client.last_request
    assert request.path == "/v26.0/campaign-1/insights"
    assert request.query["level"] == "adset"
    assert "time_increment" not in request.query


def test_ad_set_insights_include_the_configuration_without_assuming_a_custom_event_type() -> None:
    promoted_object = {
        "custom_conversion_id": "conversion-123",
        "pixel_id": "pixel-456",
        "application_id": "application-789",
    }
    client = FakeMetaClient(
        collection(
            {
                "campaign_id": "campaign-1",
                "adset_id": "adset-1",
                "adset_name": "Conversions",
                "account_currency": "USD",
                "date_start": "2026-09-01",
                "date_stop": "2026-09-24",
                "spend": "250.50",
                "actions": [{"action_type": "offsite_conversion.fb_pixel_purchase", "value": "5"}],
                "cost_per_action_type": [
                    {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "50.10"}
                ],
            }
        ),
        Response(
            status_code=200,
            body={
                "id": "adset-1",
                "optimization_goal": "OFFSITE_CONVERSIONS",
                "promoted_object": promoted_object,
            },
        ),
    )
    query = InsightsQuery(
        level=InsightsLevel.AD_SET,
        date_range=DateRange("2026-09-01", "2026-09-24"),
        metrics=[Metric.SPEND],
    )

    result = make_service(client).get(query)[0]

    assert result.raw_data.spend == "250.50"
    assert result.raw_data.optimization_goal == "OFFSITE_CONVERSIONS"
    assert result.raw_data.promoted_object == promoted_object
    assert "custom_event_type" not in (result.raw_data.promoted_object or {})
    assert result.raw_data.cost_per_action_type == [
        {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "50.10"}
    ]

    assert client.request_count == 2
    assert client.requests[1].path == "/v26.0/adset-1"
    assert client.requests[1].query == {"fields": "id,optimization_goal,promoted_object"}


def test_empty_insights_are_successful() -> None:
    client = FakeMetaClient(collection())

    assert make_service(client).get(account_query()) == []


def test_it_uses_the_shared_cursor_pagination() -> None:
    client = FakeMetaClient(
        Response(
            status_code=200,
            body={
                "data": [account_row("2026-09-01", "10")],
                "paging": {"cursors": {"after": "next-page"}, "next": "https://graph.facebook.com/next"},
            },
        ),
        collection(account_row("2026-09-02", "20")),
    )

    results = make_service(client).get(account_query(daily=True))

    assert len(results) == 2
    assert [result.spend for result in results] == [10.0, 20.0]
    assert client.requests[1].query["after"] == "next-page"
    assert [row.currency for row in results] == ["USD", "USD"]


def test_the_response_serialises_the_currency_once_for_daily_rows() -> None:
    client = FakeMetaClient(collection(account_row("2026-09-01", "10"), account_row("2026-09-02", "20")))

    response = make_service(client).get_response(account_query(daily=True))
    payload = json.loads(json.dumps(response.to_dict()))

    assert response.currency == "USD"
    assert payload["level"] == "account"
    assert payload["currency"] == "USD"
    assert [row["spend"] for row in response.to_dict()["data"]] == [10.0, 20.0]
    assert "currency" not in payload["data"][0]
    assert "currency" not in payload["data"][1]
    assert client.request_count == 1


def test_a_missing_currency_uses_one_account_request_for_the_whole_response() -> None:
    rows = [account_row("2026-09-01", "10"), account_row("2026-09-02", "20")]
    for row in rows:
        del row["account_currency"]

    client = FakeMetaClient(
        collection(*rows),
        Response(status_code=200, body={"id": "act_123456789", "currency": "BDT"}),
    )

    response = make_service(client).get_response(account_query(daily=True))

    assert response.currency == "BDT"
    assert [row.currency for row in response.data] == ["BDT", "BDT"]
    assert client.request_count == 2
    assert client.requests[1].path == "/v26.0/act_123456789"
    assert client.requests[1].query == {"fields": "currency"}


def test_a_missing_currency_can_use_another_row_without_an_account_request() -> None:
    row = account_row("2026-09-01", "10")
    del row["account_currency"]

    client = FakeMetaClient(collection(row, account_row("2026-09-02", "20")))

    response = make_service(client).get_response(account_query(daily=True))

    assert response.data[0].currency == "USD"
    assert client.request_count == 1


def test_an_empty_response_still_has_the_configured_currency() -> None:
    client = FakeMetaClient(
        collection(),
        Response(status_code=200, body={"id": "act_123456789", "currency": "EUR"}),
    )

    assert make_service(client).get_response(account_query()).to_dict() == {
        "level": "account",
        "currency": "EUR",
        "data": [],
    }
    assert client.request_count == 2


@pytest.mark.parametrize(
    "currency",
    [None, "", "usd", 123, ["USD"], "USDX"],
    ids=["null", "empty", "lowercase", "number", "array", "long"],
)
def test_a_malformed_currency_is_not_hidden_by_the_fallback(currency: object) -> None:
    row = account_row("2026-09-01", "10")
    row["account_currency"] = currency

    client = FakeMetaClient(collection(row))

    with pytest.raises(UnexpectedResponseError, match="account_currency"):
        make_service(client).get_response(account_query())


def test_conflicting_currencies_across_pages_are_rejected() -> None:
    row = account_row("2026-09-02", "20")
    row["account_currency"] = "EUR"

    client = FakeMetaClient(
        Response(
            status_code=200,
            body={
                "data": [account_row("2026-09-01", "10")],
                "paging": {"cursors": {"after": "page-2"}, "next": "https://graph.facebook.com/next"},
            },
        ),
        collection(row),
    )

    with pytest.raises(UnexpectedResponseError, match="conflicting"):
        make_service(client).get_response(account_query(daily=True))


def test_the_currency_fallback_preserves_mapped_api_errors() -> None:
    row = account_row("2026-09-01", "10")
    del row["account_currency"]

    client = FakeMetaClient(
        collection(row),
        Response(status_code=403, body={"error": {"code": 200, "message": "Permission denied"}}),
    )

    with pytest.raises(PermissionDeniedError):
        make_service(client).get(account_query())


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        (401, 190, AuthenticationError),
        (403, 200, PermissionDeniedError),
        (429, 4, RateLimitError),
        (404, 100, ResourceNotFoundError),
    ],
    ids=["authentication", "permission", "rate limit", "resource not found"],
)
def test_it_maps_meta_errors(status: int, code: int, expected: type[Exception]) -> None:
    client = FakeMetaClient(
        Response(
            status_code=status,
            body={
                "error": {
                    "message": f"Unsafe upstream message {TOKEN}",
                    "type": "OAuthException",
                    "code": code,
                    "fbtrace_id": "trace-id",
                }
            },
        )
    )

    with pytest.raises(expected) as error:
        make_service(client).get(account_query())

    assert TOKEN not in error.value.message
    assert TOKEN not in repr(error.value.to_dict())


def test_it_rejects_malformed_responses() -> None:
    client = FakeMetaClient(Response(status_code=200, body={"data": "invalid"}))

    with pytest.raises(UnexpectedResponseError):
        make_service(client).get(account_query())


def test_invalid_queries_fail_before_a_network_request() -> None:
    client = FakeMetaClient()

    with pytest.raises(InvalidInputError):
        InsightsQuery(
            level=InsightsLevel.ACCOUNT,
            date_range=DateRange("2026-09-01", "2026-09-24"),
            metrics=[Metric.SPEND],
            entity_id=" ",
        )

    assert client.request_count == 0


def test_unsupported_metrics_fail_before_a_network_request() -> None:
    client = FakeMetaClient()

    with pytest.raises(UnsupportedMetricError):
        InsightsQuery(
            level=InsightsLevel.ACCOUNT,
            date_range=DateRange("2026-09-01", "2026-09-24"),
            metrics=["profit"],  # type: ignore[list-item]
        )

    assert client.request_count == 0


def test_unsupported_filter_fields_fail_before_a_network_request() -> None:
    client = FakeMetaClient()
    query = InsightsQuery(
        level=InsightsLevel.CAMPAIGN,
        date_range=DateRange("2026-09-01", "2026-09-24"),
        metrics=[Metric.SPEND],
        filters=[Filter("account.currency", FilterOperator.EQUAL, "BDT")],
    )

    with pytest.raises(InvalidInputError):
        make_service(client).get(query)

    assert client.request_count == 0


def test_a_query_requires_at_least_one_metric() -> None:
    with pytest.raises(InvalidInputError, match="At least one Insights metric"):
        InsightsQuery(
            level=InsightsLevel.ACCOUNT,
            date_range=DateRange("2026-09-01", "2026-09-24"),
            metrics=[],
        )
