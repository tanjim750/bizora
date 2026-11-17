#!/usr/bin/env python3
"""Example 2: Listing and finding campaigns with typed fields and filters."""

from __future__ import annotations

import os
import sys

from metametrics import Fields, Filter, FilterOperator, MetaAds, MetaConfig
from metametrics.campaign import CampaignQuery
from metametrics.exceptions import MetaAdsError


def main() -> None:
    token = os.environ.get("METAMETRICS_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
    account_id = os.environ.get("METAMETRICS_AD_ACCOUNT_ID", "act_123456789")

    config = MetaConfig(access_token=token, ad_account_id=account_id, api_version="v26.0")

    with MetaAds(config) as meta:
        try:
            print("Listing active campaigns...")
            query = CampaignQuery(
                fields=Fields(["id", "name", "status", "objective", "created_time"]),
                filters=[Filter("effective_status", FilterOperator.IN, ("ACTIVE", "PAUSED"))],
                limit=10,
            )
            campaigns = meta.campaigns().all(query)
            for campaign in campaigns:
                print(f"  [{campaign.id}] {campaign.name} - Objective: {campaign.objective}")

            if campaigns:
                target_id = campaigns[0].id
                print(f"\nFinding campaign by ID: {target_id}...")
                found = meta.campaigns().find(target_id)
                print(f"  Found: {found.name} (Status: {found.status})")
        except MetaAdsError as exc:
            print(f"API Error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
