#!/usr/bin/env python3
"""Example 4: Listing and finding ads."""

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
            print("Listing ads...")
            ads = meta.ads().all()
            for ad in ads[:10]:
                print(f"  [{ad.id}] {ad.name} (AdSet: {ad.adset_id})")
        except MetaAdsError as exc:
            print(f"API Error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
