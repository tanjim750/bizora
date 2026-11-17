"""Management command to process and send tracking events in bounded batches.

Decision Q5: Bounded management command trigger without Redis, Celery, or external workers.
Enforces:
- Tenant scoping by business
- Safe batch limits (--limit, default 50)
- Idempotent execution (skips already attempted events)
- Dry-run support
- Structured JSON or console summary
"""
import json
from typing import Any, Dict, List

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from app.integrations.tracking.builder import identify_provider
from app.integrations.tracking.config import get_tracking_config
from app.integrations.tracking.service import process_tracking_event
from app.models import Business, IntegrationConnection, WebsiteEvent
from app.observability.models import OperationAttempt


class Command(BaseCommand):
    help = "Process unattempted WebsiteEvent records for advertising and analytics tracking connections."

    def add_arguments(self, parser):
        parser.add_argument(
            "--business",
            dest="business",
            required=True,
            help="Business ID or slug.",
        )
        parser.add_argument(
            "--connection",
            dest="connection_id",
            type=int,
            default=None,
            help="Optional single IntegrationConnection ID.",
        )
        parser.add_argument(
            "--provider",
            dest="provider",
            choices=["meta", "tiktok", "ga4"],
            default=None,
            help="Filter by tracking provider type.",
        )
        parser.add_argument(
            "--limit",
            dest="limit",
            type=int,
            default=50,
            help="Maximum number of events to process per connection (default: 50).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Inspect pending events without creating attempts or making network calls.",
        )
        parser.add_argument(
            "--json",
            dest="output_json",
            action="store_true",
            default=False,
            help="Output structured JSON results.",
        )

    def handle(self, *args, **options):
        business_ref = options["business"]
        connection_id = options.get("connection_id")
        provider_filter = options.get("provider")
        limit = max(1, min(int(options.get("limit") or 50), 500))
        dry_run = bool(options.get("dry_run", False))
        output_json = bool(options.get("output_json", False))

        # 1. Resolve business
        business = None
        if str(business_ref).isdigit():
            business = Business.objects.filter(pk=int(business_ref)).first()
        if not business:
            business = Business.objects.filter(slug=str(business_ref)).first()
        if not business:
            raise CommandError(f"Business '{business_ref}' not found.")

        # 2. Find eligible tracking connections
        supported_sources = [
            "meta_ads",
            "meta",
            "facebook",
            "tiktok_ads",
            "tiktok",
            "ga4",
            "google_analytics_4",
            "analytics",
        ]
        conn_query = IntegrationConnection.objects.filter(
            business=business,
            integration_source__key__in=supported_sources,
        ).exclude(status="DISCONNECTED")

        if connection_id:
            conn_query = conn_query.filter(pk=connection_id)

        connections = list(conn_query.select_related("integration_source", "business"))
        if not connections:
            msg = f"No active tracking connections found for business '{business.slug}'."
            if output_json:
                self.stdout.write(json.dumps({"status": "NO_CONNECTIONS", "message": msg}))
            else:
                self.stdout.write(self.style.WARNING(msg))
            return

        results: List[Dict[str, Any]] = []
        now = timezone.now()

        for conn in connections:
            provider = identify_provider(conn)
            if provider_filter and provider != provider_filter:
                continue

            # Query unattempted WebsiteEvents for this connection
            attempted_target_ids = OperationAttempt.objects.filter(
                connection=conn,
                action="TRACKING_EVENT",
            ).values_list("target_id", flat=True)

            pending_events = list(
                WebsiteEvent.objects.filter(session__business_id=business.pk)
                .exclude(pk__in=attempted_target_ids)
                .select_related("session", "visitor", "customer", "product", "order")
                .order_by("occurred_at", "pk")[:limit]
            )

            conn_summary = {
                "connection_id": conn.pk,
                "provider": provider,
                "source_key": conn.integration_source.key,
                "is_mock": conn.is_mock,
                "pending_count": len(pending_events),
                "processed_count": 0,
                "prepared_count": 0,
                "succeeded_count": 0,
                "failed_count": 0,
                "unsupported_count": 0,
            }

            if dry_run:
                conn_summary["status"] = "DRY_RUN"
                results.append(conn_summary)
                continue

            for event in pending_events:
                try:
                    attempt = process_tracking_event(conn, event, now=now)
                    conn_summary["processed_count"] += 1
                    is_prepared = isinstance(attempt.result, dict) and attempt.result.get("mode") == "PREPARED"
                    if is_prepared:
                        conn_summary["prepared_count"] += 1
                    elif attempt.status == "SUCCEEDED":
                        conn_summary["succeeded_count"] += 1
                    elif attempt.status == "UNSUPPORTED":
                        conn_summary["unsupported_count"] += 1
                    else:
                        conn_summary["failed_count"] += 1
                except Exception as exc:
                    conn_summary["processed_count"] += 1
                    conn_summary["failed_count"] += 1
                    if not output_json:
                        self.stderr.write(
                            self.style.ERROR(
                                f"Error processing event {event.pk} for conn {conn.pk}: {exc}"
                            )
                        )

            conn_summary["status"] = "COMPLETED"
            results.append(conn_summary)

        # Output results
        total_processed = sum(r["processed_count"] for r in results)
        total_prepared = sum(r["prepared_count"] for r in results)
        total_succeeded = sum(r["succeeded_count"] for r in results)
        total_failed = sum(r["failed_count"] for r in results)
        total_pending = sum(r["pending_count"] for r in results)

        summary = {
            "business": business.slug,
            "dry_run": dry_run,
            "total_pending": total_pending,
            "total_processed": total_processed,
            "total_prepared": total_prepared,
            "total_succeeded": total_succeeded,
            "total_failed": total_failed,
            "connections": results,
        }

        if output_json:
            self.stdout.write(json.dumps(summary, indent=2))
        else:
            mode_label = "DRY-RUN" if dry_run else "LIVE/PREPARED"
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{mode_label}] Processed {total_processed} events across {len(results)} "
                    f"connection(s) for '{business.slug}' (prepared (not sent): {total_prepared}, sent and accepted: {total_succeeded}, Failed: {total_failed})."
                )
            )
