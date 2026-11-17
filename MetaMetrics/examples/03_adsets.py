#!/usr/bin/env python3
"""Example 3: Querying Ad Sets and scoping by campaign."""

from __future__ import annotations

import os
import sys

from metametrics import MetaAds, MetaConfig
from metametrics.exceptions import MetaAdsError


def main() -> None:
    token = os.environ.get("METAMETRICS_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
    account_id = os.environ.get("METAMETRICS_AD_ACCOUNT_ID", "act_123456789")

    config = MetaConfig(access_token=token, ad_account_id=account_id, api_version="v26.0")

    with MetaAds(config) as meta:
        try:
            print("Listing all ad sets...")
            ad_sets = meta.ad_sets().all()
            for ad_set in ad_sets[:10]:
                print(f"  [{ad_set.id}] {ad_set.name} (Campaign: {ad_set.campaign_id})")
        except MetaAdsError as exc:
            print(f"API Error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
