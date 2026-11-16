"""Tests for the Campaign service.

Ported from ``tests/Unit/Campaign/CampaignServiceTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.campaign.query import CampaignQuery
from metametrics.campaign.service import CampaignService
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


def campaign_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "1200000000000001",
        "name": "Prospecting",
        "status": "ACTIVE",
        "configured_status": "ACTIVE",
        "effective_status": "ACTIVE",
        "objective": "OUTCOME_SALES",
        "created_time": "2026-08-10T00:00:00+0000",
        "updated_time": "2026-09-01T10:30:00+0000",
    }
    body.update(overrides)
    return body


def collection_response(*items: dict[str, object]) -> Response:
    return Response(status_code=200, body={"data": list(items)})


def test_it_lists_campaigns() -> None:
    client = FakeMetaClient(collection_response(campaign_body()))

    campaigns = CampaignService(client, make_config()).all()

    assert len(campaigns) == 1
    assert campaigns[0].id == "1200000000000001"
    assert campaigns[0].name == "Prospecting"
    assert campaigns[0].objective == "OUTCOME_SALES"
    assert campaigns[0].created_time is not None
    assert campaigns[0].created_time.tzinfo is not None


def test_it_normalises_timestamps_to_utc() -> None:
    client = FakeMetaClient(collection_response(campaign_body(created_time="2026-08-10T02:00:00+02:00")))

    campaigns = CampaignService(client, make_config()).all()

    assert campaigns[0].created_time is not None
    assert campaigns[0].created_time.hour == 0
    assert campaigns[0].created_time.utcoffset().total_seconds() == 0


def test_it_applies_query_parameters() -> None:
    client = FakeMetaClient(collection_response())

    CampaignService(client, make_config()).all(
        CampaignQuery(
            fields=Fields(["name"]),
            effective_statuses=("ACTIVE", "PAUSED", "ACTIVE"),
            completed=True,
            limit=50,
        )
    )

    request = client.last_request
    assert request.path == "/v23.0/act_123456789/campaigns"
    assert request.query["fields"] == "id,name"
    assert request.query["effective_status"] == '["ACTIVE","PAUSED"]'
    assert request.query["is_completed"] is True
    assert request.query["limit"] == 50


def test_it_rejects_unsupported_effective_statuses() -> None:
    with pytest.raises(InvalidInputError, match="Unsupported Campaign effective status"):
        CampaignQuery(effective_statuses=("NOPE",))


def test_it_rejects_a_non_positive_limit() -> None:
    with pytest.raises(InvalidInputError, match="limit must be greater than zero"):
        CampaignQuery(limit=0)


def test_it_rejects_unsupported_fields() -> None:
    client = FakeMetaClient(collection_response())

    with pytest.raises(InvalidInputError, match="Unsupported normalized Campaign field"):
        CampaignService(client, make_config()).all(CampaignQuery(fields=Fields(["budget"])))


def test_it_finds_a_single_campaign() -> None:
    client = FakeMetaClient(Response(status_code=200, body=campaign_body()))

    campaign = CampaignService(client, make_config()).find("1200000000000001")

    assert campaign.id == "1200000000000001"
    assert client.last_request.path == "/v23.0/1200000000000001"


def test_it_rejects_an_empty_campaign_id() -> None:
    client = FakeMetaClient()

    with pytest.raises(InvalidInputError, match="Campaign ID must not be empty"):
        CampaignService(client, make_config()).find("  ")


def test_it_rejects_a_malformed_campaign_response() -> None:
    client = FakeMetaClient(Response(status_code=200, body=["not", "an", "object"]))

    with pytest.raises(UnexpectedResponseError, match="malformed Campaign response"):
        CampaignService(client, make_config()).find("1200000000000001")


def test_it_maps_permission_errors() -> None:
    client = FakeMetaClient(error_response(403, code=200, error_type="OAuthException"))

    with pytest.raises(PermissionDeniedError):
        CampaignService(client, make_config()).find("1200000000000001")


def test_it_maps_missing_campaigns() -> None:
    client = FakeMetaClient(error_response(404, code=803, error_type="GraphMethodException"))

    with pytest.raises(ResourceNotFoundError) as error:
        CampaignService(client, make_config()).find("1200000000000001")

    assert error.value.resource_type == "Campaign"
    assert error.value.resource_id == "1200000000000001"


def test_it_produces_the_golden_requests() -> None:
    golden = load_request_fixture("entities")["campaign"]

    client = FakeMetaClient(
        collection_response(),
        collection_response(),
        Response(status_code=200, body=campaign_body()),
    )
    service = CampaignService(client, make_config())

    service.all()
    service.all(
        CampaignQuery(
            fields=Fields(["name"]),
            effective_statuses=("ACTIVE", "PAUSED"),
            completed=True,
            limit=50,
        )
    )
    service.find("1200000000000001")

    for case, request in zip(golden.values(), client.requests, strict=True):
        assert request.method == case["method"]
        assert request.path == case["path"]
        assert request.query == case["query"]
        assert encode_query(request.query) == case["encoded_query"]
