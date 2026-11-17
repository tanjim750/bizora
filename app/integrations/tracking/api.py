"""Tracking integration HTTP API views (TUI-B1 to TUI-B3)."""
import re
from typing import Any, Dict, List, Optional

from django.db.models import Count, Max, Q
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from app.business_scope import BusinessScopedAPIView
from app.configuration.integrations import CredentialUnavailable, resolve_credentials
from app.models import IntegrationConnection, WebsiteEvent
from app.observability.models import OperationAttempt

from .builder import identify_provider
from .config import get_tracking_config
from .service import should_send_live

SUPPORTED_TRACKING_PROVIDERS = {"meta", "tiktok", "ga4"}
CODE_PATTERN = re.compile(r"^[A-Z][A-Z_]{2,39}$")
ALLOWED_OUTCOMES = {
    "SUCCESS",
    "RATE_LIMIT",
    "PROVIDER_ERROR",
    "TIMEOUT",
    "CONNECTIVITY_ERROR",
    "AUTH_ERROR",
}
ALLOWED_ATTEMPT_QUERY_PARAMS = {"connection", "status", "mode", "limit", "offset"}
ALLOWED_ATTEMPT_STATUSES = {"RUNNING", "SUCCEEDED", "FAILED", "UNSUPPORTED"}
ALLOWED_ATTEMPT_MODES = {"PREPARED", "LIVE"}


def _clean_int(val: Any) -> Optional[int]:
    if isinstance(val, int) and not isinstance(val, bool):
        return val
    return None


class TrackingSummaryView(BusinessScopedAPIView):
    """GET summary of tracking connections, settings, and operation attempt counts."""

    def get(self, request, business_id: int):
        business = self.get_authorized_business()
        all_connections = (
            IntegrationConnection.objects.filter(business_id=business.pk)
            .select_related("integration_source")
            .order_by("id")
        )

        eligible_connections: List[IntegrationConnection] = []
        conn_providers: Dict[int, str] = {}
        for conn in all_connections:
            provider = identify_provider(conn)
            if provider in SUPPORTED_TRACKING_PROVIDERS:
                eligible_connections.append(conn)
                conn_providers[conn.pk] = provider

        attempt_stats: Dict[int, Dict[str, Any]] = {}
        if eligible_connections:
            eligible_ids = [c.pk for c in eligible_connections]
            stats_qs = (
                OperationAttempt.objects.filter(
                    business_id=business.pk,
                    connection_id__in=eligible_ids,
                    action="TRACKING_EVENT",
                )
                .values("connection_id")
                .annotate(
                    total=Count("id"),
                    prepared=Count("id", filter=Q(status="SUCCEEDED", result__mode="PREPARED")),
                    live_succeeded=Count("id", filter=Q(status="SUCCEEDED", result__mode="LIVE")),
                    failed=Count("id", filter=Q(status="FAILED")),
                    unsupported=Count("id", filter=Q(status="UNSUPPORTED")),
                    last_attempt_at=Max("created_at"),
                )
            )
            for row in stats_qs:
                attempt_stats[row["connection_id"]] = row

        connections_out = []
        for conn in eligible_connections:
            provider = conn_providers[conn.pk]
            is_live = should_send_live(conn)
            mode = "LIVE" if is_live else "PREPARED"

            try:
                creds = resolve_credentials(conn)
                credentials_available = bool(creds)
            except (CredentialUnavailable, Exception):
                credentials_available = False

            raw_cfg = get_tracking_config(conn)
            raw_events = raw_cfg.get("events")
            events_list = [str(e) for e in raw_events] if isinstance(raw_events, list) else []

            settings = {
                "enabled": bool(raw_cfg.get("enabled", False)),
                "test_mode": bool(raw_cfg.get("test_mode", False)),
                "events": events_list,
                "test_event_code": str(raw_cfg["test_event_code"]) if raw_cfg.get("test_event_code") is not None else None,
                "measurement_id": str(raw_cfg["measurement_id"]) if raw_cfg.get("measurement_id") is not None else None,
                "api_version": str(raw_cfg["api_version"]) if raw_cfg.get("api_version") is not None else None,
                "send_pii": bool(raw_cfg.get("send_pii", False)),
            }

            st = attempt_stats.get(conn.pk, {})
            counts = {
                "total": st.get("total", 0),
                "prepared": st.get("prepared", 0),
                "live_succeeded": st.get("live_succeeded", 0),
                "failed": st.get("failed", 0),
                "unsupported": st.get("unsupported", 0),
            }
            last_dt = st.get("last_attempt_at")
            last_attempt_at = last_dt.isoformat().replace("+00:00", "Z") if last_dt else None

            connections_out.append(
                {
                    "id": conn.pk,
                    "name": conn.name,
                    "provider": provider,
                    "status": conn.status,
                    "is_mock": conn.is_mock,
                    "mode": mode,
                    "credentials_available": credentials_available,
                    "settings": settings,
                    "counts": counts,
                    "last_attempt_at": last_attempt_at,
                }
            )

        total_attempts = sum(c["counts"]["total"] for c in connections_out)
        return Response(
            {
                "business_id": business.pk,
                "connections": connections_out,
                "totals": {
                    "connections": len(connections_out),
                    "attempts": total_attempts,
                },
            }
        )


