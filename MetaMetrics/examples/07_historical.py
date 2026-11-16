#!/usr/bin/env python3
"""Example 7: Historical delivery analysis."""

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
            print(f"Discovering historical delivered campaigns for {period.since} to {period.until}...")
            results = meta.historical().campaigns(period)
            for res in results:
                evidence = res.delivery_evidence.indicators()
                print(f"  [{res.entity_id}] {res.entity_name} - Evidence: {evidence}")
        except MetaAdsError as exc:
            print(f"API Error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
