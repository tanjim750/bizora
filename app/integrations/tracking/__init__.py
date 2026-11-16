"""Tracking integration package for Bizora.

Pure mappers and event connectivity adapters for Meta CAPI, TikTok Events API, and GA4.
"""
from .ga4 import Ga4EventMapper
from .meta import MetaEventMapper
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
from .tiktok import TikTokEventMapper
from .vocabulary import (
    CART_EVENT_TYPES,
    CHECKOUT_EVENT_TYPES,
    EXPERIENCE_EVENT_TYPES,
    PURCHASE_EVENT_TYPES,
    VIEW_EVENT_TYPES,
    map_event_name_for_provider,
    normalize_event_stage,
)

__all__ = [
    "MetaEventMapper",
    "TikTokEventMapper",
    "Ga4EventMapper",
    "hash_sha256",
    "normalize_email",
    "normalize_phone",
    "normalize_name",
    "normalize_city",
    "normalize_state",
    "normalize_country",
    "normalize_zip",
    "normalize_gender",
    "normalize_dob",
    "normalize_external_id",
    "clean_nulls",
    "map_event_name_for_provider",
    "normalize_event_stage",
    "VIEW_EVENT_TYPES",
    "CART_EVENT_TYPES",
    "CHECKOUT_EVENT_TYPES",
    "PURCHASE_EVENT_TYPES",
    "EXPERIENCE_EVENT_TYPES",
]
