#!/usr/bin/env python3
"""Example 5: Insights performance reporting."""

from __future__ import annotations

import os
import sys

from metametrics import DateRange, InsightsLevel, InsightsQuery, MetaAds, MetaConfig, Metric
from metametrics.exceptions import MetaAdsError


def main() -> None:
    token = os.environ.get("METAMETRICS_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
    account_id = os.environ.get("METAMETRICS_AD_ACCOUNT_ID", "act_123456789")

    config = MetaConfig(access_token=token, ad_account_id=account_id, api_version="v26.0")

    with MetaAds(config) as meta:
        try:
            print("Querying campaign insights for September 2026...")
            query = InsightsQuery(
                level=InsightsLevel.CAMPAIGN,
                date_range=DateRange("2026-09-01", "2026-09-24"),
                metrics=[Metric.SPEND, Metric.IMPRESSIONS, Metric.CLICKS, Metric.ROAS, Metric.CTR],
            )
            response = meta.insights().get_response(query)
            print(f"Currency: {response.currency}")
            for row in response.data:
                print(
                    f"  {row.entity_name} | Spend: {row.spend} | ROAS: {row.roas} | "
                    f"Impressions: {row.impressions} | Clicks: {row.clicks}"
                )
        except MetaAdsError as exc:
            print(f"API Error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
