"""Google Analytics 4 (Measurement Protocol) event mapper.

Pure transformation library. No network, no database, no models, no external SDKs.
Fixes risk R3 by distinguishing live collection endpoint from debug validation endpoint.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .normalizers import clean_nulls
from .vocabulary import map_event_name_for_provider

GA4_COLLECT_ENDPOINT = "https://www.google-analytics.com/mp/collect"
GA4_DEBUG_ENDPOINT = "https://www.google-analytics.com/debug/mp/collect"


class Ga4EventMapper:
    """Builds standard GA4 Measurement Protocol JSON payloads and query endpoints."""

    def __init__(
        self,
        measurement_id: str,
        api_secret: str,
        test_mode: bool = False,
    ):
        self.measurement_id = str(measurement_id).strip()
        self.api_secret = str(api_secret).strip()
        self.test_mode = test_mode

    @property
    def base_endpoint_url(self) -> str:
        """Returns debug endpoint in test_mode, collection endpoint for live."""
        return GA4_DEBUG_ENDPOINT if self.test_mode else GA4_COLLECT_ENDPOINT

    @property
    def request_url(self) -> str:
        """Complete HTTP endpoint URL with required query credentials."""
        from urllib.parse import urlencode

        query = urlencode(
            {
                "measurement_id": self.measurement_id,
                "api_secret": self.api_secret,
            }
        )
        return f"{self.base_endpoint_url}?{query}"

    def build_payload(
        self,
        event_name: str,
        client_id: str,
        event_time: Optional[int] = None,
        event_id: Optional[str] = None,
        event_source_url: Optional[str] = None,
        referrer_url: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[Any] = None,
        engagement_time_msec: Optional[int] = None,
        properties: Optional[Dict[str, Any]] = None,
        has_product: bool = False,
    ) -> Dict[str, Any]:
        """Construct a validated GA4 Measurement Protocol payload dictionary."""
        cid = str(client_id).strip() if client_id else ""
        if not cid and not user_id:
            raise ValueError("GA4 requires client_id or user_id.")

        mapped_name = map_event_name_for_provider(event_name, provider="ga4", has_product=has_product)
        if not mapped_name:
            raise ValueError("GA4 requires event_name.")

        now_ts = int(event_time or time.time())
        p = properties or {}

        params: Dict[str, Any] = {}

        if event_source_url:
            params["page_location"] = str(event_source_url).strip()
        if referrer_url:
            params["page_referrer"] = str(referrer_url).strip()

        if event_id:
            params["event_id"] = str(event_id).strip()

        if session_id is not None:
            try:
                params["session_id"] = int(session_id)
            except (ValueError, TypeError):
                params["session_id"] = str(session_id).strip()

        if engagement_time_msec is not None:
            try:
                params["engagement_time_msec"] = int(engagement_time_msec)
            except (ValueError, TypeError):
                pass

        # Top-level ecommerce properties
        if p.get("currency"):
            params["currency"] = str(p["currency"]).strip().upper()

        val = p.get("value")
        if val is not None:
            try:
                params["value"] = float(val)
            except (ValueError, TypeError):
                pass

        txn_id = p.get("transaction_id") or p.get("order_id")
        if txn_id:
            params["transaction_id"] = str(txn_id).strip()

        # Build items list from contents or product info
        items = self._build_items(p.get("contents") or [])
        if items:
            params["items"] = items

        # Include remaining custom parameters that are non-ecommerce
        for k, v in p.items():
            if k in {"contents", "content_ids", "value", "currency", "order_id", "transaction_id"}:
                continue
            if k not in params and v is not None:
                params[k] = v

        payload: Dict[str, Any] = {
            "client_id": cid or str(user_id),
            "events": [
                {
                    "name": mapped_name,
                    "params": clean_nulls(params),
                }
            ],
            "timestamp_micros": now_ts * 1_000_000,
        }

        if user_id:
            payload["user_id"] = str(user_id).strip()

        return clean_nulls(payload)

    def _build_items(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map contents array to GA4 items schema."""
        items: List[Dict[str, Any]] = []
        for c in contents:
            if not isinstance(c, dict):
                continue
            item_id = c.get("item_id") or c.get("id") or c.get("content_id") or c.get("product_id") or c.get("sku")
            item: Dict[str, Any] = {}
            if item_id is not None:
                item["item_id"] = str(item_id).strip()

            name = c.get("item_name") or c.get("content_name") or c.get("name")
            if name:
                item["item_name"] = str(name).strip()

            price = c.get("price") or c.get("item_price")
            if price is not None:
                try:
                    item["price"] = float(price)
                except (ValueError, TypeError):
                    pass

            qty = c.get("quantity")
            if qty is not None:
                try:
                    item["quantity"] = int(qty)
                except (ValueError, TypeError):
                    pass

            if c.get("item_category"):
                item["item_category"] = str(c["item_category"]).strip()
            if c.get("item_variant"):
                item["item_variant"] = str(c["item_variant"]).strip()

            if item:
                items.append(item)

        return items
