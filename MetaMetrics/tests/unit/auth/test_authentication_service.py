"""Tests for the authentication service.

Ported from ``tests/Unit/Authentication/AuthenticationServiceTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.auth.service import AuthenticationService
from metametrics.client import Request, Response, encode_query
from metametrics.config import MetaConfig
from metametrics.exceptions import (
    AuthenticationError,
    MetaAdsError,
    NetworkError,
    PermissionDeniedError,
    RateLimitError,
    ResourceNotFoundError,
    UnexpectedResponseError,
)
from tests.support.fakes import FakeMetaClient
from tests.support.fixtures import load_request_fixture

TOKEN = "known-secret-test-token"


def make_config() -> MetaConfig:
    return MetaConfig(access_token=TOKEN, ad_account_id="act_123456789", api_version="v23.0")


def error_response(
    status_code: int,
    code: int,
    subcode: int | None,
    error_type: str,
    trace_id: str = "trace-id",
) -> Response:
    error: dict[str, object] = {
        "message": "Meta supplied message",
        "type": error_type,
        "code": code,
        "fbtrace_id": trace_id,
    }
    if subcode is not None:
        error["error_subcode"] = subcode

    return Response(status_code=status_code, body={"error": error})


def capture_exception(response: Response, expected: type[MetaAdsError]) -> MetaAdsError:
    client = FakeMetaClient(response)

    with pytest.raises(expected) as error:
        AuthenticationService(client, make_config()).validate()

    return error.value


def test_it_validates_authentication_and_account_access() -> None:
    client = FakeMetaClient(Response(status_code=200, body={"id": "act_123456789"}))

    result = AuthenticationService(client, make_config()).validate()

    assert result.authenticated is True
    assert result.account_accessible is True
    assert result.account_id == "act_123456789"

    request = client.last_request
    assert request.method == "GET"
    assert request.path == "/v23.0/act_123456789"
    assert request.query == {"fields": "id"}


def test_it_produces_the_golden_request() -> None:
    golden = load_request_fixture("authentication")["validate"]
    client = FakeMetaClient(Response(status_code=200, body={"id": "act_123456789"}))

    AuthenticationService(client, make_config()).validate()

    request = client.last_request
    assert request.method == golden["method"]
    assert request.path == golden["path"]
    assert request.query == golden["query"]
    assert encode_query(request.query) == golden["encoded_query"]


def test_it_maps_an_invalid_token_to_authentication_error() -> None:
    exception = capture_exception(
        error_response(400, 190, None, "OAuthException"),
        AuthenticationError,
    )

    assert exception.meta_error_code == 190
    assert exception.meta_error_type == "OAuthException"


def test_it_maps_an_expired_token_to_authentication_error() -> None:
    exception = capture_exception(
        error_response(400, 190, 463, "OAuthException", "trace-expired"),
        AuthenticationError,
    )

    assert exception.meta_error_code == 190
    assert exception.meta_error_subcode == 463
    assert exception.trace_id == "trace-expired"


def test_it_maps_missing_permission_to_permission_denied_error() -> None:
    exception = capture_exception(
        error_response(403, 200, None, "OAuthException"),
        PermissionDeniedError,
    )

    assert exception.meta_error_code == 200


def test_it_does_not_classify_an_inaccessible_account_as_an_invalid_token() -> None:
    exception = capture_exception(
        error_response(400, 100, 33, "GraphMethodException"),
        ResourceNotFoundError,
    )

    assert exception.meta_error_code == 100
    assert exception.meta_error_subcode == 33


def test_it_preserves_network_errors_from_the_client() -> None:
    network_error = NetworkError("Unable to connect to Meta.")

    class FailingClient:
        def send(self, request: Request) -> Response:
            raise network_error

    with pytest.raises(NetworkError) as error:
        AuthenticationService(FailingClient(), make_config()).validate()

    assert error.value is network_error


def test_it_maps_rate_limit_errors_separately() -> None:
    exception = capture_exception(
        error_response(400, 4, None, "OAuthException", "trace-rate"),
        RateLimitError,
    )

    assert exception.meta_error_code == 4
    assert exception.trace_id == "trace-rate"


def test_it_maps_http_rate_limit_without_an_error_payload() -> None:
    exception = capture_exception(Response(status_code=429, body=[]), RateLimitError)

    assert exception.meta_error_code is None


def test_it_rejects_a_success_response_with_the_wrong_account() -> None:
    client = FakeMetaClient(Response(status_code=200, body={"id": "act_987654321"}))

    with pytest.raises(UnexpectedResponseError):
        AuthenticationService(client, make_config()).validate()


def test_it_rejects_a_malformed_success_response() -> None:
    client = FakeMetaClient(Response(status_code=200, body="<html>not json</html>"))

    with pytest.raises(UnexpectedResponseError):
        AuthenticationService(client, make_config()).validate()


def test_credentials_never_appear_in_results_requests_or_exceptions() -> None:
    client = FakeMetaClient(Response(status_code=200, body={"id": "act_123456789"}))

    result = AuthenticationService(client, make_config()).validate()

    assert TOKEN not in repr(result)
    assert TOKEN not in repr(client.last_request)

    response = Response(
        status_code=400,
        body={
            "error": {
                "message": f"Rejected token {TOKEN}",
                "type": "OAuthException",
                "code": 190,
            }
        },
    )
    exception = capture_exception(response, AuthenticationError)

    assert TOKEN not in exception.message
    assert TOKEN not in repr(exception.to_dict())
