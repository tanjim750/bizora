"""Tests for cursor-based pagination.

Ported from the pagination cases of
``tests/Unit/Authentication/ErrorHandlingTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.client import Request, Response
from metametrics.exceptions import RateLimitError, UnexpectedResponseError
from metametrics.pagination.paginator import Paginator
from tests.support.fakes import FakeMetaClient


def page(*items: dict[str, object], next_cursor: str | None = None) -> Response:
    body: dict[str, object] = {"data": list(items)}
    if next_cursor is not None:
        body["paging"] = {
            "next": "https://graph.facebook.com/next",
            "cursors": {"after": next_cursor},
        }

    return Response(status_code=200, body=body)


def test_it_returns_a_single_page_when_there_is_no_cursor() -> None:
    client = FakeMetaClient(page({"id": "one"}))

    items = Paginator(client).fetch_all(Request(method="GET", path="/v23.0/items"))

    assert items == [{"id": "one"}]


def test_it_follows_the_cursor_until_the_last_page() -> None:
    client = FakeMetaClient(
        page({"id": "one"}, next_cursor="cursor-1"),
        page({"id": "two"}, next_cursor="cursor-2"),
        page({"id": "three"}),
    )

    items = Paginator(client).fetch_all(Request(method="GET", path="/v23.0/items"))

    assert items == [{"id": "one"}, {"id": "two"}, {"id": "three"}]
    assert len(client.requests) == 3
    assert client.requests[0].query == {}
    assert client.requests[1].query == {"after": "cursor-1"}
    assert client.requests[2].query == {"after": "cursor-2"}


def test_it_rejects_a_repeated_cursor() -> None:
    client = FakeMetaClient(
        page({"id": "one"}, next_cursor="same"),
        page({"id": "two"}, next_cursor="same"),
    )

    with pytest.raises(UnexpectedResponseError, match="repeated pagination cursor"):
        Paginator(client).fetch_all(Request(method="GET", path="/v23.0/items"))


def test_it_rejects_a_malformed_paginated_response() -> None:
    client = FakeMetaClient(Response(status_code=200, body={"items": []}))

    with pytest.raises(UnexpectedResponseError, match="malformed paginated response"):
        Paginator(client).fetch_all(Request(method="GET", path="/v23.0/items"))


def test_it_rejects_a_malformed_collection_item() -> None:
    client = FakeMetaClient(Response(status_code=200, body={"data": ["not-an-object"]}))

    with pytest.raises(UnexpectedResponseError, match="malformed collection item"):
        Paginator(client).fetch_all(Request(method="GET", path="/v23.0/items"))


def test_it_rejects_a_missing_next_cursor() -> None:
    client = FakeMetaClient(
        Response(status_code=200, body={"data": [], "paging": {"next": "https://graph.facebook.com/next"}}),
    )

    with pytest.raises(UnexpectedResponseError, match="missing its next cursor"):
        Paginator(client).fetch_all(Request(method="GET", path="/v23.0/items"))


def test_a_mid_pagination_rate_limit_does_not_return_partial_data() -> None:
    client = FakeMetaClient(
        page({"id": "first"}, next_cursor="next-page"),
        Response(status_code=429, body={"error": {"message": "Throttled", "code": 4}}),
    )

    with pytest.raises(RateLimitError):
        Paginator(client).fetch_all(Request(method="GET", path="/v23.0/items"))


def test_the_page_result_reports_whether_more_pages_exist() -> None:
    client = FakeMetaClient(page({"id": "one"}, next_cursor="cursor-1"))

    result = Paginator(client).fetch_page(Request(method="GET", path="/v23.0/items"))

    assert result.items == ({"id": "one"},)
    assert result.next_cursor == "cursor-1"
    assert result.has_next_page is True
