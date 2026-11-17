"""Cursor-based pagination over the Meta API."""

from __future__ import annotations

from typing import Any

from metametrics.client import MetaClientProtocol, Request
from metametrics.errors.mapper import MetaErrorMapper
from metametrics.exceptions import UnexpectedResponseError
from metametrics.pagination.result import PaginationResult

__all__ = ["Paginator"]


class Paginator:
    """Walks a Meta collection page by page.

    A repeated cursor aborts the walk with an
    :class:`~metametrics.exceptions.UnexpectedResponseError` instead of looping
    forever, and a failure on any page raises rather than returning the pages
    that happened to succeed.
    """

    def __init__(self, client: MetaClientProtocol, error_mapper: MetaErrorMapper | None = None) -> None:
        self.client = client
        self.error_mapper = error_mapper or MetaErrorMapper()

    def fetch_all(self, request: Request) -> list[dict[str, Any]]:
        """Fetch every page of a collection and return the combined items."""
        items: list[dict[str, Any]] = []
        seen_cursors: set[str] = set()

        current = request

        while True:
            page = self.fetch_page(current)
            items.extend(page.items)

            cursor = page.next_cursor
            if cursor is None:
                return items

            if cursor in seen_cursors:
                raise UnexpectedResponseError("Meta returned a repeated pagination cursor.")

            seen_cursors.add(cursor)
            current = current.with_query_parameter("after", cursor)

    def fetch_page(self, request: Request) -> PaginationResult:
        """Fetch a single page of a collection."""
        response = self.client.send(request)

        if not response.is_successful():
            raise self.error_mapper.map(response)

        body = response.body
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            raise UnexpectedResponseError("Meta returned a malformed paginated response.")

        data = body["data"]

        for item in data:
            if not isinstance(item, dict):
                raise UnexpectedResponseError("Meta returned a malformed collection item.")

        return PaginationResult(items=tuple(data), next_cursor=self._next_cursor(body))

    @staticmethod
    def _next_cursor(body: dict[str, Any]) -> str | None:
        paging = body.get("paging")

        if not isinstance(paging, dict) or "next" not in paging:
            return None

        cursors = paging.get("cursors")
        cursor = cursors.get("after") if isinstance(cursors, dict) else None

        if not isinstance(cursor, str) or cursor == "":
            raise UnexpectedResponseError("Meta pagination is missing its next cursor.")

        return cursor