class TrackingAttemptListView(BusinessScopedAPIView):
    """GET paginated list of tracking operation attempts with strict leak-free serialization."""

    def get(self, request, business_id: int):
        business = self.get_authorized_business()

        # Validate query parameters
        extra_keys = set(request.query_params.keys()) - ALLOWED_ATTEMPT_QUERY_PARAMS
        if extra_keys:
            raise ValidationError({k: "Unknown query parameter." for k in extra_keys})

        conn_id = None
        if "connection" in request.query_params:
            conn_raw = request.query_params.get("connection")
            try:
                conn_id = int(conn_raw)
            except (ValueError, TypeError):
                raise ValidationError({"connection": "Connection ID must be an integer."})
            if not IntegrationConnection.objects.filter(pk=conn_id, business_id=business.pk).exists():
                raise ValidationError({"connection": "Connection does not belong to this business."})

        status_val = None
        if "status" in request.query_params:
            status_val = request.query_params.get("status")
            if status_val not in ALLOWED_ATTEMPT_STATUSES:
                raise ValidationError({"status": f"Invalid status: {status_val}"})

        mode_val = None
        if "mode" in request.query_params:
            mode_val = request.query_params.get("mode")
            if mode_val not in ALLOWED_ATTEMPT_MODES:
                raise ValidationError({"mode": f"Invalid mode: {mode_val}"})

        limit = 25
        if "limit" in request.query_params:
            limit_raw = request.query_params.get("limit")
            try:
                limit = int(limit_raw)
            except (ValueError, TypeError):
                raise ValidationError({"limit": "Limit must be an integer."})
            if limit < 1 or limit > 200:
                raise ValidationError({"limit": "Limit must be between 1 and 200."})

        offset = 0
        if "offset" in request.query_params:
            offset_raw = request.query_params.get("offset")
            try:
                offset = int(offset_raw)
            except (ValueError, TypeError):
                raise ValidationError({"offset": "Offset must be an integer."})
            if offset < 0:
                raise ValidationError({"offset": "Offset must be non-negative."})

        qs = OperationAttempt.objects.filter(
            business_id=business.pk,
            action="TRACKING_EVENT",
        )
        if conn_id is not None:
            qs = qs.filter(connection_id=conn_id)
        if status_val is not None:
            qs = qs.filter(status=status_val)
        if mode_val is not None:
            qs = qs.filter(result__mode=mode_val)

        qs = qs.order_by("-created_at", "-id")

        total_count = qs.count()
        paginated_attempts = list(
            qs.select_related("connection", "connection__integration_source")[offset : offset + limit]
        )

        target_ids = [att.target_id for att in paginated_attempts if att.target_id is not None]
        event_type_map = {}
        if target_ids:
            events = (
                WebsiteEvent.objects.filter(
                    pk__in=target_ids,
                    session__business_id=business.pk,
                ).values("pk", "event_type")
            )
            for ev in events:
                event_type_map[ev["pk"]] = ev["event_type"]

        results = []
        for att in paginated_attempts:
            res = att.result if isinstance(att.result, dict) else {}
            mode = res.get("mode") if res.get("mode") in ("PREPARED", "LIVE") else None
            sent = True if (mode == "LIVE" and att.status == "SUCCEEDED") else False

            event_id = res.get("event_id")
            if not isinstance(event_id, str):
                event_id = f"bizora_we_{att.target_id}" if att.target_id is not None else None

            error_val = res.get("error")
            error = (
                error_val
                if (isinstance(error_val, str) and CODE_PATTERN.match(error_val))
                else None
            )

            reason_val = res.get("reason")
            reason = (
                reason_val
                if (isinstance(reason_val, str) and CODE_PATTERN.match(reason_val))
                else None
            )

            created_at = (
                att.created_at.isoformat().replace("+00:00", "Z")
                if att.created_at
                else None
            )
            completed_at = (
                att.completed_at.isoformat().replace("+00:00", "Z")
                if att.completed_at
                else None
            )
            next_retry_at = (
                att.next_retry_at.isoformat().replace("+00:00", "Z")
                if att.next_retry_at
                else None
            )

            results.append(
                {
                    "id": att.pk,
                    "connection_id": att.connection_id,
                    "connection_name": att.connection.name if att.connection else None,
                    "provider": identify_provider(att.connection) if att.connection else None,
                    "website_event_id": att.target_id,
                    "event_type": event_type_map.get(att.target_id),
                    "event_id": event_id,
                    "status": att.status,
                    "mode": mode,
                    "sent": sent,
                    "outcome": (
                        res.get("outcome")
                        if res.get("outcome") in ALLOWED_OUTCOMES
                        else None
                    ),
                    "http_status": _clean_int(res.get("http_status")),
                    "latency_ms": _clean_int(res.get("latency_ms")),
                    "retry_after_seconds": _clean_int(res.get("retry_after_seconds")),
                    "error": error,
                    "reason": reason,
                    "created_at": created_at,
                    "completed_at": completed_at,
                    "next_retry_at": next_retry_at,
                }
            )

        return Response(
            {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "results": results,
            }
        )

