"""Tests for the low-level HTTP client.

These cover the behaviour the PHP original gets from cURL: GET-only requests,
a bearer token in the header (never in the URL), RFC 3986 query encoding, and
typed transport failures.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from metametrics.client import BASE_URL, MetaClient, Request, Response, encode_query
from metametrics.config import MetaConfig
from metametrics.exceptions import InvalidInputError, NetworkError, UnexpectedResponseError

TOKEN = "known-secret-test-token"


def make_client() -> MetaClient:
    return MetaClient(MetaConfig(access_token=TOKEN, ad_account_id="act_123456789", api_version="v23.0"))


def test_query_encoding_matches_php_http_build_query() -> None:
    assert encode_query({"fields": "id,name"}) == "fields=id%2Cname"
    assert encode_query({"is_completed": True}) == "is_completed=1"
    assert encode_query({"is_completed": False}) == "is_completed=0"
    assert encode_query({"limit": 25}) == "limit=25"
    assert encode_query({"name": "a b"}) == "name=a%20b"
    assert encode_query({"skipped": None, "kept": "yes"}) == "kept=yes"


def test_a_request_with_a_query_parameter_returns_a_copy() -> None:
    request = Request(method="GET", path="/v23.0/act_1/campaigns", query={"fields": "id"})

    updated = request.with_query_parameter("after", "cursor-1")

    assert updated.query == {"fields": "id", "after": "cursor-1"}
    assert request.query == {"fields": "id"}


def test_response_headers_are_normalised_to_lowercase() -> None:
    response = Response(status_code=200, body={}, headers={"Retry-After": "30"})

    assert response.headers == {"retry-after": "30"}
    assert response.header("RETRY-AFTER") == "30"
    assert response.header("missing") is None


def test_a_success_response_containing_an_error_payload_is_not_successful() -> None:
    assert Response(status_code=200, body={"id": "act_1"}).is_successful() is True
    assert Response(status_code=200, body={"error": {"code": 190}}).is_successful() is False
    assert Response(status_code=500, body={}).is_successful() is False


def test_it_rejects_non_get_requests() -> None:
    with pytest.raises(InvalidInputError, match="Unsupported Meta API HTTP method"):
        make_client().send(Request(method="POST", path="/v23.0/act_1"))


@pytest.mark.parametrize("path", ["v23.0/act_1", "/v23.0/act_1?fields=id"])
def test_it_rejects_invalid_paths(path: str) -> None:
    with pytest.raises(InvalidInputError, match="request path is invalid"):
        make_client().send(Request(method="GET", path=path))


def test_it_rejects_non_positive_timeouts() -> None:
    with pytest.raises(InvalidInputError, match="timeouts must be positive"):
        MetaClient(
            MetaConfig(access_token=TOKEN, ad_account_id="act_1", api_version="v23.0"),
            timeout=0,
        )


@respx.mock
def test_it_sends_the_bearer_token_in_the_header_and_not_in_the_url() -> None:
    route = respx.get(f"{BASE_URL}/v23.0/act_123456789").mock(
        return_value=httpx.Response(200, json={"id": "act_123456789"})
    )

    with make_client() as client:
        response = client.send(Request(method="GET", path="/v23.0/act_123456789", query={"fields": "id"}))

    request = route.calls.last.request
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert request.headers["accept"] == "application/json"
    assert request.headers["user-agent"] == "MetaMetrics/1.0"
    assert TOKEN not in str(request.url)
    assert str(request.url) == f"{BASE_URL}/v23.0/act_123456789?fields=id"
    assert response.status_code == 200
    assert response.body == {"id": "act_123456789"}


@respx.mock
def test_it_encodes_the_query_string_the_php_way() -> None:
    route = respx.get(f"{BASE_URL}/v23.0/act_1/campaigns").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with make_client() as client:
        client.send(
            Request(
                method="GET",
                path="/v23.0/act_1/campaigns",
                query={"fields": "id,name", "is_completed": True, "limit": 25},
            )
        )

    assert str(route.calls.last.request.url) == (
        f"{BASE_URL}/v23.0/act_1/campaigns?fields=id%2Cname&is_completed=1&limit=25"
    )


@respx.mock
def test_a_malformed_json_payload_is_an_unexpected_response() -> None:
    respx.get(f"{BASE_URL}/v23.0/act_1").mock(return_value=httpx.Response(200, text="{invalid"))

    with make_client() as client, pytest.raises(UnexpectedResponseError) as error:
        client.send(Request(method="GET", path="/v23.0/act_1"))

    assert error.value.http_status == 200


@respx.mock
def test_a_transport_failure_is_a_retryable_network_error() -> None:
    respx.get(f"{BASE_URL}/v23.0/act_1").mock(side_effect=httpx.ConnectTimeout("timed out"))

    with make_client() as client, pytest.raises(NetworkError) as error:
        client.send(Request(method="GET", path="/v23.0/act_1"))

    assert error.value.retryable is True


@respx.mock
def test_only_safe_response_headers_are_preserved() -> None:
    respx.get(f"{BASE_URL}/v23.0/act_1").mock(
        return_value=httpx.Response(
            200,
            json={"id": "act_1"},
            headers={"Retry-After": "30", "Authorization": "Bearer leaked"},
        )
    )

    with make_client() as client:
        response = client.send(Request(method="GET", path="/v23.0/act_1"))

    assert response.headers == {"retry-after": "30"}
