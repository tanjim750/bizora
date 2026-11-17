"""End-to-end test suite for send_tracking_events management command (Phase 4).

Tests:
- Bounded batch execution
- Dry-run mode
- Idempotency across successive command runs
- Prepared mode batch execution on mock connections
- Live batch execution against a local fake HTTP server
- Limit capping
- Nonexistent business error handling
"""
import io
import json
import os
import threading
from datetime import datetime, timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.models import (
    Business,
    ConfigurationRecord,
    Customer,
    IntegrationConnection,
    IntegrationSource,
    Order,
    OrderItem,
    Product,
    WebsiteEvent,
    WebsiteSession,
    WebsiteVisitor,
)
from app.observability.models import ObservationReceipt, OperationAttempt

NOW = datetime(2026, 11, 15, 14, 0, 0, tzinfo=timezone.utc)


class E2EHTTPHandler(BaseHTTPRequestHandler):
    recorded = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        E2EHTTPHandler.recorded.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": body,
            }
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "events_received": 1}')

    def log_message(self, format, *args):
        pass


class TrackingCommandE2ETests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = HTTPServer(("127.0.0.1", 0), E2EHTTPHandler)
        cls.port = cls.server.server_port
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        super().tearDownClass()

    def setUp(self):
        E2EHTTPHandler.recorded = []

        self.business = Business.objects.create(
            name="E2E Fashion Store",
            slug="e2e-fashion",
            currency="BDT",
            created_at=NOW,
            updated_at=NOW,
        )

        self.source_meta = IntegrationSource.objects.create(
            key="meta_ads",
            name="Meta Ads",
            category="MARKETING",
            created_at=NOW,
            updated_at=NOW,
        )
        self.source_ga4 = IntegrationSource.objects.create(
            key="ga4",
            name="Google Analytics 4",
            category="ANALYTICS",
            created_at=NOW,
            updated_at=NOW,
        )

        # 1. Mock Meta connection (prepared mode)
        self.conn_mock_meta = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            name="Meta Pixel Mock",
            is_mock=True,
            external_account_id="pixel_mock_111",
            config={"tracking": {"enabled": True}},
            created_at=NOW,
            updated_at=NOW,
        )

        # Visitor and session
        self.visitor = WebsiteVisitor.objects.create(
            business=self.business,
            visitor_key="visitor_e2e_01",
            first_seen_at=NOW,
        )
        self.session = WebsiteSession.objects.create(
            business=self.business,
            visitor=self.visitor,
            started_at=NOW,
            landing_page_url="https://e2e.bizora.shop/",
        )

        # Create 3 events for the session
        self.event1 = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            event_type="PAGE_VIEW",
            page_url="https://e2e.bizora.shop/",
            occurred_at=NOW,
        )
        self.event2 = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            event_type="ADD_TO_CART",
            page_url="https://e2e.bizora.shop/cart",
            event_value=Decimal("1200.00"),
            currency="BDT",
            occurred_at=NOW,
        )
        self.event3 = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            event_type="PURCHASE",
            page_url="https://e2e.bizora.shop/checkout/done",
            event_value=Decimal("1200.00"),
            currency="BDT",
            occurred_at=NOW,
        )

    def test_command_dry_run(self):
        """Dry-run reports pending events without writing OperationAttempt records."""
        out = io.StringIO()
        call_command(
            "send_tracking_events",
            business=self.business.slug,
            dry_run=True,
            output_json=True,
            stdout=out,
        )
        result = json.loads(out.getvalue())

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["total_pending"], 3)
        self.assertEqual(result["total_processed"], 0)
        self.assertEqual(OperationAttempt.objects.count(), 0)

    def test_command_prepared_batch_execution(self):
        """Command processes unattempted events into prepared OperationAttempts."""
        out = io.StringIO()
        call_command(
            "send_tracking_events",
            business=self.business.slug,
            output_json=True,
            stdout=out,
        )
        result = json.loads(out.getvalue())

        self.assertEqual(result["total_processed"], 3)
        self.assertEqual(result["total_succeeded"], 3)
        self.assertEqual(result["total_failed"], 0)

        # Verify 3 OperationAttempt records were created with mode=PREPARED
        attempts = OperationAttempt.objects.filter(connection=self.conn_mock_meta)
        self.assertEqual(attempts.count(), 3)
        for att in attempts:
            self.assertEqual(att.status, "SUCCEEDED")
            self.assertEqual(att.result["mode"], "PREPARED")

        # Second run should find 0 pending events (idempotent / bounded)
        out2 = io.StringIO()
        call_command(
            "send_tracking_events",
            business=self.business.slug,
            output_json=True,
            stdout=out2,
        )
        result2 = json.loads(out2.getvalue())
        self.assertEqual(result2["total_pending"], 0)
        self.assertEqual(result2["total_processed"], 0)

    def test_command_with_limit(self):
        """Command respects --limit argument."""
        out = io.StringIO()
        call_command(
            "send_tracking_events",
            business=self.business.slug,
            limit=2,
            output_json=True,
            stdout=out,
        )
        result = json.loads(out.getvalue())

        self.assertEqual(result["total_processed"], 2)
        self.assertEqual(OperationAttempt.objects.filter(connection=self.conn_mock_meta).count(), 2)

    def test_command_nonexistent_business_raises(self):
        """Nonexistent business raises CommandError."""
        with self.assertRaises(CommandError) as ctx:
            call_command("send_tracking_events", business="nonexistent-business-xyz")
        self.assertIn("not found", str(ctx.exception))

    def test_command_live_execution_e2e(self):
        """Live connection configured with credentials successfully sends HTTP events via command."""
        # Create a live connection pointing to our test HTTP server
        conn_live = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_ga4,
            name="GA4 Live E2E",
            is_mock=False,
            external_account_id="G-E2ETEST",
            config={
                "tracking": {
                    "enabled": True,
                    "test_mode": True,
                }
            },
            created_at=NOW,
            updated_at=NOW,
        )

        env_name = f"BIZORA_BUSINESS_{self.business.pk}_GA4_API_KEY"
        os.environ[env_name] = "ga4-test-secret-key"
        ConfigurationRecord.objects.create(
            business=self.business,
            kind="INTEGRATION",
            key=str(conn_live.pk),
            data={
                "enabled": True,
                "credentials": {
                    "api_key": f"env:{env_name}",
                },
            },
        )

        try:
            # We patch the live sender's build_live_request or URL to point to our test server
            from unittest.mock import patch

            with patch(
                "app.integrations.tracking.sender.build_live_request"
            ) as mock_req:
                mock_req.return_value = (
                    f"{self.base_url}/debug/mp/collect?measurement_id=G-E2ETEST&api_secret=ga4-test-secret-key",
                    {"Content-Type": "application/json"},
                    b'{"client_id": "vis_1", "events": [{"name": "page_view"}]}',
                )

                out = io.StringIO()
                call_command(
                    "send_tracking_events",
                    business=self.business.slug,
                    connection=conn_live.pk,
                    limit=1,
                    output_json=True,
                    stdout=out,
                )
                res = json.loads(out.getvalue())
                self.assertEqual(res["total_processed"], 1)
                self.assertEqual(res["total_succeeded"], 1)

                # Verify HTTP server received 1 request
                self.assertEqual(len(E2EHTTPHandler.recorded), 1)
                req = E2EHTTPHandler.recorded[0]
                self.assertIn("measurement_id=G-E2ETEST", req["path"])

                # Verify OperationAttempt saved with mode LIVE and redacted URL
                att = OperationAttempt.objects.filter(connection=conn_live).first()
                self.assertIsNotNone(att)
                self.assertEqual(att.status, "SUCCEEDED")
                self.assertEqual(att.result["mode"], "LIVE")
                self.assertIn("api_secret=%5BREDACTED%5D", att.result["endpoint_url"])
                self.assertNotIn("ga4-test-secret-key", str(att.result))
        finally:
            os.environ.pop(env_name, None)
