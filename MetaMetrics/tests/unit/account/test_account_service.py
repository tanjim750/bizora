"""Tests for the Ad Account service.

Ported from ``tests/Unit/Account/AccountServiceTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.account.normalizer import AccountNormalizer
from metametrics.account.service import AccountService
from metametrics.client import Response, encode_query
from metametrics.config import MetaConfig
from metametrics.exceptions import (
    ResourceNotFoundError,
    UnexpectedResponseError,
)
from tests.support.fakes import FakeMetaClient, error_response
from tests.support.fixtures import load_request_fixture

ACCOUNT_ID = "act_4274485329463051"


def make_config() -> MetaConfig:
    return MetaConfig(access_token="test-token", ad_account_id=ACCOUNT_ID, api_version="v26.0")


def account_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": ACCOUNT_ID,
        "name": "Triizync Solution Ad account",
        "account_id": "4274485329463051",
        "account_status": 1,
        "currency": "BDT",
        "timezone_name": "Europe/London",
    }
    body.update(overrides)
    return body


def test_it_retrieves_the_account_currency() -> None:
    client = FakeMetaClient(Response(status_code=200, body=account_body()))

    currency = AccountService(client, make_config()).get_currency()

    assert currency == "BDT"

    request = client.last_request
    assert request.method == "GET"
    assert request.path == f"/v26.0/{ACCOUNT_ID}"
    assert request.query == {"fields": "currency"}


@pytest.mark.parametrize(
    "body",
    [
        {"id": ACCOUNT_ID},
        {"id": ACCOUNT_ID, "currency": None},
        {"id": ACCOUNT_ID, "currency": ""},
        {"id": ACCOUNT_ID, "currency": 123},
        {"id": ACCOUNT_ID, "currency": ["BDT"]},
        {"id": ACCOUNT_ID, "currency": "bdt"},
        {"id": ACCOUNT_ID, "currency": "BD"},
        {"currency": "BDT"},
        {"id": "act_999", "currency": "BDT"},
        "BDT",
    ],
    ids=[
        "missing currency",
        "null currency",
        "empty currency",
        "non-string currency",
        "array currency",
        "lowercase code",
        "invalid code length",
        "missing account ID",
        "wrong account ID",
        "non-object response",
    ],
)
def test_it_rejects_malformed_currency_responses(body: object) -> None:
    client = FakeMetaClient(Response(status_code=200, body=body))

    with pytest.raises(UnexpectedResponseError) as error:
        AccountService(client, make_config()).get_currency()

    assert error.value.http_status == 200
    assert error.value.resource_id == ACCOUNT_ID


def test_currency_retrieval_uses_typed_api_errors() -> None:
    client = FakeMetaClient(error_response(400, code=100, subcode=33, error_type="GraphMethodException"))

    with pytest.raises(ResourceNotFoundError) as error:
        AccountService(client, make_config()).get_currency()

    assert error.value.resource_type == "Ad Account"
    assert error.value.resource_id == ACCOUNT_ID


def test_it_retrieves_and_normalises_the_configured_account() -> None:
    client = FakeMetaClient(Response(status_code=200, body=account_body()))

    account = AccountService(client, make_config()).get()

    assert account.id == ACCOUNT_ID
    assert account.name == "Triizync Solution Ad account"
    assert account.account_id == "4274485329463051"
    assert account.account_status == 1
    assert account.currency == "BDT"
    assert account.timezone_name == "Europe/London"

    request = client.last_request
    assert request.path == f"/v26.0/{ACCOUNT_ID}"
    assert request.query == {"fields": "id,name,account_id,account_status,currency,timezone_name"}


def test_it_rejects_malformed_account_responses() -> None:
    client = FakeMetaClient(Response(status_code=200, body={"id": ACCOUNT_ID}))

    with pytest.raises(UnexpectedResponseError):
        AccountService(client, make_config()).get()


@pytest.mark.parametrize(
    "overrides",
    [{"id": "act_999"}, {"account_id": "999"}],
    ids=["canonical ID", "numeric account ID"],
)
def test_it_rejects_responses_for_another_account(overrides: dict[str, str]) -> None:
    client = FakeMetaClient(Response(status_code=200, body=account_body(**overrides)))

    with pytest.raises(UnexpectedResponseError) as error:
        AccountService(client, make_config()).get()

    assert error.value.http_status == 200
    assert error.value.resource_type == "Ad Account"
    assert error.value.resource_id == ACCOUNT_ID


def test_optional_account_fields_may_be_absent() -> None:
    account = AccountNormalizer().normalize({"id": "act_1", "name": "Account", "account_id": "1"})

    assert account.account_status is None
    assert account.currency is None
    assert account.timezone_name is None


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"name": "Account", "account_id": "1"}, "id"),
        ({"id": "act_1", "account_id": "1"}, "name"),
        ({"id": "act_1", "name": "Account"}, "account_id"),
        ({"id": "act_1", "name": "Account", "account_id": "1", "account_status": "1"}, "account_status"),
    ],
    ids=["missing ID", "missing name", "missing account ID", "invalid status"],
)
def test_the_normalizer_rejects_malformed_account_fields(data: dict[str, object], field: str) -> None:
    with pytest.raises(UnexpectedResponseError, match=field):
        AccountNormalizer().normalize(data)


def test_it_produces_the_golden_requests() -> None:
    golden = load_request_fixture("entities")["account"]

    client = FakeMetaClient(
        Response(status_code=200, body=account_body()),
        Response(status_code=200, body=account_body()),
    )
    service = AccountService(client, make_config())

    service.get()
    service.get_currency()

    for case, request in zip(golden.values(), client.requests, strict=True):
        assert request.method == case["method"]
        assert request.path == case["path"]
        assert request.query == case["query"]
        assert encode_query(request.query) == case["encoded_query"]
