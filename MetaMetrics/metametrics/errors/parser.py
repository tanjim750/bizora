"""Extraction of diagnostic fields from a raw Meta API response."""

from __future__ import annotations

from typing import Any

from metametrics.client import Response
from metametrics.exceptions import UnexpectedResponseError
from metametrics.utils.diagnostics import DiagnosticSanitizer

from .model import MetaError

__all__ = ["MetaErrorParser"]


class MetaErrorParser:
    """Reads the ``error`` object out of a Meta API response.

    Meta occasionally returns partially malformed diagnostics. When the payload
    is structurally broken the parser raises
    :class:`~metametrics.exceptions.UnexpectedResponseError` rather than
    silently returning ``None`` for a field that was present but invalid.
    """

    def __init__(self, sanitizer: DiagnosticSanitizer | None = None) -> None:
        self.sanitizer = sanitizer or DiagnosticSanitizer()

    def parse(self, response: Response) -> MetaError:
        body = response.body
        payload: dict[str, Any] = {}

        if isinstance(body, dict) and "error" in body:
            raw_error = body["error"]
            if not isinstance(raw_error, dict):
                raise UnexpectedResponseError(
                    "Meta returned a malformed error response.",
                    http_status=response.status_code,
                )
            payload = raw_error

        status = response.status_code
        trace_id = self._optional_string(payload, "fbtrace_id", status)
        trace_header = response.header("x-fb-trace-id")

        return MetaError(
            http_status=status,
            message=self._safe_message(payload, status),
            type=self._optional_string(payload, "type", status),
            code=self._optional_integer(payload, "code", status),
            subcode=self._optional_integer(payload, "error_subcode", status),
            trace_id=trace_id if trace_id is not None else (trace_header or None),
            transient=self._optional_boolean(payload, "is_transient", status),
        )

    def _safe_message(self, payload: dict[str, Any], http_status: int) -> str | None:
        message = self._optional_string(payload, "message", http_status)

        return None if message is None else self.sanitizer.sanitize_message(message)

    def _optional_string(self, payload: dict[str, Any], field: str, http_status: int) -> str | None:
        if field not in payload or payload[field] is None:
            return None

        value = payload[field]
        if not isinstance(value, str) or value == "":
            raise UnexpectedResponseError(
                "Meta returned malformed error diagnostics.",
                http_status=http_status,
            )

        return value

    def _optional_integer(self, payload: dict[str, Any], field: str, http_status: int) -> int | None:
        if field not in payload or payload[field] is None:
            return None

        value = payload[field]
        if not isinstance(value, int) or isinstance(value, bool):
            raise UnexpectedResponseError(
                "Meta returned malformed error diagnostics.",
                http_status=http_status,
            )

        return value

    def _optional_boolean(self, payload: dict[str, Any], field: str, http_status: int) -> bool | None:
        if field not in payload or payload[field] is None:
            return None

        value = payload[field]
        if not isinstance(value, bool):
            raise UnexpectedResponseError(
                "Meta returned malformed error diagnostics.",
                http_status=http_status,
            )

        return value
