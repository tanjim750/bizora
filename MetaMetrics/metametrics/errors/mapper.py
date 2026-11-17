"""Mapping of Meta API failures onto the library's typed exceptions."""

from __future__ import annotations

import re
from typing import Final

from metametrics.client import Response
from metametrics.exceptions import (
    AuthenticationError,
    MetaAdsError,
    PermissionDeniedError,
    RateLimitError,
    ResourceNotFoundError,
)

from .model import MetaError
from .parser import MetaErrorParser

__all__ = ["MetaErrorMapper"]

_AUTHENTICATION_CODES: Final[frozenset[int]] = frozenset({102, 190})
_PERMISSION_CODES: Final[frozenset[int]] = frozenset({10})
_RATE_LIMIT_CODES: Final[frozenset[int]] = frozenset({4, 17, 32, 341, 613})
_RESOURCE_CODES: Final[frozenset[int]] = frozenset({803})
_RESOURCE_SUBCODES: Final[frozenset[int]] = frozenset({33})
_TRANSIENT_CODES: Final[frozenset[int]] = frozenset({1, 2})

_RETRY_AFTER_PATTERN: Final[re.Pattern[str]] = re.compile(r"\A[0-9]+\Z")

_USAGE_HEADERS: Final[tuple[str, ...]] = (
    "x-app-usage",
    "x-ad-account-usage",
    "x-business-use-case-usage",
)


class MetaErrorMapper:
    """Converts an unsuccessful Meta API response into a typed exception."""

    def __init__(self, parser: MetaErrorParser | None = None) -> None:
        self.parser = parser or MetaErrorParser()

    def map(
        self,
        response: Response,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> MetaAdsError:
        error = self.parser.parse(response)

        return self._build(error, response, resource_type, resource_id)

    def _build(
        self,
        error: MetaError,
        response: Response,
        resource_type: str | None,
        resource_id: str | None,
    ) -> MetaAdsError:
        code = error.code
        subcode = error.subcode
        http_status = error.http_status

        if http_status == 429 or (code is not None and code in _RATE_LIMIT_CODES):
            return RateLimitError(
                "Meta API rate limit exceeded.",
                meta_error_code=code,
                meta_error_subcode=subcode,
                meta_error_type=error.type,
                trace_id=error.trace_id,
                http_status=http_status,
                retryable=True,
                retry_after_seconds=self._retry_after_seconds(response),
                resource_type=resource_type,
                resource_id=resource_id,
                safe_context=self._usage_context(response),
            )

        if (code is not None and code in _AUTHENTICATION_CODES) or http_status == 401:
            return AuthenticationError(
                "Meta rejected the configured access token.",
                meta_error_code=code,
                meta_error_subcode=subcode,
                meta_error_type=error.type,
                trace_id=error.trace_id,
                http_status=http_status,
                resource_type=resource_type,
                resource_id=resource_id,
            )

        if self._is_permission_code(code) or http_status == 403:
            return PermissionDeniedError(
                "The access token does not have permission to perform this Meta API operation.",
                meta_error_code=code,
                meta_error_subcode=subcode,
                meta_error_type=error.type,
                trace_id=error.trace_id,
                http_status=http_status,
                resource_type=resource_type,
                resource_id=resource_id,
            )

        if self._is_resource_error(code, subcode) or http_status == 404:
            message = (
                "The requested Meta resource could not be found or accessed."
                if resource_type is None
                else f"The requested Meta {resource_type} could not be found or accessed."
            )
            return ResourceNotFoundError(
                message,
                meta_error_code=code,
                meta_error_subcode=subcode,
                meta_error_type=error.type,
                trace_id=error.trace_id,
                http_status=http_status,
                resource_type=resource_type,
                resource_id=resource_id,
            )

        return MetaAdsError(
            "Meta API request failed.",
            meta_error_code=code,
            meta_error_subcode=subcode,
            meta_error_type=error.type,
            trace_id=error.trace_id,
            http_status=http_status,
            retryable=self._is_retryable(error),
            resource_type=resource_type,
            resource_id=resource_id,
        )

    @staticmethod
    def _is_permission_code(code: int | None) -> bool:
        return code is not None and (code in _PERMISSION_CODES or 200 <= code <= 299)

    @staticmethod
    def _is_resource_error(code: int | None, subcode: int | None) -> bool:
        return (code is not None and code in _RESOURCE_CODES) or (
            subcode is not None and subcode in _RESOURCE_SUBCODES
        )

    @staticmethod
    def _is_retryable(error: MetaError) -> bool:
        return (
            error.transient is True
            or error.http_status >= 500
            or (error.code is not None and error.code in _TRANSIENT_CODES)
        )

    @staticmethod
    def _retry_after_seconds(response: Response) -> int | None:
        retry_after = response.header("retry-after")
        if retry_after is None or not _RETRY_AFTER_PATTERN.match(retry_after):
            return None

        seconds = int(retry_after)

        return seconds if seconds >= 0 else None

    @staticmethod
    def _usage_context(response: Response) -> dict[str, str]:
        context: dict[str, str] = {}

        for header in _USAGE_HEADERS:
            value = response.header(header)
            if value is not None:
                context[header.replace("-", "_")] = value

        return context
