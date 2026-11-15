"""Event vocabulary and mapping from Bizora canonical events to provider event names.

Maps canonical stages (VIEW, CART, CHECKOUT, PURCHASE) and known event types
to Meta Conversions API, TikTok Events API, and Google Analytics 4 (Measurement Protocol).
Pure library; no models, no network, no database.
"""
from __future__ import annotations

from typing import Optional

# Closed sets of normalized event types matching app.business_intelligence.website
VIEW_EVENT_TYPES = frozenset({"VIEW", "PRODUCT_VIEW", "PAGE_VIEW"})
CART_EVENT_TYPES = frozenset({"ADD_TO_CART", "CART"})
CHECKOUT_EVENT_TYPES = frozenset({"CHECKOUT", "CHECKOUT_START", "BEGIN_CHECKOUT"})
PURCHASE_EVENT_TYPES = frozenset({"PURCHASE", "ORDER", "CHECKOUT_COMPLETE", "ORDER_COMPLETE"})
EXPERIENCE_EVENT_TYPES = frozenset({"RAGE_CLICK", "DEAD_CLICK", "QUICK_BACK", "ERROR", "LATENCY"})

# Canonical funnel stages
STAGE_VIEW = "VIEW"
STAGE_CART = "CART"
STAGE_CHECKOUT = "CHECKOUT"
STAGE_PURCHASE = "PURCHASE"

# Meta Event Mappings
META_EVENT_MAP = {
    "PAGE_VIEW": "PageView",
    "VIEW": "PageView",
    "PRODUCT_VIEW": "ViewContent",
    "ADD_TO_CART": "AddToCart",
    "CART": "AddToCart",
    "CHECKOUT": "InitiateCheckout",
    "CHECKOUT_START": "InitiateCheckout",
    "BEGIN_CHECKOUT": "InitiateCheckout",
    "PURCHASE": "Purchase",
    "ORDER": "Purchase",
    "CHECKOUT_COMPLETE": "Purchase",
    "ORDER_COMPLETE": "Purchase",
}

# TikTok Event Mappings (TikTok standard events)
TIKTOK_EVENT_MAP = {
    "PAGE_VIEW": "PageView",
    "VIEW": "PageView",
    "PRODUCT_VIEW": "ViewContent",
    "ADD_TO_CART": "AddToCart",
    "CART": "AddToCart",
    "CHECKOUT": "InitiateCheckout",
    "CHECKOUT_START": "InitiateCheckout",
    "BEGIN_CHECKOUT": "InitiateCheckout",
    "PURCHASE": "CompletePayment",
    "ORDER": "CompletePayment",
    "CHECKOUT_COMPLETE": "CompletePayment",
    "ORDER_COMPLETE": "CompletePayment",
}

# GA4 Recommended Event Mappings
GA4_EVENT_MAP = {
    "PAGE_VIEW": "page_view",
    "VIEW": "page_view",
    "PRODUCT_VIEW": "view_item",
    "ADD_TO_CART": "add_to_cart",
    "CART": "add_to_cart",
    "CHECKOUT": "begin_checkout",
    "CHECKOUT_START": "begin_checkout",
    "BEGIN_CHECKOUT": "begin_checkout",
    "PURCHASE": "purchase",
    "ORDER": "purchase",
    "CHECKOUT_COMPLETE": "purchase",
    "ORDER_COMPLETE": "purchase",
    # Direct Meta -> GA4 mapping compatibility
    "PageView": "page_view",
    "ViewContent": "view_item",
    "ViewCategory": "view_item_list",
    "AddToCart": "add_to_cart",
    "AddToWishlist": "add_to_wishlist",
    "InitiateCheckout": "begin_checkout",
    "AddPaymentInfo": "add_payment_info",
    "Purchase": "purchase",
    "Lead": "generate_lead",
    "CompleteRegistration": "sign_up",
    "Search": "search",
}


def normalize_event_stage(raw_event_type: str | None) -> Optional[str]:
    """Map raw event type string to canonical funnel stage, or None if unmapped."""
    if not raw_event_type:
        return None
    normalized = str(raw_event_type).strip().upper()
    if normalized in VIEW_EVENT_TYPES:
        return STAGE_VIEW
    if normalized in CART_EVENT_TYPES:
        return STAGE_CART
    if normalized in CHECKOUT_EVENT_TYPES:
        return STAGE_CHECKOUT
    if normalized in PURCHASE_EVENT_TYPES:
        return STAGE_PURCHASE
    return None


def map_event_name_for_provider(
    raw_event_type: str | None,
    provider: str,
    has_product: bool = False,
) -> str:
    """Map Bizora event type to provider-specific event name.

    Supported providers: 'meta', 'tiktok', 'ga4'.
    If has_product is True and stage is VIEW, maps to ViewContent / view_item.
    """
    if not raw_event_type:
        return "Custom"

    event_upper = str(raw_event_type).strip().upper()
    provider_lower = provider.strip().lower()

    if provider_lower in {"meta", "facebook", "meta_ads"}:
        if event_upper in VIEW_EVENT_TYPES and has_product:
            return "ViewContent"
        return META_EVENT_MAP.get(event_upper, str(raw_event_type).strip())

    if provider_lower in {"tiktok", "tiktok_ads"}:
        if event_upper in VIEW_EVENT_TYPES and has_product:
            return "ViewContent"
        return TIKTOK_EVENT_MAP.get(event_upper, str(raw_event_type).strip())

    if provider_lower in {"ga4", "google_analytics_4", "analytics"}:
        if event_upper in VIEW_EVENT_TYPES and has_product:
            return "view_item"
        # Check direct upper match, or raw name match (e.g. 'AddToCart' -> 'add_to_cart')
        return GA4_EVENT_MAP.get(
            event_upper,
            GA4_EVENT_MAP.get(str(raw_event_type).strip(), str(raw_event_type).strip().lower()),
        )

    return str(raw_event_type).strip()
