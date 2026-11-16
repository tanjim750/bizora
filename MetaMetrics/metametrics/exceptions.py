"""Exception hierarchy for the MetaMetrics library.

Every failure raised by the public API derives from :class:`MetaAdsError`. The
diagnostic payload attached to an exception is intentionally allow-listed so
that it can be written to an application log without leaking credentials.

The hierarchy mirrors the PHP original one-to-one::

    PHP                                Python
    --------------------------------  -------------------------------
    MetaAdsException                   MetaAdsError
    AuthenticationException            AuthenticationError
    InvalidConfigurationException      InvalidConfigurationError
    InvalidInputException              InvalidInputError
    NetworkException                   NetworkError
    PermissionException                PermissionDeniedError
    RateLimitException                 RateLimitError
    ResourceNotFoundException          ResourceNotFoundError
    UnexpectedResponseException        UnexpectedResponseError
    UnsupportedMetricException         UnsupportedMetricError

``PermissionDeniedError`` deliberately does **not** use the name
``PermissionError``: that name belongs to a builtin ``OSError`` subclass and
shadowing it would break ``except PermissionError`` handlers in consumer code.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Final

__all__ = [
    "AuthenticationError",
    "InvalidConfigurationError",
    "InvalidInputError",
    "MetaAdsError",
    "NetworkError",
    "PermissionDeniedError",
    "RateLimitError",
    "ResourceNotFoundError",
    "UnexpectedResponseError",
    "UnsupportedMetricError",
]

#: The only context keys that may ever be attached to an exception.
SAFE_CONTEXT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "x_ad_account_usage",
        "x_app_usage",
        "x_business_use_case_usage",
    }
)

_SENSITIVE_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"token|secret|authorization|appsecret|credential",
    re.IGNORECASE,
)


class MetaAdsError(RuntimeError):
    """Base class for every failure raised by MetaMetrics.

    The exception carries the Meta API diagnostic fields so that a caller can
    decide whether to retry, surface a message, or escalate.
    """

    def __init__(
        self,
        message: str,
        *,
        meta_error_code: int | None = None,
        meta_error_subcode: int | None = None,
        meta_error_type: str | None = None,
        trace_id: str | None = None,
        http_status: int | None = None,
        retryable: bool = False,
        retry_after_seconds: int | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        safe_context: Mapping[str, bool | float | int | str | None] | None = None,
    ) -> None:
        validated = self._validate_context(safe_context or {})

        self.message = message
        self.meta_error_code = meta_error_code
        self.meta_error_subcode = meta_error_subcode
        self.meta_error_type = meta_error_type
        self.trace_id = trace_id
        self.http_status = http_status
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.safe_context: dict[str, bool | float | int | str | None] = validated

        super().__init__(message)

    @staticmethod
    def _validate_context(
        context: Mapping[str, bool | float | int | str | None],
    ) -> dict[str, bool | float | int | str | None]:
        for key, value in context.items():
            if not isinstance(key, str) or (
                not isinstance(value, (bool, float, int, str)) and value is not None
            ):
                raise ValueError("Exception context must contain safe scalar values.")

            if _SENSITIVE_KEY_PATTERN.search(key):
                raise ValueError("Exception context contains a sensitive key.")

            if key not in SAFE_CONTEXT_KEYS:
                raise ValueError("Exception context contains an unsupported key.")

        return dict(context)

    def context(self) -> dict[str, bool | float | int | str | None]:
        """Return the log-safe diagnostic context for this exception."""
        merged: dict[str, Any] = {
            **self.safe_context,
            "http_status": self.http_status,
            "meta_code": self.meta_error_code,
            "meta_subcode": self.meta_error_subcode,
            "meta_type": self.meta_error_type,
            "trace_id": self.trace_id,
            "retryable": self.retryable,
            "retry_after_seconds": self.retry_after_seconds,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
        }

        return {key: value for key, value in merged.items() if value is not None}

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation of this exception."""
        return {
            "message": self.message,
            "meta_error_code": self.meta_error_code,
            "meta_error_subcode": self.meta_error_subcode,
            "meta_error_type": self.meta_error_type,
            "trace_id": self.trace_id,
            "http_status": self.http_status,
            "retryable": self.retryable,
            "retry_after_seconds": self.retry_after_seconds,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "context": dict(self.safe_context),
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r}, context={self.context()!r})"


class AuthenticationError(MetaAdsError):
    """Raised when Meta rejects the configured access token."""


class InvalidConfigurationError(MetaAdsError):
    """Raised when the client configuration is invalid."""


class InvalidInputError(MetaAdsError):
    """Raised when a caller supplies an invalid argument."""


class NetworkError(MetaAdsError):
    """Raised when the Meta API request could not be delivered."""


class PermissionDeniedError(MetaAdsError):
    """Raised when the access token lacks permission for an operation."""


class RateLimitError(MetaAdsError):
    """Raised when the Meta API rate limit has been exceeded."""


class ResourceNotFoundError(MetaAdsError):
    """Raised when a Meta resource cannot be found or accessed."""


class UnexpectedResponseError(MetaAdsError):
    """Raised when Meta returns a malformed or unexpected payload."""


class UnsupportedMetricError(MetaAdsError):
    """Raised when a metric is unknown, unsupported, or misconfigured."""
