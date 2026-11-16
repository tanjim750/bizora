"""Low-level HTTP client for the Meta Marketing API.

The client is intentionally GET-only and never raises on an HTTP error status:
it returns a :class:`Response` and lets the service layer decide how to map a
failure onto a typed exception. This mirrors the PHP original and keeps raw
responses reachable through ``MetaAds.client()``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Final, Protocol, runtime_checkable
from urllib.parse import quote, urlencode

import httpx

from .config import MetaConfig
from .exceptions import InvalidInputError, NetworkError, UnexpectedResponseError
from .utils.diagnostics import DiagnosticSanitizer

__all__ = [
    "BASE_URL",
    "JsonResponseDecoder",
    "MetaClient",
    "MetaClientProtocol",
    "Request",
    "Response",
    "encode_query",
]

BASE_URL: Final[str] = "https://graph.facebook.com"

_USER_AGENT: Final[str] = "MetaMetrics/1.0"

QueryValue = str | int | float | bool
QueryParameters = dict[str, QueryValue]


def _encode_scalar(value: QueryValue) -> str:
    """Render a scalar the way PHP's ``http_build_query`` would.

    PHP renders booleans as ``1``/``0`` and encodes spaces as ``%20``
    (``PHP_QUERY_RFC3986``). ``httpx`` renders booleans as ``true``/``false``,
    so every value is converted before it reaches the transport.
    """
    if isinstance(value, bool):
        return "1" if value else "0"

    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)

    return str(value)


def encode_query(query: Mapping[str, QueryValue | None]) -> str:
    """Encode query parameters exactly as PHP's ``http_build_query`` does."""
    items = [(name, _encode_scalar(value)) for name, value in query.items() if value is not None]

    return urlencode(items, quote_via=quote)


@dataclass(frozen=True, slots=True)
class Request:
    """An immutable Meta API request."""

    method: str
    path: str
    query: QueryParameters = field(default_factory=dict)

    def with_query_parameter(self, name: str, value: QueryValue) -> Request:
        """Return a copy of this request with an additional query parameter."""
        return Request(method=self.method, path=self.path, query={**self.query, name: value})


@dataclass(frozen=True, slots=True)
class Response:
    """An immutable Meta API response."""

    status_code: int
    body: Any
    raw_body: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized: dict[str, str] = {}

        for name, value in self.headers.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise InvalidInputError("Response headers must be strings.")

            normalized[name.lower()] = value

        object.__setattr__(self, "headers", normalized)

    def header(self, name: str) -> str | None:
        """Return a response header, or ``None`` when it is absent."""
        return self.headers.get(name.lower())

    def is_successful(self) -> bool:
        """Return ``True`` for a 2xx response that does not carry an error payload."""
        return 200 <= self.status_code < 300 and not (isinstance(self.body, dict) and "error" in self.body)


@runtime_checkable
class MetaClientProtocol(Protocol):
    """The contract every Meta API transport must satisfy."""

    def send(self, request: Request) -> Response:  # pragma: no cover - protocol definition
        ...


class JsonResponseDecoder:
    """Decodes raw Meta API payloads into Python objects."""

    def decode(self, raw_body: str, http_status: int | None = None) -> Any:
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as error:
            raise UnexpectedResponseError(
                "Meta returned a malformed JSON response.",
                http_status=http_status,
            ) from error


class MetaClient:
    """A ``httpx``-backed implementation of :class:`MetaClientProtocol`."""

    def __init__(
        self,
        config: MetaConfig,
        *,
        connect_timeout: float = 10.0,
        timeout: float = 30.0,
        decoder: JsonResponseDecoder | None = None,
        sanitizer: DiagnosticSanitizer | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if connect_timeout < 1 or timeout < 1:
            raise InvalidInputError("HTTP timeouts must be positive integers.")

        self.config = config
        self.connect_timeout = connect_timeout
        self.timeout = timeout
        self.decoder = decoder or JsonResponseDecoder()
        self.sanitizer = sanitizer or DiagnosticSanitizer()
        self._owns_client = http_client is None
        self._http_client = http_client or httpx.Client(
            base_url=BASE_URL,
            timeout=httpx.Timeout(timeout, connect=connect_timeout),
            follow_redirects=False,
        )

    def send(self, request: Request) -> Response:
        """Execute a Meta API request and return the raw response."""
        method = request.method.upper()

        if method != "GET":
            raise InvalidInputError(f'Unsupported Meta API HTTP method "{method}".')

        path = request.path
        if not path.startswith("/") or "?" in path:
            raise InvalidInputError("Meta API request path is invalid.")

        query = encode_query(request.query)
        url = f"{path}?{query}" if query else path

        try:
            raw_response = self._http_client.request(
                method,
                url,
                headers=self._headers(),
            )
        except httpx.HTTPError as error:
            raise NetworkError(
                "Meta API network request failed.",
                retryable=True,
            ) from error

        raw_body = raw_response.text

        return Response(
            status_code=raw_response.status_code,
            body=self.decoder.decode(raw_body, raw_response.status_code),
            raw_body=raw_body,
            headers=self.sanitizer.sanitize_headers(dict(raw_response.headers)),
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config.access_token}",
            "User-Agent": _USER_AGENT,
        }

    def close(self) -> None:
        """Close the underlying transport when this client owns it."""
        if self._owns_client:
            self._http_client.close()

    def __enter__(self) -> MetaClient:
        return self

    def __exit__(self, *exception_info: object) -> None:
        self.close()
