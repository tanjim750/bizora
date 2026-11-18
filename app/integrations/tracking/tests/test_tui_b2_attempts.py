"""Tests for tracking attempts list endpoint (TUI-B2)."""
from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase

from app.models import (
    Business,
    IntegrationConnection,
    IntegrationSource,
    WebsiteEvent,
    WebsiteSession,
    WebsiteVisitor,
)
from app.observability.models import OperationAttempt
from app.tests.bi_graph_helpers import client_for, make_member

NOW = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)


class TrackingAttemptsApiTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(
            name="Alpha Corp", slug="alpha-corp", currency="BDT", created_at=NOW
        )
        self.other_business = Business.objects.create(
            name="Beta Corp", slug="beta-corp", currency="BDT", created_at=NOW
        )

        self.owner = make_member(self.business, role="OWNER")
        self.viewer = make_member(self.business, role="VIEWER")
        self.outsider = make_member(self.other_business, role="OWNER")

        self.source_meta = IntegrationSource.objects.create(
            key="meta_ads", name="Meta Ads", category="ADVERTISING", created_at=NOW
        )
        self.source_ga4 = IntegrationSource.objects.create(
            key="ga4", name="Google Analytics 4", category="ANALYTICS", created_at=NOW
        )

        self.conn_meta = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            name="Meta Pixel",
            is_mock=True,
            status="CONNECTED",
            created_at=NOW,
        )
        self.conn_ga4 = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_ga4,
            name="GA4 Live",
            is_mock=False,
            status="CONNECTED",
            created_at=NOW,
        )
        self.other_conn = IntegrationConnection.objects.create(
            business=self.other_business,
            integration_source=self.source_meta,
            name="Other Meta",
            is_mock=True,
            status="CONNECTED",
            created_at=NOW,
        )

        self.visitor = WebsiteVisitor.objects.create(
            business=self.business, visitor_key="v-1", first_seen_at=NOW
        )
        self.session = WebsiteSession.objects.create(
            business=self.business, visitor=self.visitor, started_at=NOW
        )
        self.event = WebsiteEvent.objects.create(
            session=self.session, visitor=self.visitor, event_type="PURCHASE", occurred_at=NOW
        )

        self.client_owner = client_for(self.owner)
        self.client_viewer = client_for(self.viewer)
        self.client_outsider = client_for(self.outsider)

    def test_ordering_and_pagination(self):
        # Create 5 attempts with distinct created_at
        attempts = []
        for i in range(5):
            dt = datetime(2026, 11, 17, 12, i, 0, tzinfo=timezone.utc)
            att = OperationAttempt.objects.create(
                business_id=self.business.pk,
                connection=self.conn_meta,
                key=f"tracking:event:{i}",
                action="TRACKING_EVENT",
                target_id=self.event.pk,
                status="SUCCEEDED",
                result={"mode": "PREPARED", "event_id": f"we_{i}"},
                created_at=dt,
                completed_at=dt,
            )
            attempts.append(att)

        url = f"/api/businesses/{self.business.pk}/integrations/tracking/attempts/?limit=2&offset=0"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_count"], 5)
        self.assertEqual(data["limit"], 2)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(len(data["results"]), 2)
        # Newest first
        self.assertEqual(data["results"][0]["id"], attempts[4].pk)
        self.assertEqual(data["results"][1]["id"], attempts[3].pk)

        # Page 2
        url2 = f"/api/businesses/{self.business.pk}/integrations/tracking/attempts/?limit=2&offset=2"
        resp2 = self.client_owner.get(url2)
        data2 = resp2.json()
        self.assertEqual(len(data2["results"]), 2)
        self.assertEqual(data2["results"][0]["id"], attempts[2].pk)
        self.assertEqual(data2["results"][1]["id"], attempts[1].pk)

    def test_filtering_by_connection_status_mode(self):
        att1 = OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_meta,
            key="tracking:1",
            action="TRACKING_EVENT",
            target_id=self.event.pk,
            status="SUCCEEDED",
            result={"mode": "PREPARED"},
            created_at=NOW,
        )
        att2 = OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_ga4,
            key="tracking:2",
            action="TRACKING_EVENT",
            target_id=self.event.pk,
            status="SUCCEEDED",
            result={"mode": "LIVE"},
            created_at=NOW,
        )
        att3 = OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_meta,
            key="tracking:3",
            action="TRACKING_EVENT",
            target_id=self.event.pk,
            status="FAILED",
            result={"mode": "LIVE"},
            created_at=NOW,
        )

        base_url = f"/api/businesses/{self.business.pk}/integrations/tracking/attempts/"

        # Filter connection
        r_conn = self.client_owner.get(f"{base_url}?connection={self.conn_meta.pk}")
        self.assertEqual(r_conn.status_code, 200)
        self.assertEqual([x["id"] for x in r_conn.json()["results"]], [att3.pk, att1.pk])

        # Filter status
        r_stat = self.client_owner.get(f"{base_url}?status=FAILED")
        self.assertEqual(r_stat.status_code, 200)
        self.assertEqual([x["id"] for x in r_stat.json()["results"]], [att3.pk])

        # Filter mode
        r_mode = self.client_owner.get(f"{base_url}?mode=PREPARED")
        self.assertEqual(r_mode.status_code, 200)
        self.assertEqual([x["id"] for x in r_mode.json()["results"]], [att1.pk])

        # Combined filter
        r_comb = self.client_owner.get(
            f"{base_url}?connection={self.conn_meta.pk}&status=SUCCEEDED&mode=PREPARED"
        )
        self.assertEqual(r_comb.status_code, 200)
        self.assertEqual([x["id"] for x in r_comb.json()["results"]], [att1.pk])

    def test_validation_errors_400(self):
        base_url = f"/api/businesses/{self.business.pk}/integrations/tracking/attempts/"

        # Unknown query param
        r1 = self.client_owner.get(f"{base_url}?unknown=1")
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()["code"], "INVALID_DATA")

        # Bad status enum
        r2 = self.client_owner.get(f"{base_url}?status=INVALID_STATUS")
        self.assertEqual(r2.status_code, 400)

        # Bad mode enum
        r3 = self.client_owner.get(f"{base_url}?mode=UNKNOWN_MODE")
        self.assertEqual(r3.status_code, 400)

        # Limit out of range (0 or > 200)
        r4 = self.client_owner.get(f"{base_url}?limit=0")
        self.assertEqual(r4.status_code, 400)
        r5 = self.client_owner.get(f"{base_url}?limit=201")
        self.assertEqual(r5.status_code, 400)
        r6 = self.client_owner.get(f"{base_url}?limit=abc")
        self.assertEqual(r6.status_code, 400)

        # Offset negative or invalid
        r7 = self.client_owner.get(f"{base_url}?offset=-1")
        self.assertEqual(r7.status_code, 400)
        r8 = self.client_owner.get(f"{base_url}?offset=xyz")
        self.assertEqual(r8.status_code, 400)

        # Connection of another business
        r9 = self.client_owner.get(f"{base_url}?connection={self.other_conn.pk}")
        self.assertEqual(r9.status_code, 400)

    def test_other_business_attempts_never_appear(self):
        att_other = OperationAttempt.objects.create(
            business_id=self.other_business.pk,
            connection=self.other_conn,
            key="tracking:other",
            action="TRACKING_EVENT",
            target_id=9999,
            status="SUCCEEDED",
            result={"mode": "PREPARED"},
            created_at=NOW,
        )
        url = f"/api/businesses/{self.business.pk}/integrations/tracking/attempts/"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_count"], 0)
        self.assertEqual(data["results"], [])

    def test_result_shapes_and_payload_leaks_prevented(self):
        # 1. Prepared row
        OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_meta,
            key="tracking:prep",
            action="TRACKING_EVENT",
            target_id=self.event.pk,
            status="SUCCEEDED",
            result={
                "mode": "PREPARED",
                "sent": False,
                "provider": "meta",
                "endpoint_url": "https://graph.facebook.com/v18.0/pixel/events?access_token=SECRET_TOK",
                "event_id": "bizora_we_101",
                "payload": {"sensitive_customer_email": "user@example.test", "data": [1, 2, 3]},
            },
            created_at=NOW,
            completed_at=NOW,
        )

        # 2. Live success row
        OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_ga4,
            key="tracking:live:succ",
            action="TRACKING_EVENT",
            target_id=self.event.pk,
            status="SUCCEEDED",
            result={
                "mode": "LIVE",
                "sent": True,
                "provider": "ga4",
                "endpoint_url": "https://google-analytics.com/mp/collect?api_secret=GA4_SECRET",
                "event_id": "bizora_we_102",
                "outcome": "SUCCESS",
                "http_status": 204,
                "latency_ms": 120,
                "response": "Live raw response from provider body",
                "payload": {"events": [{"name": "page_view"}]},
            },
            created_at=NOW,
            completed_at=NOW,
        )

        # 3. Live rate-limit row
        OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_ga4,
            key="tracking:live:rl",
            action="TRACKING_EVENT",
            target_id=self.event.pk,
            status="FAILED",
            result={
                "mode": "LIVE",
                "provider": "ga4",
                "endpoint_url": "https://google-analytics.com/mp/collect",
                "outcome": "RATE_LIMIT",
                "http_status": 429,
                "latency_ms": 45,
                "retry_after_seconds": 60,
                "error": "RATE_LIMITED",
                "detail": "Too many requests to endpoint",
                "response": "Rate limit response details",
            },
            created_at=NOW,
            completed_at=NOW,
        )

        # 4. Credential failure row
        OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_ga4,
            key="tracking:live:cred",
            action="TRACKING_EVENT",
            target_id=self.event.pk,
            status="FAILED",
            result={
                "mode": "LIVE",
                "provider": "ga4",
                "outcome": "AUTH_ERROR",
                "error": "CREDENTIALS_UNAVAILABLE",
                "detail": "Secret key env:TEST_KEY was not resolved",
            },
            created_at=NOW,
            completed_at=NOW,
        )

        # 5. Unsupported row
        OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_meta,
            key="tracking:unsup",
            action="TRACKING_EVENT",
            target_id=self.event.pk,
            status="UNSUPPORTED",
            result={
                "reason": "EVENT_NOT_IN_ALLOW_LIST",
                "event_type": "PAGE_VIEW",
            },
            created_at=NOW,
            completed_at=NOW,
        )

        url = f"/api/businesses/{self.business.pk}/integrations/tracking/attempts/?limit=10"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        raw_text = resp.content.decode("utf-8")

        # Crucial leak prevention assertions
        self.assertNotIn("SECRET_TOK", raw_text)
        self.assertNotIn("GA4_SECRET", raw_text)
        self.assertNotIn("access_token", raw_text)
        self.assertNotIn("api_secret", raw_text)
        self.assertNotIn("sensitive_customer_email", raw_text)
        self.assertNotIn("user@example.test", raw_text)
        self.assertNotIn("endpoint_url", raw_text)
        self.assertNotIn("Live raw response from provider body", raw_text)
        self.assertNotIn("Rate limit response details", raw_text)
        self.assertNotIn("Too many requests to endpoint", raw_text)
        self.assertNotIn("Secret key env:TEST_KEY", raw_text)
        self.assertNotIn('"payload"', raw_text)
        self.assertNotIn('"response"', raw_text)
        self.assertNotIn('"detail"', raw_text)

        # Inspect fields of results
        results = resp.json()["results"]
        self.assertEqual(len(results), 5)

        # Check unsupported row
        unsup = next(r for r in results if r["status"] == "UNSUPPORTED")
        self.assertIsNone(unsup["mode"])
        self.assertFalse(unsup["sent"])
        self.assertEqual(unsup["reason"], "EVENT_NOT_IN_ALLOW_LIST")

        # Check live success row
        live_succ = next(r for r in results if r["outcome"] == "SUCCESS")
        self.assertEqual(live_succ["mode"], "LIVE")
        self.assertTrue(live_succ["sent"])
        self.assertEqual(live_succ["http_status"], 204)
        self.assertEqual(live_succ["latency_ms"], 120)

        # Check rate-limit row
        rl = next(r for r in results if r["outcome"] == "RATE_LIMIT")
        self.assertFalse(rl["sent"])
        self.assertEqual(rl["retry_after_seconds"], 60)
        self.assertEqual(rl["error"], "RATE_LIMITED")

    def test_event_type_resolution_and_null_case(self):
        # Target exists
        att_with_event = OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_meta,
            key="tracking:with:ev",
            action="TRACKING_EVENT",
            target_id=self.event.pk,
            status="SUCCEEDED",
            result={"mode": "PREPARED"},
            created_at=NOW,
        )
        # Target missing or nonexistent
        att_no_event = OperationAttempt.objects.create(
            business_id=self.business.pk,
            connection=self.conn_meta,
            key="tracking:no:ev",
            action="TRACKING_EVENT",
            target_id=9876543,
            status="SUCCEEDED",
            result={"mode": "PREPARED"},
            created_at=NOW,
        )

        url = f"/api/businesses/{self.business.pk}/integrations/tracking/attempts/"
        resp = self.client_owner.get(url)
        results = resp.json()["results"]
        r_with = next(r for r in results if r["id"] == att_with_event.pk)
        r_no = next(r for r in results if r["id"] == att_no_event.pk)

        self.assertEqual(r_with["event_type"], "PURCHASE")
        self.assertIsNone(r_no["event_type"])

    def test_permissions_viewer_outsider_anonymous(self):
        url = f"/api/businesses/{self.business.pk}/integrations/tracking/attempts/"

        # Viewer can read (200)
        resp_viewer = self.client_viewer.get(url)
        self.assertEqual(resp_viewer.status_code, 200)

        # Outsider gets 403
        resp_out = self.client_outsider.get(url)
        self.assertEqual(resp_out.status_code, 403)

        # Anonymous gets 401 or 403
        anon_client = client_for(None)
        resp_anon = anon_client.get(url)
        self.assertIn(resp_anon.status_code, (401, 403))

    def test_query_ceiling(self):
        # Create 25 rows
        for i in range(25):
            OperationAttempt.objects.create(
                business_id=self.business.pk,
                connection=self.conn_meta,
                key=f"tracking:batch:{i}",
                action="TRACKING_EVENT",
                target_id=self.event.pk,
                status="SUCCEEDED",
                result={"mode": "PREPARED"},
                created_at=NOW,
            )

        url = f"/api/businesses/{self.business.pk}/integrations/tracking/attempts/?limit=25"
        # Bounded query ceiling: exactly 5 queries for 25 rows (ceiling is at most 8)
        with self.assertNumQueries(5):
            resp = self.client_owner.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(resp.json()["results"]), 25)
