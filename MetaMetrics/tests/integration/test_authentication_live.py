"""Integration tests for Authentication against the live Meta Marketing API.

Ported from ``tests/Integration/Authentication/AuthenticationServiceTest.php``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from metametrics.auth.service import AuthenticationService
from metametrics.client import MetaClient, Request
from metametrics.config import MetaConfig


def _load_live_credentials() -> dict[str, str] | None:
    # First check environment variables
    env_token = os.environ.get("METAMETRICS_ACCESS_TOKEN")
    env_act = os.environ.get("METAMETRICS_AD_ACCOUNT_ID")
    env_ver = os.environ.get("METAMETRICS_API_VERSION", "v26.0")

    if env_token and env_act:
        return {
            "access_token": env_token,
            "ad_account_id": env_act,
            "api_version": env_ver,
        }

    # Second check credentials.local.json in tests root
    cred_file = Path(__file__).parent.parent / "credentials.local.json"
    if cred_file.is_file():
        with cred_file.open(encoding="utf-8") as handle:
            data: dict[str, Any] = json.load(handle)
            if data.get("access_token") and data.get("ad_account_id"):
                return {
                    "access_token": str(data["access_token"]),
                    "ad_account_id": str(data["ad_account_id"]),
                    "api_version": str(data.get("api_version", "v26.0")),
                }

    return None


@pytest.mark.integration
def test_configured_credentials_can_access_the_ad_account() -> None:
    creds = _load_live_credentials()
    if creds is None or not creds.get("access_token"):
        pytest.skip(
            "Live Meta tests require METAMETRICS_ACCESS_TOKEN and METAMETRICS_AD_ACCOUNT_ID "
            "or tests/credentials.local.json"
        )

    config = MetaConfig(
        access_token=creds["access_token"],
        ad_account_id=creds["ad_account_id"],
        api_version=creds["api_version"],
    )
    client = MetaClient(config)

    try:
        service = AuthenticationService(client, config)
        result = service.validate()

        assert result.authenticated is True
        assert result.account_accessible is True
        assert result.account_id == config.ad_account_id

        response = client.send(
            Request(
                method="GET",
                path=f"/{config.api_version}/{config.ad_account_id}",
                query={"fields": "id,name,account_id,account_status,currency,timezone_name"},
            )
        )

        assert response.status_code == 200
        assert isinstance(response.body, dict)
        assert response.body["id"] == config.ad_account_id
    finally:
        client.close()
