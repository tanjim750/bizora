"""The MetaAds entry point."""

from __future__ import annotations

from metametrics.account.service import AccountService
from metametrics.ad.service import AdService
from metametrics.adset.service import AdSetService
from metametrics.auth.service import AuthenticationService
from metametrics.campaign.service import CampaignService
from metametrics.client import MetaClient, MetaClientProtocol
from metametrics.config import MetaConfig
from metametrics.hierarchy.service import HierarchyService
from metametrics.historical.service import HistoricalService
from metametrics.insights.service import InsightsService

__all__ = ["MetaAds"]


class MetaAds:
    """Composes the Meta API services around a single shared client.

    The client is optional; when omitted a default :class:`~metametrics.client.MetaClient`
    is created from the configuration and is closed together with the facade.

    Every accessor returns the same service instance for the lifetime of the
    facade, so collaborators such as the paginator are shared.
    """

    def __init__(self, config: MetaConfig, client: MetaClientProtocol | None = None) -> None:
        self.config = config
        self._client = client if client is not None else MetaClient(config)
        self._owns_client = client is None

        self._authentication = AuthenticationService(self._client, self.config)
        self._account = AccountService(self._client, self.config)
        self._campaigns = CampaignService(self._client, self.config)
        self._ad_sets = AdSetService(self._client, self.config)
        self._ads = AdService(self._client, self.config)
        self._insights = InsightsService(self._client, self.config)
        self._historical = HistoricalService(self._insights)
        self._hierarchy = HierarchyService(self._historical)

    def authentication(self) -> AuthenticationService:
        """The Ad Account authentication service."""
        return self._authentication

    def account(self) -> AccountService:
        """The Ad Account service."""
        return self._account

    def campaigns(self) -> CampaignService:
        """The Campaign service."""
        return self._campaigns

    def ad_sets(self) -> AdSetService:
        """The Ad Set service."""
        return self._ad_sets

    def ads(self) -> AdService:
        """The Ad service."""
        return self._ads

    def insights(self) -> InsightsService:
        """The Insights service."""
        return self._insights

    def historical(self) -> HistoricalService:
        """The Historical analysis service."""
        return self._historical

    def hierarchy(self) -> HierarchyService:
        """The Hierarchy service."""
        return self._hierarchy

    def client(self) -> MetaClientProtocol:
        """The shared low-level client."""
        return self._client

    def close(self) -> None:
        """Close the underlying transport when this facade owns it."""
        if self._owns_client:
            close = getattr(self._client, "close", None)
            if callable(close):
                close()

    def __enter__(self) -> MetaAds:
        return self

    def __exit__(self, *exception_info: object) -> None:
        self.close()
