"""Tests for Meta error mapping and diagnostic sanitisation.

Ported from ``tests/Unit/Authentication/ErrorHandlingTest.php``. The two
pagination-specific cases move to the Phase 2 pagination test module.
"""

from __future__ import annotations

import pytest

from metametrics.client import JsonResponseDecoder, Response
from metametrics.errors.mapper import MetaErrorMapper
from metametrics.errors.parser import MetaErrorParser
from metametrics.exceptions import (
    AuthenticationError,
    InvalidConfigurationError,
    InvalidInputError,
    MetaAdsError,
    NetworkError,
    PermissionDeniedError,
    RateLimitError,
    ResourceNotFoundError,
    UnexpectedResponseError,
    UnsupportedMetricError,
)
from metametrics.utils.diagnostics import DiagnosticSanitizer

SPECIFIC_EXCEPTIONS = [
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
    NetworkError,
    InvalidConfigurationError,
    InvalidInputError,
    ResourceNotFoundError,
    UnsupportedMetricError,
    UnexpectedResponseError,
]


@pytest.mark.parametrize("exception_class", SPECIFIC_EXCEPTIONS)
def test_every_specific_exception_extends_the_root(exception_class: type[MetaAdsError]) -> None:
    assert issubclass(exception_class, MetaAdsError)


def test_the_root_exception_is_a_runtime_error() -> None:
    assert issubclass(MetaAdsError, RuntimeError)


def test_permission_error_does_not_shadow_the_builtin() -> None:
    import builtins

    from metametrics import exceptions

    assert "PermissionError" not in exceptions.__all__
    assert not issubclass(PermissionDeniedError, builtins.OSError)
    assert issubclass(builtins.PermissionError, builtins.OSError)


def test_rate_limit_preserves_safe_retry_metadata_without_retrying() -> None:
    response = Response(
        status_code=400,
        body={
            "error": {
                "message": "Application request limit reached",
                "type": "OAuthException",
                "code": 4,
                "error_subcode": 99,
                "fbtrace_id": "trace-rate",
            }
        },
        headers={
            "Retry-After": "120",
            "X-App-Usage": '{"call_count":100}',
            "Authorization": "Bearer secret",
        },
    )

    exception = MetaErrorMapper().map(response)

    assert isinstance(exception, RateLimitError)
    assert exception.retryable is True
    assert exception.retry_after_seconds == 120
    assert exception.http_status == 400
    assert exception.trace_id == "trace-rate"
    assert exception.context()["x_app_usage"] == '{"call_count":100}'
    assert "secret" not in repr(exception.to_dict())


def test_unknown_meta_error_uses_the_generic_root_exception() -> None:
    exception = MetaErrorMapper().map(
        Response(
            status_code=400,
            body={
                "error": {
                    "message": "Unknown failure",
                    "type": "GraphAPIException",
                    "code": 987654,
                    "error_subcode": 123,
                    "fbtrace_id": "trace-unknown",
                }
            },
        )
    )

    assert type(exception) is MetaAdsError
    assert exception.meta_error_code == 987654
    assert exception.http_status == 400
    assert exception.retryable is False


def test_server_failure_is_generic_and_retryable() -> None:
    exception = MetaErrorMapper().map(
        Response(
            status_code=503,
            body={"error": {"message": "Unavailable", "type": "GraphAPIException", "code": 2}},
        )
    )

    assert type(exception) is MetaAdsError
    assert exception.retryable is True
    assert exception.http_status == 503


def test_meta_transient_indicator_makes_a_generic_failure_retryable() -> None:
    exception = MetaErrorMapper().map(
        Response(
            status_code=400,
            body={
                "error": {
                    "message": "Temporary failure",
                    "type": "GraphAPIException",
                    "code": 999999,
                    "is_transient": True,
                }
            },
        )
    )

    assert type(exception) is MetaAdsError
    assert exception.retryable is True


@pytest.mark.parametrize(
    ("code", "subcode", "error_type", "expected"),
    [
        (190, 463, "OAuthException", AuthenticationError),
        (200, None, "OAuthException", PermissionDeniedError),
        (4, None, "OAuthException", RateLimitError),
        (100, 33, "GraphMethodException", ResourceNotFoundError),
        (100, None, "OAuthException", MetaAdsError),
    ],
)
def test_http_status_is_not_the_sole_classifier(
    code: int,
    subcode: int | None,
    error_type: str,
    expected: type[MetaAdsError],
) -> None:
    error: dict[str, object] = {"message": "Meta failure", "type": error_type, "code": code}
    if subcode is not None:
        error["error_subcode"] = subcode

    exception = MetaErrorMapper().map(Response(status_code=400, body={"error": error}))

    assert isinstance(exception, expected)


