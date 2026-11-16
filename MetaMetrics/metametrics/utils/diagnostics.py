"""Utilities for redacting secrets from diagnostic data."""

from __future__ import annotations

import re
from typing import Final
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

__all__ = ["DiagnosticSanitizer"]

_SENSITIVE_QUERY_PARAMETERS: Final[frozenset[str]] = frozenset({"access_token", "appsecret_proof"})

_SAFE_HEADERS: Final[frozenset[str]] = frozenset(
    {
        "retry-after",
        "x-ad-account-usage",
        "x-app-usage",
        "x-business-use-case-usage",
        "x-fb-trace-id",
    }
)

_REDACTED: Final[str] = "[REDACTED]"

_QUOTED_SECRET_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'(["\']?(?:access_token|appsecret_proof|app_secret|authorization)["\']?\s*:\s*)(["\'])[^"\']*\2',
    re.IGNORECASE,
)

_AUTHORIZATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\bAuthorization\s*[:=]\s*(?:(?:Bearer|Basic)\s+)?[^\s,;\'\"]+",
    re.IGNORECASE,
)

_QUERY_SECRET_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(access_token|appsecret_proof|app_secret)=([^&\s]+)",
    re.IGNORECASE,
)

_COLON_SECRET_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(access_token|appsecret_proof|app_secret)\s*:\s*([^\s,;}]+)",
    re.IGNORECASE,
)

_ENCODED_SECRET_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(access_token|appsecret_proof|app_secret|authorization)%3D([^&\s]+)",
    re.IGNORECASE,
)

_BEARER_PATTERN: Final[re.Pattern[str]] = re.compile(r"\bBearer\s+[^\s]+", re.IGNORECASE)


class DiagnosticSanitizer:
    """Redacts credentials from URLs, messages, and response headers."""

    def sanitize_url(self, url: str) -> str:
        parts = urlsplit(url)

        if not parts.scheme or not parts.netloc:
            return "[INVALID URL]"

        query = [
            (name, _REDACTED if name.lower() in _SENSITIVE_QUERY_PARAMETERS else value)
            for name, value in parse_qsl(parts.query, keep_blank_values=True)
        ]

        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, quote_via=quote), ""))

    def sanitize_message(self, message: str) -> str:
        sanitized = _QUOTED_SECRET_PATTERN.sub(
            lambda match: f"{match.group(1)}{match.group(2)}{_REDACTED}{match.group(2)}",
            message,
        )
        sanitized = _AUTHORIZATION_PATTERN.sub("Authorization: [REDACTED]", sanitized)
        sanitized = _QUERY_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}={_REDACTED}", sanitized)
        sanitized = _COLON_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}{_REDACTED}", sanitized)
        sanitized = _ENCODED_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}%3D{_REDACTED}", sanitized)

        return _BEARER_PATTERN.sub("Bearer [REDACTED]", sanitized)

    def sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        safe: dict[str, str] = {}

        for name, value in headers.items():
            normalized = name.lower()
            if normalized in _SAFE_HEADERS:
                safe[normalized] = value

        return safe
