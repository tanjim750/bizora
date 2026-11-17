"""Tests for the MetaAds facade.

Ported from ``tests/Unit/MetaAdsTest.php``.
"""

from __future__ import annotations

from metametrics.account.service import AccountService
from metametrics.ad.service import AdService
from metametrics.adset.service import AdSetService
from metametrics.auth.service import AuthenticationService
from metametrics.campaign.service import CampaignService
from metametrics.client import Response
from metametrics.config import MetaConfig
from metametrics.hierarchy.service import HierarchyService
from metametrics.historical.service import HistoricalService
from metametrics.insights.service import InsightsService
from metametrics.meta_ads import MetaAds
from tests.support.fakes import FakeMetaClient


def make_config() -> MetaConfig:
    return MetaConfig(access_token="test-token", ad_account_id="act_123", api_version="v26.0")


def test_it_exposes_services_backed_by_the_injected_client() -> None:
    client = FakeMetaClient(
        Response(
            status_code=200,
            body={"id": "act_123", "name": "Facade Account", "account_id": "123"},
        )
    )
    meta = MetaAds(make_config(), client)

    assert meta.client() is client
    assert isinstance(meta.authentication(), AuthenticationService)
    assert isinstance(meta.account(), AccountService)
    assert isinstance(meta.campaigns(), CampaignService)
    assert isinstance(meta.ad_sets(), AdSetService)
    assert isinstance(meta.ads(), AdService)
    assert isinstance(meta.insights(), InsightsService)
    assert isinstance(meta.historical(), HistoricalService)
    assert isinstance(meta.hierarchy(), HierarchyService)

    assert meta.account().get().id == "act_123"
    assert client.request_count == 1


def test_the_shared_client_is_reused_across_accessors() -> None:
    client = FakeMetaClient()
    meta = MetaAds(make_config(), client)

    assert meta.authentication() is meta.authentication()
    assert meta.campaigns() is meta.campaigns()
    assert meta.ads() is meta.ads()


def test_it_closes_the_transport_it_owns() -> None:
    meta = MetaAds(make_config())

    with meta:
        pass

    meta.close()


def test_it_does_not_close_an_injected_client() -> None:
    client = FakeMetaClient()
    meta = MetaAds(make_config(), client)

    meta.close()

    assert client.request_count == 0
