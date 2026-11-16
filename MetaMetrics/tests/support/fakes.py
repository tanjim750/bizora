"""Shared test doubles for the MetaMetrics test suite."""

from __future__ import annotations

from typing import Any

from metametrics.client import Request, Response


class FakeMetaClient:
    """A client that records requests and replays queued responses."""

    def __init__(self, *responses: Response | Exception) -> None:
        self._responses: list[Response | Exception] = list(responses)
        self.requests: list[Request] = []

    def queue(self, *responses: Response | Exception) -> FakeMetaClient:
        self._responses.extend(responses)
        return self

    def send(self, request: Request) -> Response:
        self.requests.append(request)

        if not self._responses:
            raise AssertionError(f"FakeMetaClient received an unexpected request: {request.path}")

        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    @property
    def request_count(self) -> int:
        return len(self.requests)

    @property
    def last_request(self) -> Request:
        return self.requests[-1]


def error_response(
    status_code: int = 400,
    *,
    code: int | None = None,
    subcode: int | None = None,
    error_type: str | None = None,
    message: str = "Something went wrong.",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> Response:
    """Build a Meta-shaped error response."""
    error: dict[str, Any] = {"message": message}
    if code is not None:
        error["code"] = code
    if subcode is not None:
        error["error_subcode"] = subcode
    if error_type is not None:
        error["type"] = error_type

    payload: dict[str, Any] = body if body is not None else {"error": error}

    return Response(status_code=status_code, body=payload, raw_body="{}", headers=headers or {})
