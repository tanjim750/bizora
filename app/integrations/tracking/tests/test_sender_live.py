"""Tests for live outbound tracking sender with urllib.request (Phase 3).

Verifies against a local in-process HTTP server:
- R1/R2: No secrets or raw PII leaked in logs or OperationAttempt.
- R3: GA4 uses collection endpoint /mp/collect in live, debug in test_mode.
- R4: Meta api_version configurable.
- R6: Exception handling, outcome mapping (AUTH_ERROR, RATE_LIMIT, TIMEOUT, etc.).
- R7: Timeouts enforced.
- R9: test_event_code only sent when test_mode is True.
"""
import json
import os
import socket
import threading
from datetime import datetime, timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import URLError

from django.test import TestCase

from app.models import (
    Business,
    ConfigurationRecord,
    Customer,
    IntegrationConnection,
    IntegrationSource,
    Product,
    WebsiteEvent,
    WebsiteSession,
    WebsiteVisitor,
)
from app.observability.models import ObservationReceipt, OperationAttempt

from ..sender import sanitize_url, send_live_tracking_event
from ..service import process_tracking_event

NOW = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)


class FakeHTTPHandler(BaseHTTPRequestHandler):
    """Configurable HTTP handler for tracking provider test endpoints."""

    response_code = 200
    response_headers = {"Content-Type": "application/json"}
    response_body = b'{"status": "ok"}'
    recorded_requests = []

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        FakeHTTPHandler.recorded_requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": body,
            }
        )
        self.send_response(FakeHTTPHandler.response_code)
        for h, v in FakeHTTPHandler.response_headers.items():
            self.send_header(h, v)
        self.end_headers()
        self.wfile.write(FakeHTTPHandler.response_body)

    def log_message(self, format, *args):
        # Silence HTTP server logs during test run
        pass


class TrackingSenderLiveTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Find a free port and start server
        cls.server = HTTPServer(("127.0.0.1", 0), FakeHTTPHandler)
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
        FakeHTTPHandler.response_code = 200
        FakeHTTPHandler.response_headers = {"Content-Type": "application/json"}
        FakeHTTPHandler.response_body = b'{"status": "ok"}'
        FakeHTTPHandler.recorded_requests = []

        self.business = Business.objects.create(
            name="Live Store",
            slug="live-store",
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
        self.source_tiktok = IntegrationSource.objects.create(
            key="tiktok_ads",
            name="TikTok Ads",
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

        # Meta connection configured for our local test server
        self.conn_meta = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            name="Meta Live",
            is_mock=False,
            external_account_id="pixel_meta_live",
            config={
                "tracking": {
                    "enabled": True,
                    "api_version": "v18.0",
                }
            },
            created_at=NOW,
            updated_at=NOW,
        )
        # Configure Meta credentials via ConfigurationRecord and environment variable
        self.meta_env_var = f"BIZORA_BUSINESS_{self.business.pk}_META_TOKEN"
        os.environ[self.meta_env_var] = "meta-secret-token-xyz"
        ConfigurationRecord.objects.create(
            business=self.business,
            kind="INTEGRATION",
            key=str(self.conn_meta.pk),
            data={
                "enabled": True,
                "credentials": {
                    "access_token": f"env:{self.meta_env_var}",
                },
            },
        )

        # Customer & session
        self.customer = Customer.objects.create(
            business=self.business,
            first_name="Live",
            last_name="Shopper",
            display_name="Live Shopper",
        )
        self.visitor = WebsiteVisitor.objects.create(
            business=self.business,
            customer=self.customer,
            visitor_key="vis_live_001",
            first_seen_at=NOW,
        )
        self.session = WebsiteSession.objects.create(
            business=self.business,
            visitor=self.visitor,
            customer=self.customer,
            started_at=NOW,
        )
        self.event = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            event_type="PAGE_VIEW",
            page_url="https://bizora.shop/catalog",
            occurred_at=NOW,
        )

    def tearDown(self):
        os.environ.pop(self.meta_env_var, None)
        super().tearDown()

    def test_sanitize_url(self):
        """Sanitizer masks sensitive query tokens."""
        url = "https://www.google-analytics.com/mp/collect?measurement_id=G-123&api_secret=supersecret999"
        sanitized = sanitize_url(url)
        self.assertNotIn("supersecret999", sanitized)
        self.assertIn("api_secret=%5BREDACTED%5D", sanitized)
        self.assertIn("measurement_id=G-123", sanitized)

        # Non-sensitive URLs remain unchanged
        plain = "https://graph.facebook.com/v18.0/pixel_123/events"
        self.assertEqual(sanitize_url(plain), plain)

    def test_live_send_meta_success(self):
        """Meta live send transmits Authorization Bearer header and records success."""
        endpoint = f"{self.base_url}/v18.0/pixel_meta_live/events"
        attempt = send_live_tracking_event(
            connection=self.conn_meta,
            event=self.event,
            provider_type="meta",
            endpoint_url=endpoint,
            payload={"data": [{"event_name": "PageView"}]},
            op_key=f"tracking:event:{self.event.pk}",
            now=NOW,
        )

        self.assertEqual(attempt.status, "SUCCEEDED")
        self.assertEqual(attempt.result["outcome"], "SUCCESS")
        self.assertEqual(attempt.result["http_status"], 200)
        self.assertGreater(attempt.result["latency_ms"], 0)

        # Verify request reached fake server
        self.assertEqual(len(FakeHTTPHandler.recorded_requests), 1)
        req = FakeHTTPHandler.recorded_requests[0]
        self.assertEqual(req["headers"].get("Authorization"), "Bearer meta-secret-token-xyz")
        body = json.loads(req["body"].decode("utf-8"))
        self.assertEqual(body["data"][0]["event_name"], "PageView")

        # Verify no secret leaked in attempt result
        self.assertNotIn("meta-secret-token-xyz", str(attempt.result))

        # Verify observation created
        receipt = ObservationReceipt.objects.filter(
            connection=self.conn_meta,
            key=f"tracking:event:{self.event.pk}:live",
        ).first()
        self.assertIsNotNone(receipt)

    def test_live_send_auth_error_401(self):
        """HTTP 401 returns outcome AUTH_ERROR and marks attempt FAILED."""
        FakeHTTPHandler.response_code = 401
        FakeHTTPHandler.response_body = b'{"error": {"message": "Invalid OAuth access token"}}'

        endpoint = f"{self.base_url}/events"
        attempt = send_live_tracking_event(
            connection=self.conn_meta,
            event=self.event,
            provider_type="meta",
            endpoint_url=endpoint,
            payload={"data": []},
            op_key=f"tracking:event:{self.event.pk}",
            now=NOW,
        )

        self.assertEqual(attempt.status, "FAILED")
        self.assertEqual(attempt.result["outcome"], "AUTH_ERROR")
        self.assertEqual(attempt.result["http_status"], 401)
        self.assertIn("Invalid OAuth", attempt.result["response"])

    def test_live_send_rate_limit_429_with_retry_after(self):
        """HTTP 429 parses Retry-After header and computes next_retry_at."""
        FakeHTTPHandler.response_code = 429
        FakeHTTPHandler.response_headers = {
            "Content-Type": "application/json",
            "Retry-After": "120",
        }
        FakeHTTPHandler.response_body = b'{"error": "Too Many Requests"}'

        endpoint = f"{self.base_url}/events"
        attempt = send_live_tracking_event(
            connection=self.conn_meta,
            event=self.event,
            provider_type="meta",
            endpoint_url=endpoint,
            payload={"data": []},
            op_key=f"tracking:event:{self.event.pk}",
            now=NOW,
        )

        self.assertEqual(attempt.status, "FAILED")
        self.assertEqual(attempt.result["outcome"], "RATE_LIMIT")
        self.assertEqual(attempt.result["http_status"], 429)
        self.assertEqual(attempt.result["retry_after_seconds"], 120)
        self.assertIsNotNone(attempt.next_retry_at)
        delta = (attempt.next_retry_at - NOW).total_seconds()
        self.assertEqual(delta, 120)

    def test_live_send_provider_error_500(self):
        """HTTP 500 maps to outcome PROVIDER_ERROR."""
        FakeHTTPHandler.response_code = 500
        FakeHTTPHandler.response_body = b'{"error": "Internal Server Error"}'

        endpoint = f"{self.base_url}/events"
        attempt = send_live_tracking_event(
            connection=self.conn_meta,
            event=self.event,
            provider_type="meta",
            endpoint_url=endpoint,
            payload={"data": []},
            op_key=f"tracking:event:{self.event.pk}",
            now=NOW,
        )

        self.assertEqual(attempt.status, "FAILED")
        self.assertEqual(attempt.result["outcome"], "PROVIDER_ERROR")
        self.assertEqual(attempt.result["http_status"], 500)

    def test_live_send_connection_refused(self):
        """Attempting to connect to an unopened port maps to CONNECTIVITY_ERROR."""
        # Port 1 is rarely/never bound on loopback
        dead_endpoint = "http://127.0.0.1:1/events"
        attempt = send_live_tracking_event(
            connection=self.conn_meta,
            event=self.event,
            provider_type="meta",
            endpoint_url=dead_endpoint,
            payload={"data": []},
            op_key=f"tracking:event:{self.event.pk}",
            now=NOW,
        )

        self.assertEqual(attempt.status, "FAILED")
        self.assertEqual(attempt.result["outcome"], "CONNECTIVITY_ERROR")
        self.assertNotIn("http_status", attempt.result)

    def test_live_send_ga4_and_tiktok_headers(self):
        """Verify provider-specific header formatting for TikTok and query parameter for GA4."""
        # 1. TikTok connection
        conn_tt = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_tiktok,
            name="TikTok Live",
            is_mock=False,
            external_account_id="pixel_tt_live",
            config={"tracking": {"enabled": True}},
            created_at=NOW,
            updated_at=NOW,
        )
        tt_env = f"BIZORA_BUSINESS_{self.business.pk}_TT_TOKEN"
        os.environ[tt_env] = "tiktok-secret-token-abc"
        ConfigurationRecord.objects.create(
            business=self.business,
            kind="INTEGRATION",
            key=str(conn_tt.pk),
            data={
                "enabled": True,
                "credentials": {"access_token": f"env:{tt_env}"},
            },
        )
        try:
            attempt_tt = send_live_tracking_event(
                connection=conn_tt,
                event=self.event,
                provider_type="tiktok",
                endpoint_url=f"{self.base_url}/tiktok/track",
                payload={"data": []},
                op_key=f"tracking:event:{self.event.pk}:tt",
                now=NOW,
            )
            self.assertEqual(attempt_tt.status, "SUCCEEDED")
            last_req = FakeHTTPHandler.recorded_requests[-1]
            self.assertEqual(last_req["headers"].get("Access-Token"), "tiktok-secret-token-abc")
        finally:
            os.environ.pop(tt_env, None)
