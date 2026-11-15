"""Pure data normalization and hashing utilities for tracking event mappers.

No Django models, no network, no database calls.
Implements requirements Q2, Q7 and closes risk R8.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any


def hash_sha256(value: str | None) -> str:
    """Return lowercase hex SHA-256 digest of utf-8 string, or empty string if empty."""
    if not value:
        return ""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def normalize_email(value: str | None) -> str:
    """Normalize email: strip leading/trailing whitespace, convert to lowercase."""
    if not value:
        return ""
    return str(value).strip().lower()


def normalize_phone(value: str | None, default_country_code: str | int | None = None) -> str:
    """Normalize phone number per Q7 and R8.

    Q7 policy: If default_country_code is absent or empty, do not normalize
    or send phones (return empty string).
    When present:
    - Strips all non-digit characters.
    - If number has a leading 0, strips it and prefixes default_country_code.
    - If number does not start with default_country_code, prefixes it.
    - If number already starts with default_country_code, retains it.
    """
    if not default_country_code:
        return ""
    if not value:
        return ""

    cc_digits = re.sub(r"\D", "", str(default_country_code))
    if not cc_digits:
        return ""

    raw_digits = re.sub(r"\D", "", str(value))
    if not raw_digits:
        return ""

    # Check if number already starts with country code
    if raw_digits.startswith(cc_digits):
        normalized = raw_digits
    elif raw_digits.startswith("0"):
        # Strip single leading zero (common national format like 017...)
        normalized = f"{cc_digits}{raw_digits.lstrip('0')}"
    else:
        normalized = f"{cc_digits}{raw_digits}"

    # Basic sanity: international E.164 numbers are between 7 and 15 digits
    if len(normalized) < 7 or len(normalized) > 15:
        return ""

    return normalized


def normalize_name(value: str | None) -> str:
    """Normalize first or last name: strip whitespace, convert to lowercase, collapse whitespace."""
    if not value:
        return ""
    clean = re.sub(r"\s+", " ", str(value).strip())
    # Strip common punctuation but preserve letters
    return re.sub(r"[^\w\s]", "", clean).strip().lower()


def normalize_city(value: str | None) -> str:
    """Normalize city: remove digits, punctuation, and whitespace, convert to lowercase."""
    if not value:
        return ""
    return re.sub(r"[0-9.\s\-()]", "", str(value).strip().lower())


def normalize_state(value: str | None) -> str:
    """Normalize state/province: lowercase, letters only."""
    if not value:
        return ""
    return re.sub(r"[^a-z]", "", str(value).strip().lower())


def normalize_country(value: str | None) -> str:
    """Normalize country: 2-letter ISO lowercase country code."""
    if not value:
        return ""
    return re.sub(r"[^a-z]", "", str(value).strip().lower())[:2]


def normalize_zip(value: str | None) -> str:
    """Normalize postal/zip code: remove space, hyphen suffix."""
    if not value:
        return ""
    return str(value).split("-")[0].replace(" ", "").strip().lower()


def normalize_gender(value: str | None) -> str:
    """Normalize gender: 'm' or 'f', else empty string."""
    if not value:
        return ""
    g = str(value).strip().lower()
    return g if g in {"m", "f"} else ""


def normalize_dob(value: str | None) -> str:
    """Normalize date of birth: YYYYMMDD 8 digits."""
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    return digits if len(digits) == 8 else ""


def normalize_external_id(value: Any) -> str:
    """Normalize external ID: string representation of canonical ID."""
    if value is None:
        return ""
    return str(value).strip()


def clean_nulls(value: Any) -> Any:
    """Recursively clean None values from dictionaries and lists."""
    if isinstance(value, dict):
        return {k: clean_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [clean_nulls(v) for v in value if v is not None]
    return value
