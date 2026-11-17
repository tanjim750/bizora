"""Steadfast webhook authentication and parsing."""
import hashlib
import hmac
import json
import re

from .client import SteadfastError


def verify_webhook(raw_body: bytes, *, token: str, signature=None, authorization=None):
    if not token:
        raise ValueError('Webhook token is required.')
    signed = isinstance(signature, str) and bool(re.fullmatch(r'[a-fA-F0-9]{64}', signature)) and hmac.compare_digest(
        hmac.new(token.encode(), raw_body, hashlib.sha256).hexdigest(), signature.lower())
    bearer = re.fullmatch(r'Bearer[ \t]+([^\s]+)', authorization or '', flags=re.IGNORECASE)
    return signed or bool(bearer and hmac.compare_digest(token, bearer.group(1)))


def parse_webhook(raw_body: bytes):
    try:
        data = json.loads(raw_body)
    except (UnicodeDecodeError, ValueError) as exc:
        raise SteadfastError('Webhook body contains invalid JSON.') from exc
    if not isinstance(data, dict) or not isinstance(data.get('notification_type'), str) or not data['notification_type'].strip():
        raise SteadfastError('Webhook notification_type must be a nonempty string.')
    return data
