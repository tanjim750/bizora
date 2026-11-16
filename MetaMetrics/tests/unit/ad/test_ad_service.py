"""Tests for the Ad service.

Ported from ``tests/Unit/Ad/AdServiceTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.ad.query import AdQuery
from metametrics.ad.service import AdService
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


def ad_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "1200000000000003",
        "name": "Creative One",
        "adset_id": "1200000000000002",
        "campaign_id": "1200000000000001",
        "status": "ACTIVE",
        "configured_status": "ACTIVE",
        "effective_status": "ACTIVE",
        "created_time": "2026-08-10T00:00:00+0000",
        "updated_time": "2026-09-01T10:30:00+0000",
    }
    body.update(overrides)
    return body


def collection_response(*items: dict[str, object]) -> Response:
    return Response(status_code=200, body={"data": list(items)})


def test_it_lists_ads() -> None:
    client = FakeMetaClient(collection_response(ad_body()))

    ads = AdService(client, make_config()).all()

    assert len(ads) == 1
    assert ads[0].id == "1200000000000003"
    assert ads[0].ad_set_id == "1200000000000002"
    assert ads[0].campaign_id == "1200000000000001"


def test_it_lists_ads_for_a_campaign() -> None:
    client = FakeMetaClient(collection_response())

    AdService(client, make_config()).for_campaign("1200000000000001")

    assert client.last_request.path == "/v23.0/1200000000000001/ads"


def test_it_lists_ads_for_an_ad_set() -> None:
    client = FakeMetaClient(collection_response())

    AdService(client, make_config()).for_ad_set("1200000000000002")

    assert client.last_request.path == "/v23.0/1200000000000002/ads"


@pytest.mark.parametrize(
    ("method", "label"),
    [("for_campaign", "Campaign"), ("for_ad_set", "Ad Set")],
)
def test_it_rejects_an_empty_parent_id(method: str, label: str) -> None:
    client = FakeMetaClient()
    service = AdService(client, make_config())

    with pytest.raises(InvalidInputError, match=f"{label} ID must not be empty"):
        getattr(service, method)("   ")


def test_it_applies_query_parameters() -> None:
    client = FakeMetaClient(collection_response())

    AdService(client, make_config()).all(
        AdQuery(fields=Fields(["name"]), effective_statuses=("ACTIVE",), limit=10)
    )

    request = client.last_request
    assert request.query["fields"] == "id,name,adset_id,campaign_id"
    assert request.query["effective_status"] == '["ACTIVE"]'
    assert request.query["limit"] == 10


def test_it_rejects_unsupported_effective_statuses() -> None:
    with pytest.raises(InvalidInputError, match="Unsupported Ad effective status"):
        AdQuery(effective_statuses=("NOPE",))


def test_it_rejects_unsupported_fields() -> None:
    client = FakeMetaClient(collection_response())

    with pytest.raises(InvalidInputError, match="Unsupported normalized Ad field"):
        AdService(client, make_config()).all(AdQuery(fields=Fields(["budget"])))


def test_it_finds_a_single_ad() -> None:
    client = FakeMetaClient(Response(status_code=200, body=ad_body()))

    ad = AdService(client, make_config()).find("1200000000000003")

    assert ad.id == "1200000000000003"
    assert client.last_request.path == "/v23.0/1200000000000003"


def test_it_rejects_an_empty_ad_id() -> None:
    client = FakeMetaClient()

    with pytest.raises(InvalidInputError, match="Ad ID must not be empty"):
        AdService(client, make_config()).find("  ")


def test_it_rejects_a_malformed_ad_response() -> None:
    client = FakeMetaClient(Response(status_code=200, body="not-an-object"))

    with pytest.raises(UnexpectedResponseError, match="malformed Ad response"):
        AdService(client, make_config()).find("1200000000000003")


def test_it_maps_permission_errors() -> None:
    client = FakeMetaClient(error_response(403, code=200, error_type="OAuthException"))

    with pytest.raises(PermissionDeniedError):
        AdService(client, make_config()).find("1200000000000003")


def test_it_maps_missing_ads() -> None:
    client = FakeMetaClient(error_response(404, code=803, error_type="GraphMethodException"))

    with pytest.raises(ResourceNotFoundError) as error:
        AdService(client, make_config()).find("1200000000000003")

    assert error.value.resource_type == "Ad"
    assert error.value.resource_id == "1200000000000003"


def test_it_produces_the_golden_requests() -> None:
    golden = load_request_fixture("entities")["ad"]

    client = FakeMetaClient(collection_response(), collection_response())
    service = AdService(client, make_config())

    service.all()
    service.for_ad_set("1200000000000002", AdQuery(fields=Fields(["name", "adset_id", "campaign_id"])))

    for case, request in zip(golden.values(), client.requests, strict=True):
        assert request.method == case["method"]
        assert request.path == case["path"]
        assert request.query == case["query"]
        assert encode_query(request.query) == case["encoded_query"]
