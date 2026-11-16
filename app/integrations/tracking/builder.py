"""Event builder that transforms canonical WebsiteEvent rows into provider tracking payloads.

Reads canonical WebsiteEvent, Order, OrderItem, Product, WebsiteSession, and WebsiteVisitor.
Enforces decision Q2 (no personal identifiers sent) and tenant boundary isolation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.models import IntegrationConnection, OrderItem, WebsiteEvent

from .ga4 import Ga4EventMapper
from .meta import MetaEventMapper
from .tiktok import TikTokEventMapper
from .vocabulary import map_event_name_for_provider


def identify_provider(connection: IntegrationConnection) -> str:
    """Identify provider type ('meta', 'tiktok', 'ga4') from connection source key."""
    key = str(connection.integration_source.key).strip().lower()
    if key in {"meta_ads", "meta", "facebook"}:
        return "meta"
    if key in {"tiktok_ads", "tiktok"}:
        return "tiktok"
    if key in {"ga4", "google_analytics_4", "analytics"}:
        return "ga4"
    return key


def extract_event_contents(event: WebsiteEvent) -> List[Dict[str, Any]]:
    """Extract item/product contents from WebsiteEvent, linked Order, or linked Product."""
    contents: List[Dict[str, Any]] = []

    # 1. From linked Order items
    if event.order_id:
        items = OrderItem.objects.filter(order_id=event.order_id).select_related("product")
        for item in items:
            prod = item.product
            cid = prod.sku if (prod and prod.sku) else str(item.product_id or item.pk)
            name = prod.name if prod else ""
            entry = {
                "id": cid,
                "content_id": cid,
                "item_id": cid,
                "name": name,
                "content_name": name,
                "item_name": name,
                "quantity": int(item.quantity) if item.quantity else 1,
                "price": float(item.unit_price) if item.unit_price is not None else 0.0,
                "item_price": float(item.unit_price) if item.unit_price is not None else 0.0,
            }
            contents.append(entry)
        if contents:
            return contents

    # 2. From linked single Product
    if event.product_id:
        prod = event.product
        cid = prod.sku if (prod and prod.sku) else str(event.product_id)
        name = prod.name if prod else ""
        price_val = float(event.event_value or prod.price or 0.0) if prod else float(event.event_value or 0.0)
        return [
            {
                "id": cid,
                "content_id": cid,
                "item_id": cid,
                "name": name,
                "content_name": name,
                "item_name": name,
                "quantity": 1,
                "price": price_val,
                "item_price": price_val,
            }
        ]

    # 3. From event.properties if present
    props = event.properties if isinstance(event.properties, dict) else {}
    raw_contents = props.get("contents") or props.get("items")
    if isinstance(raw_contents, list):
        for c in raw_contents:
            if isinstance(c, dict):
                cid = str(c.get("id") or c.get("content_id") or c.get("item_id") or "")
                if cid:
                    contents.append(
                        {
                            "id": cid,
                            "content_id": cid,
                            "item_id": cid,
                            "name": str(c.get("name") or c.get("content_name") or c.get("item_name") or ""),
                            "content_name": str(c.get("name") or c.get("content_name") or c.get("item_name") or ""),
                            "item_name": str(c.get("name") or c.get("content_name") or c.get("item_name") or ""),
                            "quantity": int(c.get("quantity") or 1),
                            "price": float(c.get("price") or c.get("item_price") or 0.0),
                            "item_price": float(c.get("price") or c.get("item_price") or 0.0),
                        }
                    )
    return contents


def build_tracking_payload(
    connection: IntegrationConnection,
    event: WebsiteEvent,
    tracking_config: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """Build provider-specific payload for a canonical WebsiteEvent.

    Returns (provider_type, endpoint_url, payload_dict).
    Validates tenant isolation: event must belong to connection.business_id.
    Strictly suppresses PII per decision Q2.
    """
    session = event.session
    if session.business_id != connection.business_id:
        raise ValueError(
            f"Tenant boundary violation: Event {event.pk} belongs to business "
            f"{session.business_id}, not connection business {connection.business_id}."
        )

    t_cfg = tracking_config or (
        connection.config.get("tracking", {})
        if isinstance(connection.config, dict) and isinstance(connection.config.get("tracking"), dict)
        else {}
    )

    provider_type = identify_provider(connection)
    event_id = f"bizora_we_{event.pk}"
    event_time = int(event.occurred_at.timestamp())
    event_source_url = event.page_url or session.landing_page_url or ""
    has_product = bool(event.product_id or event.order_id)
    contents = extract_event_contents(event)

    currency = event.currency
    if not currency and event.order_id and event.order.currency:
        currency = event.order.currency
    if not currency and connection.business.currency:
        currency = connection.business.currency
    currency = (currency or "BDT").upper()

    value = float(event.event_value) if event.event_value is not None else None
    if value is None and event.order_id and event.order.total_amount is not None:
        value = float(event.order.total_amount)

    order_id = str(event.order.order_number or event.order.pk) if event.order_id else None

    # Properties block for mappers
    props = dict(event.properties) if isinstance(event.properties, dict) else {}
    props["currency"] = currency
    if value is not None:
        props["value"] = value
    if order_id:
        props["order_id"] = order_id
        props["transaction_id"] = order_id
    if contents:
        props["contents"] = contents
        props["content_ids"] = [c["id"] for c in contents]

    # Technical identifiers from properties / session
    user_data: Dict[str, Any] = {}
    ip = props.get("client_ip_address") or props.get("ip")
    if ip:
        user_data["client_ip_address"] = ip
        user_data["ip"] = ip
    ua = props.get("client_user_agent") or props.get("user_agent")
    if ua:
        user_data["client_user_agent"] = ua
        user_data["user_agent"] = ua

    fbc = props.get("fbc") or props.get("fb_click_id")
    fbp = props.get("fbp") or props.get("fb_browser_id")
    ttclid = props.get("ttclid") or props.get("tiktok_click_id")
    ttp = props.get("ttp") or props.get("tiktok_browser_id")

    # Q2: send_pii is False by default; no personal data extracted or sent
    send_pii = bool(t_cfg.get("send_pii", False))
    country_code = t_cfg.get("default_country_code")
    test_mode = bool(t_cfg.get("test_mode", False))
    test_event_code = t_cfg.get("test_event_code")

    if provider_type == "meta":
        pixel_id = connection.external_account_id or ""
        api_version = t_cfg.get("api_version", "v18.0")
        mapper = MetaEventMapper(
            pixel_id=pixel_id,
            api_version=api_version,
            default_country_code=country_code,
            send_pii=send_pii,
        )
        event_name = map_event_name_for_provider(event.event_type, "meta", has_product=has_product)
        payload = mapper.build_payload(
            event_name=event_name,
            event_time=event_time,
            event_id=event_id,
            event_source_url=event_source_url,
            user_data=user_data,
            custom_data=props,
            fbc=fbc,
            fbp=fbp,
            test_event_code=test_event_code if test_mode else None,
        )
        return provider_type, mapper.endpoint_url, payload

    elif provider_type == "tiktok":
        pixel_code = connection.external_account_id or ""
        partner_name = t_cfg.get("partner_name", "Bizora")
        mapper_tt = TikTokEventMapper(
            pixel_code=pixel_code,
            partner_name=partner_name,
            default_country_code=country_code,
            send_pii=send_pii,
        )
        event_name = map_event_name_for_provider(event.event_type, "tiktok", has_product=has_product)
        payload = mapper_tt.build_payload(
            event_name=event_name,
            event_time=event_time,
            event_id=event_id,
            event_source_url=event_source_url,
            referrer_url=props.get("referrer"),
            user_data=user_data,
            properties=props,
            ttclid=ttclid,
            ttp=ttp,
            test_event_code=test_event_code if test_mode else None,
        )
        return provider_type, mapper_tt.endpoint_url, payload

    elif provider_type == "ga4":
        measurement_id = connection.external_account_id or ""
        api_secret = t_cfg.get("api_secret", "")
        mapper_ga4 = Ga4EventMapper(
            measurement_id=measurement_id,
            api_secret=api_secret,
            test_mode=test_mode,
        )
        client_id = event.visitor.visitor_key if event.visitor_id else f"vis_{session.pk}_{event.pk}"
        payload = mapper_ga4.build_payload(
            event_name=event.event_type,
            client_id=client_id,
            event_time=event_time,
            event_id=event_id,
            event_source_url=event_source_url,
            referrer_url=props.get("referrer"),
            session_id=event.session_id,
            properties=props,
            has_product=has_product,
        )
        return provider_type, mapper_ga4.request_url, payload

    else:
        raise ValueError(f"Unsupported tracking provider key: {connection.integration_source.key}")
