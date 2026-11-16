#!/usr/bin/env python3
"""Example 8: Reconstructing and navigating entity hierarchy trees."""

from __future__ import annotations

import os
import sys

from metametrics import DateRange, MetaAds, MetaConfig
from metametrics.exceptions import MetaAdsError


def main() -> None:
    token = os.environ.get("METAMETRICS_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
    account_id = os.environ.get("METAMETRICS_AD_ACCOUNT_ID", "act_123456789")

    config = MetaConfig(access_token=token, ad_account_id=account_id, api_version="v26.0")

    with MetaAds(config) as meta:
        try:
            period = DateRange("2026-09-01", "2026-09-24")
            print("Assembling hierarchy tree...")
            tree = meta.hierarchy().historical(period)

            print(f"Currency: {tree.currency}")
            print(f"Campaigns ({len(tree.campaigns)}):")
            for camp in tree.campaigns:
                print(f"  └── Campaign: {camp.entity_id}")
                for adset in camp.children:
                    print(f"        └── AdSet: {adset.entity_id}")
                    for ad in adset.children:
                        print(f"              └── Ad: {ad.entity_id}")

            if tree.unattached_ad_sets:
                print(f"Unattached Ad Sets: {[n.entity_id for n in tree.unattached_ad_sets]}")
            if tree.unattached_ads:
                print(f"Unattached Ads: {[n.entity_id for n in tree.unattached_ads]}")
        except MetaAdsError as exc:
            print(f"API Error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
