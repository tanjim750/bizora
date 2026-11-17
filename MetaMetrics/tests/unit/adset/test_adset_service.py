"""Tests for the Ad Set service.

Ported from ``tests/Unit/AdSet/AdSetServiceTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.adset.query import AdSetQuery
from metametrics.adset.service import AdSetService
from metametrics.client import Response, encode_query
from metametrics.config import MetaConfig
from metametrics.exceptions import (
    InvalidInputError,
    PermissionDeniedError,
    ResourceNotFoundError,
    UnexpectedResponseError,
)
from metametrics.query.fields import Fields
from tests.support.fakes import FakeMetaClient, error_response
from tests.support.fixtures import load_request_fixture


def make_config() -> MetaConfig:
    return MetaConfig(access_token="test-token", ad_account_id="act_123456789", api_version="v23.0")


def ad_set_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "1200000000000002",
        "name": "Lookalike 1%",
        "campaign_id": "1200000000000001",
        "status": "ACTIVE",
        "configured_status": "ACTIVE",
        "effective_status": "ACTIVE",
        "optimization_goal": "OFFSITE_CONVERSIONS",
        "billing_event": "IMPRESSIONS",
        "daily_budget": "5000",
        "lifetime_budget": "100000",
        "created_time": "2026-08-10T00:00:00+0000",
        "updated_time": "2026-09-01T10:30:00+0000",
        "start_time": "2026-08-11T00:00:00+0000",
        "end_time": "2026-10-01T00:00:00+0000",
    }
    body.update(overrides)
    return body


def collection_response(*items: dict[str, object]) -> Response:
    return Response(status_code=200, body={"data": list(items)})


def test_it_lists_ad_sets() -> None:
    client = FakeMetaClient(collection_response(ad_set_body()))

    ad_sets = AdSetService(client, make_config()).all()

    assert len(ad_sets) == 1
    assert ad_sets[0].id == "1200000000000002"
    assert ad_sets[0].campaign_id == "1200000000000001"
    assert ad_sets[0].optimization_goal == "OFFSITE_CONVERSIONS"
    assert ad_sets[0].billing_event == "IMPRESSIONS"
    assert ad_sets[0].daily_budget == "5000"
    assert ad_sets[0].lifetime_budget == "100000"
    assert ad_sets[0].start_time is not None
    assert ad_sets[0].end_time is not None


def test_it_lists_ad_sets_for_a_campaign() -> None:
    client = FakeMetaClient(collection_response())

    AdSetService(client, make_config()).for_campaign("1200000000000001")

    assert client.last_request.path == "/v23.0/1200000000000001/adsets"


def test_it_rejects_an_empty_campaign_id() -> None:
    client = FakeMetaClient()

    with pytest.raises(InvalidInputError, match="Campaign ID must not be empty"):
        AdSetService(client, make_config()).for_campaign("")


def test_it_applies_query_parameters() -> None:
    client = FakeMetaClient(collection_response())

    AdSetService(client, make_config()).all(
        AdSetQuery(
            fields=Fields(["name"]),
            effective_statuses=("ACTIVE",),
            completed=False,
            limit=25,
        )
    )

    request = client.last_request
    assert request.query["fields"] == "id,name,campaign_id"
    assert request.query["effective_status"] == '["ACTIVE"]'
    assert request.query["is_completed"] is False
    assert request.query["limit"] == 25


def test_it_rejects_unsupported_effective_statuses() -> None:
    with pytest.raises(InvalidInputError, match="Unsupported Ad Set effective status"):
        AdSetQuery(effective_statuses=("NOPE",))


def test_it_rejects_unsupported_fields() -> None:
    client = FakeMetaClient(collection_response())

    with pytest.raises(InvalidInputError, match="Unsupported normalized Ad Set field"):
        AdSetService(client, make_config()).all(AdSetQuery(fields=Fields(["budget"])))


def test_it_finds_a_single_ad_set() -> None:
    client = FakeMetaClient(Response(status_code=200, body=ad_set_body()))

    ad_set = AdSetService(client, make_config()).find("1200000000000002")

    assert ad_set.id == "1200000000000002"
    assert client.last_request.path == "/v23.0/1200000000000002"


def test_it_rejects_an_empty_ad_set_id() -> None:
    client = FakeMetaClient()

    with pytest.raises(InvalidInputError, match="Ad Set ID must not be empty"):
        AdSetService(client, make_config()).find("  ")


def test_it_rejects_a_malformed_ad_set_response() -> None:
    client = FakeMetaClient(Response(status_code=200, body="not-an-object"))

    with pytest.raises(UnexpectedResponseError, match="malformed Ad Set response"):
        AdSetService(client, make_config()).find("1200000000000002")


def test_it_maps_permission_errors() -> None:
    client = FakeMetaClient(error_response(403, code=200, error_type="OAuthException"))

    with pytest.raises(PermissionDeniedError):
        AdSetService(client, make_config()).find("1200000000000002")


def test_it_maps_missing_ad_sets() -> None:
    client = FakeMetaClient(error_response(404, code=803, error_type="GraphMethodException"))

    with pytest.raises(ResourceNotFoundError) as error:
        AdSetService(client, make_config()).find("1200000000000002")

    assert error.value.resource_type == "Ad Set"
    assert error.value.resource_id == "1200000000000002"


def test_it_produces_the_golden_requests() -> None:
    golden = load_request_fixture("entities")["ad_set"]

    client = FakeMetaClient(collection_response(), collection_response())
    service = AdSetService(client, make_config())

    service.all()
    service.for_campaign("1200000000000001", AdSetQuery(fields=Fields(["name", "campaign_id"])))

    for case, request in zip(golden.values(), client.requests, strict=True):
        assert request.method == case["method"]
        assert request.path == case["path"]
        assert request.query == case["query"]
        assert encode_query(request.query) == case["encoded_query"]
