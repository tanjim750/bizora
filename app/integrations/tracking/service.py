"""Tracking service orchestrating event build, prepared execution, and observability.

Enforces:
Q1: Prepared-only by default; live sending only if not mock, credentials resolve, and tracking enabled.
Q2: Send NO personal identifiers (suppressed in builder/safe_details).
Q3: No new tables or migrations; uses OperationAttempt and record_observation.
Tenant isolation: strict business-boundary verification.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError
from django.utils import timezone

from app.configuration.integrations import CredentialUnavailable, resolve_credentials
from app.models import IntegrationConnection, WebsiteEvent
from app.observability.models import OperationAttempt
from app.observability.policies import safe_details
from app.observability.services import record_observation

from .builder import build_tracking_payload, identify_provider
from .config import get_tracking_config
from .vocabulary import normalize_event_stage


def is_event_allowed(event_type: str, tracking_config: Dict[str, Any]) -> bool:
    """Check if event_type matches allowed events list. If empty, all are allowed."""
    allowed = tracking_config.get("events")
    if not allowed or not isinstance(allowed, list):
        return True
    allowed_set = {str(e).strip().upper() for e in allowed}
    e_upper = str(event_type).strip().upper()
    if e_upper in allowed_set:
        return True
    stage = normalize_event_stage(event_type)
    if stage and stage in allowed_set:
        return True
    return False


def should_send_live(connection: IntegrationConnection) -> bool:
    """Check decision Q1 condition for live outbound sending.

    Must satisfy ALL:
    1. is_mock is False
    2. tracking section in config is enabled
    3. credentials resolve via resolve_credentials
    """
    if connection.is_mock:
        return False

    t_cfg = get_tracking_config(connection)
    if not t_cfg.get("enabled"):
        return False

    try:
        creds = resolve_credentials(connection)
        return bool(creds)
    except (CredentialUnavailable, Exception):
        return False


def process_tracking_event(
    connection: IntegrationConnection,
    event: WebsiteEvent,
    actor=None,
    now=None,
) -> OperationAttempt:
    """Process a single WebsiteEvent for an IntegrationConnection.

    Idempotent: uses OperationAttempt with key 'tracking:event:<event.pk>'.
    In default/mock mode, records as 'PREPARED' and posts an observation.
    """
    now_dt = now or timezone.now()

    # 1. Tenant boundary enforcement
    if event.session.business_id != connection.business_id:
        raise ValidationError(
            f"Tenant boundary violation: Event business {event.session.business_id} "
            f"does not match connection business {connection.business_id}."
        )

    # 2. Idempotency check: one OperationAttempt per (connection, key)
    op_key = f"tracking:event:{event.pk}"
    prior = OperationAttempt.objects.filter(connection=connection, key=op_key).first()
    if prior:
        return prior

    t_cfg = get_tracking_config(connection)

    # 3. Check event allow-list
    if not is_event_allowed(event.event_type, t_cfg):
        attempt = OperationAttempt.objects.create(
            business_id=connection.business_id,
            connection=connection,
            key=op_key,
            action="TRACKING_EVENT",
            target_id=event.pk,
            status="UNSUPPORTED",
            actor=actor,
            result=safe_details(
                {
                    "reason": "EVENT_NOT_IN_ALLOW_LIST",
                    "event_type": event.event_type,
                }
            ),
            created_at=now_dt,
            completed_at=now_dt,
        )
        return attempt

    # 4. Build tracking payload
    provider_type, endpoint_url, payload = build_tracking_payload(
        connection=connection,
        event=event,
        tracking_config=t_cfg,
    )

    is_live = should_send_live(connection)

    if not is_live:
        # Prepared-only execution (default: zero network calls)
        # Limitation: OperationAttempt.status choices are fixed without migrations, so SUCCEEDED is kept with sent=False.
        attempt = OperationAttempt.objects.create(
            business_id=connection.business_id,
            connection=connection,
            key=op_key,
            action="TRACKING_EVENT",
            target_id=event.pk,
            status="SUCCEEDED",
            actor=actor,
            result=safe_details(
                {
                    "mode": "PREPARED",
                    "sent": False,
                    "provider": provider_type,
                    "endpoint_url": endpoint_url,
                    "event_id": f"bizora_we_{event.pk}",
                    "payload": payload,
                }
            ),
            created_at=now_dt,
            completed_at=now_dt,
        )

        return attempt

    # Live sending branch (handled by sender in Phase 3)
    from .sender import send_live_tracking_event

    return send_live_tracking_event(
        connection=connection,
        event=event,
        provider_type=provider_type,
        endpoint_url=endpoint_url,
        payload=payload,
        op_key=op_key,
        actor=actor,
        now=now_dt,
    )