def test_resource_context_is_preserved_safely() -> None:
    exception = MetaErrorMapper().map(
        Response(
            status_code=400,
            body={
                "error": {
                    "message": "Object does not exist",
                    "type": "GraphMethodException",
                    "code": 100,
                    "error_subcode": 33,
                }
            },
        ),
        "Campaign",
        "campaign-123",
    )

    assert isinstance(exception, ResourceNotFoundError)
    assert exception.resource_type == "Campaign"
    assert exception.resource_id == "campaign-123"
    assert exception.context()["resource_id"] == "campaign-123"


def test_malformed_error_envelope_is_an_unexpected_response() -> None:
    with pytest.raises(UnexpectedResponseError):
        MetaErrorMapper().map(Response(status_code=400, body={"error": "invalid"}))


def test_malformed_error_diagnostics_retain_the_http_status() -> None:
    with pytest.raises(UnexpectedResponseError) as error:
        MetaErrorMapper().map(
            Response(
                status_code=502,
                body={"error": {"message": "Failure", "code": "not-an-integer"}},
            )
        )

    assert error.value.http_status == 502


def test_malformed_json_is_wrapped_and_preserves_its_cause() -> None:
    with pytest.raises(UnexpectedResponseError) as error:
        JsonResponseDecoder().decode("{invalid", 502)

    assert error.value.__cause__ is not None
    assert error.value.http_status == 502
    assert "{invalid" not in error.value.message


def test_trace_header_is_used_when_the_error_payload_has_no_trace_id() -> None:
    exception = MetaErrorMapper().map(
        Response(
            status_code=400,
            body={"error": {"message": "Unknown failure", "code": 987654}},
            headers={"X-FB-Trace-ID": "trace-from-header"},
        )
    )

    assert exception.trace_id == "trace-from-header"


def test_error_envelope_is_mapped_even_with_a_successful_http_status() -> None:
    response = Response(
        status_code=200,
        body={"error": {"message": "Invalid token", "type": "OAuthException", "code": 190}},
    )

    assert response.is_successful() is False


def test_diagnostic_sanitization_redacts_urls_messages_and_headers() -> None:
    sanitizer = DiagnosticSanitizer()
    secret = "EAAB_SUPER_SECRET_TEST_TOKEN"
    secret_proof = "SUPER_SECRET_APP_PROOF"

    url = sanitizer.sanitize_url(
        f"https://graph.facebook.com/v26.0/me?fields=id&ACCESS_TOKEN={secret}&appsecret_proof={secret_proof}"
    )
    message = sanitizer.sanitize_message(
        f"Failed access_token={secret} "
        f'payload={{"app_secret":"{secret_proof}"}} '
        f"encoded=appsecret_proof%3D{secret_proof} "
        f"Authorization: Bearer {secret}"
    )
    headers = sanitizer.sanitize_headers({"Authorization": f"Bearer {secret}", "Retry-After": "30"})

    assert secret not in url
    assert secret_proof not in url
    assert secret not in message
    assert secret_proof not in message
    assert headers == {"retry-after": "30"}


def test_parsed_upstream_message_is_sanitized() -> None:
    secret = "EAAB_SUPER_SECRET_TEST_TOKEN"

    error = MetaErrorParser().parse(
        Response(status_code=400, body={"error": {"message": f"Rejected access_token={secret}", "code": 190}})
    )

    assert error.message is not None
    assert secret not in error.message


def test_network_error_can_preserve_the_transport_cause() -> None:
    cause = RuntimeError("Transport failed.")

    with pytest.raises(NetworkError) as error:
        try:
            raise NetworkError("Meta API network request failed.", retryable=True) from cause
        except NetworkError as raised:
            raise raised from cause

    assert error.value.__cause__ is cause
    assert error.value.retryable is True


@pytest.mark.parametrize(
    "context",
    [
        {"access_token": "secret"},
        {"unknown_header": "value"},
    ],
)
def test_unsafe_exception_context_is_rejected(context: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        MetaAdsError("boom", safe_context=context)


def test_exception_context_drops_empty_values() -> None:
    exception = MetaAdsError("boom", http_status=500)

    assert exception.context() == {"http_status": 500, "retryable": False}
