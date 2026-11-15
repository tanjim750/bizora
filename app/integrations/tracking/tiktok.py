"""TikTok Events API event mapper.

Pure transformation library. No network, no database, no models, no external SDKs.
Removes legacy third-party partner branding and respects decision Q2 (PII disabled by default).
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

TIKTOK_EVENTS_ENDPOINT = "https://business-api.tiktok.com/open_api/v1.3/event/track/"
DEFAULT_TIKTOK_PARTNER_NAME = "Bizora"


class TikTokEventMapper:
    """Builds standard TikTok Events API v1.3 JSON payloads."""

    def __init__(
        self,
        pixel_code: str,
        partner_name: Optional[str] = DEFAULT_TIKTOK_PARTNER_NAME,
        default_country_code: Optional[str] = None,
        send_pii: bool = False,
    ):
        self.pixel_code = str(pixel_code).strip()
        self.partner_name = partner_name.strip() if partner_name else None
        self.default_country_code = default_country_code
        self.send_pii = send_pii

    @property
    def endpoint_url(self) -> str:
        return TIKTOK_EVENTS_ENDPOINT

    def build_payload(
        self,
        event_name: str,
        event_time: Optional[int] = None,
        event_id: Optional[str] = None,
        event_source_url: Optional[str] = None,
        referrer_url: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
        properties: Optional[Dict[str, Any]] = None,
        ttclid: Optional[str] = None,
        ttp: Optional[str] = None,
        test_event_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct a validated TikTok Events API request body."""
        u = user_data or {}
        p = properties or {}
        now_ts = int(event_time or time.time())

        user_block = self._build_user_data(u, ttclid=ttclid, ttp=ttp)
        props_block = self._build_properties(p)
        page_block = self._build_page(event_source_url, referrer_url)

        event_data: Dict[str, Any] = {
            "event": event_name,
            "event_time": now_ts,
        }

        if event_id:
            event_data["event_id"] = str(event_id).strip()

        if user_block:
            event_data["user"] = user_block

        if props_block:
            event_data["properties"] = props_block

        if page_block:
            event_data["page"] = page_block

        payload: Dict[str, Any] = {
            "event_source": "web",
            "event_source_id": self.pixel_code,
            "data": [event_data],
        }

        if self.partner_name:
            payload["partner_name"] = self.partner_name

        if test_event_code:
            payload["test_event_code"] = str(test_event_code).strip()

        return clean_nulls(payload)

    def _build_user_data(
        self,
        user: Dict[str, Any],
        ttclid: Optional[str] = None,
        ttp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct user block for TikTok Events API.

        Under Q2, send_pii is False by default: personal identifiers are strictly omitted.
        """
        data: Dict[str, Any] = {}

        ip = user.get("ip") or user.get("client_ip_address")
        if ip:
            data["ip"] = str(ip).strip()

        ua = user.get("user_agent") or user.get("client_user_agent")
        if ua:
            data["user_agent"] = str(ua).strip()

        click_id = ttclid or user.get("ttclid")
        if click_id:
            data["ttclid"] = str(click_id).strip()

        cookie_id = ttp or user.get("ttp")
        if cookie_id:
            data["ttp"] = str(cookie_id).strip()

        if self.send_pii:
            em = hash_sha256(normalize_email(user.get("email")))
            if em:
                data["email"] = em

            ph = hash_sha256(
                normalize_phone(
                    user.get("phone_number") or user.get("phone"),
                    default_country_code=self.default_country_code,
                )
            )
            if ph:
                data["phone_number"] = ph

            fn = hash_sha256(normalize_name(user.get("first_name")))
            if fn:
                data["first_name"] = fn

            ln = hash_sha256(normalize_name(user.get("last_name")))
            if ln:
                data["last_name"] = ln

            ct = hash_sha256(normalize_city(user.get("city")))
            if ct:
                data["city"] = ct

            st = hash_sha256(normalize_state(user.get("state")))
            if st:
                data["state"] = st

            zp = hash_sha256(normalize_zip(user.get("zip_code") or user.get("zip")))
            if zp:
                data["zip_code"] = zp

            country = hash_sha256(normalize_country(user.get("country")))
            if country:
                data["country"] = country

            ext_id = hash_sha256(normalize_external_id(user.get("external_id")))
            if ext_id:
                data["external_id"] = ext_id

            ge = hash_sha256(normalize_gender(user.get("gender")))
            if ge:
                data["gender"] = ge

            db = hash_sha256(normalize_dob(user.get("date_of_birth") or user.get("dob")))
            if db:
                data["date_of_birth"] = db

        return data

    def _build_properties(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """Construct properties object."""
        props: Dict[str, Any] = {}

        if p.get("currency"):
            props["currency"] = str(p["currency"]).strip().upper()

        val = p.get("value")
        if val is not None:
            try:
                props["value"] = float(val)
            except (ValueError, TypeError):
                pass

        if p.get("order_id"):
            props["order_id"] = str(p["order_id"]).strip()

        if p.get("content_type"):
            props["content_type"] = str(p["content_type"]).strip()

        raw_contents = p.get("contents")
        if isinstance(raw_contents, list):
            contents: List[Dict[str, Any]] = []
            for item in raw_contents:
                if isinstance(item, dict):
                    cid = item.get("id") or item.get("content_id")
                    if cid is not None:
                        entry: Dict[str, Any] = {"content_id": str(cid)}
                        name = item.get("content_name") or item.get("name")
                        if name:
                            entry["content_name"] = str(name).strip()
                        qty = item.get("quantity")
                        if qty is not None:
                            try:
                                entry["quantity"] = int(qty)
                            except (ValueError, TypeError):
                                pass
                        item_price = item.get("price") or item.get("item_price")
                        if item_price is not None:
                            try:
                                entry["price"] = float(item_price)
                            except (ValueError, TypeError):
                                pass
                        contents.append(entry)
            if contents:
                props["contents"] = contents

        if p.get("num_items") is not None:
            try:
                props["num_items"] = int(p["num_items"])
            except (ValueError, TypeError):
                pass

        if p.get("search_string"):
            props["search_string"] = str(p["search_string"]).strip()

        return props

    def _build_page(
        self,
        event_source_url: Optional[str] = None,
        referrer_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct page object."""
        page: Dict[str, Any] = {}
        if event_source_url:
            page["url"] = str(event_source_url).strip()
        if referrer_url:
            page["referrer"] = str(referrer_url).strip()
        return page
