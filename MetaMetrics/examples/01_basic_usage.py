#!/usr/bin/env python3
"""Example 1: Basic initialization, authentication verification, and account metadata."""

from __future__ import annotations

import os
import sys

from metametrics import MetaAds, MetaConfig
from metametrics.exceptions import MetaAdsError


def main() -> None:
    token = os.environ.get("METAMETRICS_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
    account_id = os.environ.get("METAMETRICS_AD_ACCOUNT_ID", "act_123456789")
    api_version = os.environ.get("METAMETRICS_API_VERSION", "v26.0")

    config = MetaConfig(access_token=token, ad_account_id=account_id, api_version=api_version)

    print(f"Config initialized: account={config.ad_account_id}, version={config.api_version}")

    with MetaAds(config) as meta:
        try:
            print("Validating access token...")
            auth = meta.authentication().validate()
            print(f"  Authenticated: {auth.authenticated}")
            print(f"  Account Accessible: {auth.account_accessible}")

            print("Fetching account details...")
            account = meta.account().get()
            print(f"  Account Name: {account.name}")
            print(f"  Currency: {account.currency}")
            print(f"  Timezone: {account.timezone_name}")
        except MetaAdsError as exc:
            print(f"API Error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
