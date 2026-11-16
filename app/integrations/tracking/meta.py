"""Meta Conversions API (CAPI) event mapper.

Pure transformation library. No network, no database, no models, no external SDKs.
Addresses risks R4 (configurable API version) and respects decision Q2 (PII disabled by default).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .normalizers import (
    clean_nulls,
    hash_sha256,
    normalize_city,
    normalize_country,
    normalize_dob,
    normalize_email,
    normalize_external_id,
    normalize_gender,
    normalize_name,
    normalize_phone,
    normalize_state,
    normalize_zip,
)

DEFAULT_META_API_VERSION = "v18.0"
META_ENDPOINT_TEMPLATE = "https://graph.facebook.com/{api_version}/{pixel_id}/events"


class MetaEventMapper:
    """Builds standard Meta Conversions API (CAPI) JSON payloads."""

    def __init__(
        self,
        pixel_id: str,
        api_version: str = DEFAULT_META_API_VERSION,
        default_country_code: Optional[str] = None,
        send_pii: bool = False,
    ):
        self.pixel_id = str(pixel_id).strip()
        self.api_version = api_version.strip()
        self.default_country_code = default_country_code
        self.send_pii = send_pii

    @property
    def endpoint_url(self) -> str:
        return META_ENDPOINT_TEMPLATE.format(
            api_version=self.api_version,
            pixel_id=self.pixel_id,
        )

    def build_payload(
        self,
        event_name: str,
        event_time: Optional[int] = None,
        event_id: Optional[str] = None,
        event_source_url: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
        test_event_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct a validated CAPI request body dictionary."""
        u = user_data or {}
        c = custom_data or {}
        now_ts = int(event_time or time.time())

        built_user_data = self._build_user_data(u, fbc=fbc, fbp=fbp)
        built_custom_data = self._build_custom_data(c)

        event_obj: Dict[str, Any] = {
            "event_name": event_name,
            "event_time": now_ts,
            "action_source": "website",
            "user_data": built_user_data,
        }

        if event_id:
            event_obj["event_id"] = str(event_id).strip()

        if event_source_url:
            event_obj["event_source_url"] = str(event_source_url).strip()

        if built_custom_data:
            event_obj["custom_data"] = built_custom_data

        payload: Dict[str, Any] = {
            "data": [event_obj],
        }

        if test_event_code:
            payload["test_event_code"] = str(test_event_code).strip()

        return clean_nulls(payload)

    def _build_user_data(
        self,
        user: Dict[str, Any],
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct user_data block.

        Under Q2, send_pii is False by default: personal identifiers are strictly omitted.
        Hashing logic is fully implemented and tested when send_pii=True.
        """
        data: Dict[str, Any] = {}

        # Technical web identifiers (always permitted if present)
        client_ip = user.get("client_ip_address") or user.get("ip")
        if client_ip:
            data["client_ip_address"] = str(client_ip).strip()

        client_ua = user.get("client_user_agent") or user.get("user_agent")
        if client_ua:
            data["client_user_agent"] = str(client_ua).strip()

        fb_click = fbc or user.get("fbc")
        if fb_click:
            data["fbc"] = str(fb_click).strip()

        fb_browser = fbp or user.get("fbp")
        if fb_browser:
            data["fbp"] = str(fb_browser).strip()

        # Personal identifiers: only included if send_pii is explicitly enabled (Q2)
        if self.send_pii:
            em = hash_sha256(normalize_email(user.get("email")))
            if em:
                data["em"] = [em]

            ph = hash_sha256(
                normalize_phone(
                    user.get("phone_number") or user.get("phone"),
                    default_country_code=self.default_country_code,
                )
            )
            if ph:
                data["ph"] = [ph]

            fn = hash_sha256(normalize_name(user.get("first_name")))
            if fn:
                data["fn"] = [fn]

            ln = hash_sha256(normalize_name(user.get("last_name")))
            if ln:
                data["ln"] = [ln]

            ct = hash_sha256(normalize_city(user.get("city")))
            if ct:
                data["ct"] = [ct]

            st = hash_sha256(normalize_state(user.get("state")))
            if st:
                data["st"] = [st]

            zp = hash_sha256(normalize_zip(user.get("zip_code") or user.get("zip")))
            if zp:
                data["zp"] = [zp]

            country = hash_sha256(normalize_country(user.get("country")))
            if country:
                data["country"] = [country]

            ext_id = hash_sha256(normalize_external_id(user.get("external_id")))
            if ext_id:
                data["external_id"] = [ext_id]

            ge = hash_sha256(normalize_gender(user.get("gender")))
            if ge:
                data["ge"] = [ge]

            db = hash_sha256(normalize_dob(user.get("date_of_birth") or user.get("dob")))
            if db:
                data["db"] = [db]

        return data

    def _build_custom_data(self, c: Dict[str, Any]) -> Dict[str, Any]:
        """Construct custom_data ecommerce and value payload."""
        custom: Dict[str, Any] = {}

        if c.get("currency"):
            custom["currency"] = str(c["currency"]).strip().upper()

        val = c.get("value")
        if val is not None:
            try:
                custom["value"] = float(val)
            except (ValueError, TypeError):
                pass

        if c.get("order_id"):
            custom["order_id"] = str(c["order_id"]).strip()

        if c.get("content_type"):
            custom["content_type"] = str(c["content_type"]).strip()

        raw_contents = c.get("contents")
        if isinstance(raw_contents, list):
            contents: List[Dict[str, Any]] = []
            for item in raw_contents:
                if isinstance(item, dict):
                    cid = item.get("id") or item.get("content_id")
                    if cid is not None:
                        entry: Dict[str, Any] = {"id": str(cid)}
                        qty = item.get("quantity")
                        if qty is not None:
                            try:
                                entry["quantity"] = int(qty)
                            except (ValueError, TypeError):
                                pass
                        item_price = item.get("item_price") or item.get("price")
                        if item_price is not None:
                            try:
                                entry["item_price"] = float(item_price)
                            except (ValueError, TypeError):
                                pass
                        contents.append(entry)
            if contents:
                custom["contents"] = contents

        raw_ids = c.get("content_ids")
        if isinstance(raw_ids, list):
            custom["content_ids"] = [str(i) for i in raw_ids if i is not None]
        elif custom.get("contents") and "content_ids" not in custom:
            custom["content_ids"] = [item["id"] for item in custom["contents"]]

        if c.get("num_items") is not None:
            try:
                custom["num_items"] = int(c["num_items"])
            except (ValueError, TypeError):
                pass

        if c.get("search_string"):
            custom["search_string"] = str(c["search_string"]).strip()

        return custom
