"""Tracking integration HTTP API views (TUI-B1 to TUI-B3)."""
from typing import Any, Dict, List

from django.db.models import Count, Max, Q
from rest_framework.response import Response

from app.business_scope import BusinessScopedAPIView
from app.configuration.integrations import CredentialUnavailable, resolve_credentials
from app.models import IntegrationConnection
from app.observability.models import OperationAttempt

from .builder import identify_provider
from .config import get_tracking_config
from .service import should_send_live

SUPPORTED_TRACKING_PROVIDERS = {"meta", "tiktok", "ga4"}


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
