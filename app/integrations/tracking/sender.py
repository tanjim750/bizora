"""Outbound HTTP sender for live tracking events (Phase 3).

Uses standard library urllib.request only (no requests, no SDKs, no external workers).
Handles:
- Per-provider isolation (Meta, TikTok, GA4)
- Server-side credentials resolution via resolve_credentials
- Timeout enforcement
- Outcome and status mapping to ProviderRequest
- Retry-After header parsing for 429 Rate Limits
- URL and credentials sanitization (no secrets leaked in logs or OperationAttempt)
- Observability via record_observation(kind='provider_request')
"""
from __future__ import annotations

import json
import re
import socket
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
import urllib.request

from django.utils import timezone

from app.configuration.integrations import CredentialUnavailable, resolve_credentials
from app.models import IntegrationConnection, WebsiteEvent
from app.observability.models import OperationAttempt
from app.observability.policies import safe_details
from app.observability.services import record_observation

from .config import get_tracking_config


def sanitize_url(url: str) -> str:
    """Sanitize URL by masking sensitive query parameters (api_secret, access_token, etc.)."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        params = parse_qs(parsed.query, keep_blank_values=True)
        sanitized_params = {}
        for k, vals in params.items():
            if re.search(r"token|secret|key|auth", k, re.I):
                sanitized_params[k] = ["[REDACTED]"]
            else:
                sanitized_params[k] = vals
        flat = []
        for k, vals in sanitized_params.items():
            for v in vals:
                flat.append((k, v))
        new_query = urlencode(flat)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )
    except Exception:
        return re.sub(
            r"([?&](?:api_secret|access_token|token|key|api_key)=)[^&]+",
            r"\1[REDACTED]",
            url,
            flags=re.I,
        )


def build_live_request(
    connection: IntegrationConnection,
    provider_type: str,
    endpoint_url: str,
    payload: Dict[str, Any],
    tracking_config: Dict[str, Any],
    credentials: Dict[str, str],
) -> Tuple[str, Dict[str, str], bytes]:
    """Construct (request_url, headers, body_bytes) for provider."""
    data_bytes = json.dumps(payload).encode("utf-8")
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if provider_type == "meta":
        token = (
            credentials.get("access_token")
            or credentials.get("token")
            or credentials.get("api_key")
            or ""
        )
        headers["Authorization"] = f"Bearer {token}"
        return endpoint_url, headers, data_bytes

    elif provider_type == "tiktok":
        token = (
            credentials.get("access_token")
            or credentials.get("token")
            or credentials.get("api_key")
            or ""
        )
        headers["Access-Token"] = token
        return endpoint_url, headers, data_bytes

    elif provider_type == "ga4":
        # GA4 api_secret is stored as api_key in connection credentials (Q4)
        api_secret = (
            credentials.get("api_key")
            or credentials.get("api_secret")
            or tracking_config.get("api_secret", "")
        )
        measurement_id = (
            connection.external_account_id
            or tracking_config.get("measurement_id", "")
        )
        test_mode = bool(tracking_config.get("test_mode", False))
        base_endpoint = (
            "https://www.google-analytics.com/debug/mp/collect"
            if test_mode
            else "https://www.google-analytics.com/mp/collect"
        )
        query = urlencode(
            {
                "measurement_id": measurement_id,
                "api_secret": api_secret,
            }
        )
        request_url = f"{base_endpoint}?{query}"
        return request_url, headers, data_bytes

    else:
        token = credentials.get("access_token") or credentials.get("api_key")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return endpoint_url, headers, data_bytes


def send_live_tracking_event(
    connection: IntegrationConnection,
    event: WebsiteEvent,
    provider_type: str,
    endpoint_url: str,
    payload: Dict[str, Any],
    op_key: str,
    actor=None,
    now=None,
) -> OperationAttempt:
    """Send tracking event outbound to the live provider endpoint via urllib.request."""
    now_dt = now or timezone.now()
    t_cfg = get_tracking_config(connection)
    timeout = float(t_cfg.get("timeout_seconds", 5.0))

    # Resolve credentials
    try:
        credentials = resolve_credentials(connection)
    except (CredentialUnavailable, Exception) as exc:
        attempt = OperationAttempt.objects.create(
            business_id=connection.business_id,
            connection=connection,
            key=op_key,
            action="TRACKING_EVENT",
            target_id=event.pk,
            status="FAILED",
            actor=actor,
            result=safe_details(
                {
                    "mode": "LIVE",
                    "provider": provider_type,
                    "error": "CREDENTIALS_UNAVAILABLE",
                    "detail": str(exc),
                }
            ),
            created_at=now_dt,
            completed_at=now_dt,
        )
        record_observation(
            business_id=connection.business_id,
            connection_id=connection.pk,
            key=f"{op_key}:live",
            kind="provider_request",
            data={
                "outcome": "AUTH_ERROR",
                "capability": f"tracking.{provider_type}",
                "target": f"CONNECTION:{connection.pk}",
                "latency_ms": 0,
            },
            observed_at=now_dt,
            received_at=now_dt,
        )
        return attempt

    # Construct request
    request_url, headers, data_bytes = build_live_request(
        connection=connection,
        provider_type=provider_type,
        endpoint_url=endpoint_url,
        payload=payload,
        tracking_config=t_cfg,
        credentials=credentials,
    )

    req = urllib.request.Request(
        url=request_url,
        data=data_bytes,
        headers=headers,
        method="POST",
    )

    start_time = time.monotonic()
    status_code: Optional[int] = None
    outcome = "SUCCESS"
    resp_body = ""
    retry_after_seconds: Optional[int] = None
    next_retry_at: Optional[datetime] = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency_ms = max(1, int((time.monotonic() - start_time) * 1000))
            status_code = getattr(response, "status", 200)
            raw = response.read()
            resp_body = raw.decode("utf-8", errors="replace")[:1000]
            outcome = "SUCCESS"
    except HTTPError as exc:
        latency_ms = max(1, int((time.monotonic() - start_time) * 1000))
        status_code = exc.code
        raw = exc.read()
        resp_body = raw.decode("utf-8", errors="replace")[:1000]
        if status_code in (401, 403):
            outcome = "AUTH_ERROR"
        elif status_code == 429:
            outcome = "RATE_LIMIT"
            retry_header = exc.headers.get("Retry-After") if exc.headers else None
            if retry_header and str(retry_header).strip().isdigit():
                retry_after_seconds = int(str(retry_header).strip())
            else:
                retry_after_seconds = int(t_cfg.get("rate_limit_backoff_seconds", 60))
            next_retry_at = now_dt + timedelta(seconds=retry_after_seconds)
        elif status_code >= 500:
            outcome = "PROVIDER_ERROR"
        else:
            outcome = "PROVIDER_ERROR"
    except (TimeoutError, socket.timeout) as exc:
        latency_ms = max(1, int((time.monotonic() - start_time) * 1000))
        status_code = None
        outcome = "TIMEOUT"
        resp_body = f"Request timed out after {timeout}s: {exc}"
    except (URLError, Exception) as exc:
        latency_ms = max(1, int((time.monotonic() - start_time) * 1000))
        status_code = None
        err_msg = str(exc)
        if "timed out" in err_msg.lower():
            outcome = "TIMEOUT"
        else:
            outcome = "CONNECTIVITY_ERROR"
        resp_body = err_msg[:500]

    # Save OperationAttempt
    is_succeeded = outcome == "SUCCESS"
    sanitized_endpoint = sanitize_url(request_url)
    result_data: Dict[str, Any] = {
        "mode": "LIVE",
        "provider": provider_type,
        "endpoint_url": sanitized_endpoint,
        "event_id": f"bizora_we_{event.pk}",
        "outcome": outcome,
        "latency_ms": latency_ms,
        "response": resp_body,
    }
    if status_code is not None:
        result_data["http_status"] = status_code
    if retry_after_seconds is not None:
        result_data["retry_after_seconds"] = retry_after_seconds

    attempt = OperationAttempt.objects.create(
        business_id=connection.business_id,
        connection=connection,
        key=op_key,
        action="TRACKING_EVENT",
        target_id=event.pk,
        status="SUCCEEDED" if is_succeeded else "FAILED",
        actor=actor,
        result=safe_details(result_data),
        created_at=now_dt,
        completed_at=now_dt,
        next_retry_at=next_retry_at,
    )

    # Post observation receipt
    obs_data: Dict[str, Any] = {
        "outcome": outcome,
        "capability": f"tracking.{provider_type}",
        "target": f"CONNECTION:{connection.pk}",
        "latency_ms": latency_ms,
    }
    if status_code is not None and status_code >= 100:
        obs_data["http_status"] = status_code
    if retry_after_seconds is not None:
        obs_data["retry_after_seconds"] = retry_after_seconds

    record_observation(
        business_id=connection.business_id,
        connection_id=connection.pk,
        key=f"{op_key}:live",
        kind="provider_request",
        data=obs_data,
        observed_at=now_dt,
        received_at=now_dt,
    )

    return attempt
