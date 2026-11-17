"""Tests for tracking summary endpoint (TUI-B1)."""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from app.configuration.integrations import CredentialUnavailable
from app.integrations.tracking.service import process_tracking_event
from app.models import (
    Business,
    Customer,
    IntegrationConnection,
    IntegrationSource,
    WebsiteEvent,
    WebsiteSession,
    WebsiteVisitor,
)
from app.tests.bi_graph_helpers import client_for, make_member

NOW = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)


class TrackingSummaryApiTests(TestCase):
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
        self.source_tiktok = IntegrationSource.objects.create(
            key="tiktok_ads", name="TikTok Ads", category="ADVERTISING", created_at=NOW
        )
        self.source_ga4 = IntegrationSource.objects.create(
            key="ga4", name="Google Analytics 4", category="ANALYTICS", created_at=NOW
        )
        self.source_shopify = IntegrationSource.objects.create(
            key="shopify", name="Shopify", category="COMMERCE", created_at=NOW
        )

        self.client_owner = client_for(self.owner)
        self.client_viewer = client_for(self.viewer)
        self.client_outsider = client_for(self.outsider)

    def test_empty_business_returns_empty_connections(self):
        url = f"/api/businesses/{self.business.pk}/integrations/tracking/summary/"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["business_id"], self.business.pk)
        self.assertEqual(data["connections"], [])
        self.assertEqual(data["totals"], {"connections": 0, "attempts": 0})

    def test_eligible_providers_listed_and_other_sources_excluded(self):
        conn_meta = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            name="Meta Pixel",
            is_mock=True,
            status="CONNECTED",
            config={"provider_settings": {"tracking": {"enabled": True}}},
            created_at=NOW,
        )
        conn_tiktok = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_tiktok,
            name="TikTok Events",
            is_mock=True,
            status="CONNECTED",
            config={"provider_settings": {"tracking": {"enabled": False}}},
            created_at=NOW,
        )
        conn_ga4 = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_ga4,
            name="GA4 Stream",
            is_mock=True,
            status="CONNECTED",
            config={"provider_settings": {"tracking": {"enabled": True}}},
            created_at=NOW,
        )
        # Excluded source
        IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_shopify,
            name="Shopify Store",
            is_mock=True,
            status="CONNECTED",
            created_at=NOW,
        )
        # Excluded other business connection
        IntegrationConnection.objects.create(
            business=self.other_business,
            integration_source=self.source_meta,
            name="Other Meta",
            is_mock=True,
            status="CONNECTED",
            created_at=NOW,
        )

        url = f"/api/businesses/{self.business.pk}/integrations/tracking/summary/"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        conn_ids = [c["id"] for c in data["connections"]]
        self.assertEqual(conn_ids, [conn_meta.pk, conn_tiktok.pk, conn_ga4.pk])
        providers = [c["provider"] for c in data["connections"]]
        self.assertEqual(providers, ["meta", "tiktok", "ga4"])
        self.assertEqual(data["totals"]["connections"], 3)

    def test_counts_after_processing_tracking_events(self):
        conn = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            name="Meta Pixel",
            is_mock=True,
            status="CONNECTED",
            config={
                "provider_settings": {
                    "tracking": {
                        "enabled": True,
                        "events": ["PURCHASE"],
                    }
                }
            },
            created_at=NOW,
        )
        visitor = WebsiteVisitor.objects.create(
            business=self.business,
            visitor_key="vis-1",
            first_seen_at=NOW,
            last_seen_at=NOW,
        )
        session = WebsiteSession.objects.create(
            business=self.business,
            visitor=visitor,
            started_at=NOW,
        )
        event_allowed = WebsiteEvent.objects.create(
            session=session,
            visitor=visitor,
            event_type="PURCHASE",
            occurred_at=NOW,
        )
        event_unsupported = WebsiteEvent.objects.create(
            session=session,
            visitor=visitor,
            event_type="PAGE_VIEW",
            occurred_at=NOW,
        )

        att_prep = process_tracking_event(conn, event_allowed)
        self.assertEqual(att_prep.status, "SUCCEEDED")
        self.assertEqual(att_prep.result["mode"], "PREPARED")

        att_unsup = process_tracking_event(conn, event_unsupported)
        self.assertEqual(att_unsup.status, "UNSUPPORTED")

        url = f"/api/businesses/{self.business.pk}/integrations/tracking/summary/"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        conn_entry = data["connections"][0]
        self.assertEqual(
            conn_entry["counts"],
            {
                "total": 2,
                "prepared": 1,
                "live_succeeded": 0,
                "failed": 0,
                "unsupported": 1,
            },
        )
        self.assertIsNotNone(conn_entry["last_attempt_at"])
        self.assertEqual(data["totals"]["attempts"], 2)

    def test_mode_and_credentials_available_handling(self):
        conn = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_ga4,
            name="GA4 Stream",
            is_mock=False,
            status="CONNECTED",
            config={"provider_settings": {"tracking": {"enabled": True}}},
            created_at=NOW,
        )

        url = f"/api/businesses/{self.business.pk}/integrations/tracking/summary/"

        # Mock connection gives PREPARED mode
        with patch("app.integrations.tracking.api.should_send_live", return_value=False):
            with patch("app.integrations.tracking.api.resolve_credentials", return_value={"api_key": "val"}):
                resp = self.client_owner.get(url)
                conn_data = resp.json()["connections"][0]
                self.assertEqual(conn_data["mode"], "PREPARED")
                self.assertTrue(conn_data["credentials_available"])

        # When should_send_live is True, mode is LIVE
        with patch("app.integrations.tracking.api.should_send_live", return_value=True):
            with patch("app.integrations.tracking.api.resolve_credentials", side_effect=CredentialUnavailable):
                resp = self.client_owner.get(url)
                conn_data = resp.json()["connections"][0]
                self.assertEqual(conn_data["mode"], "LIVE")
                self.assertFalse(conn_data["credentials_available"])

    def test_secret_leaks_prevented_and_only_allowlist_keys_returned(self):
        IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            name="Meta Pixel",
            is_mock=True,
            status="CONNECTED",
            config={
                "provider_settings": {
                    "tracking": {
                        "enabled": True,
                        "test_mode": True,
                        "events": ["PURCHASE", "PAGE_VIEW"],
                        "test_event_code": "TEST1234",
                        "measurement_id": "M-999",
                        "api_version": "v18.0",
                        "send_pii": False,
                        "api_secret": "SECRET_NEVER_LEAK_ME",
                        "custom_secret_token": "TOKEN_SECRET",
                        "extra_junk": {"a": 1},
                    }
                }
            },
            created_at=NOW,
        )

        url = f"/api/businesses/{self.business.pk}/integrations/tracking/summary/"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        raw_text = resp.content.decode("utf-8")

        self.assertNotIn("SECRET_NEVER_LEAK_ME", raw_text)
        self.assertNotIn("TOKEN_SECRET", raw_text)
        self.assertNotIn("api_secret", raw_text)
        self.assertNotIn("custom_secret_token", raw_text)
        self.assertNotIn("extra_junk", raw_text)

        settings = resp.json()["connections"][0]["settings"]
        self.assertEqual(
            settings,
            {
                "enabled": True,
                "test_mode": True,
                "events": ["PURCHASE", "PAGE_VIEW"],
                "test_event_code": "TEST1234",
                "measurement_id": "M-999",
                "api_version": "v18.0",
                "send_pii": False,
            },
        )

    def test_permissions_viewer_outsider_anonymous(self):
        url = f"/api/businesses/{self.business.pk}/integrations/tracking/summary/"

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

    def test_bounded_queries(self):
        # Create 3 connections with events
        for src in [self.source_meta, self.source_tiktok, self.source_ga4]:
            IntegrationConnection.objects.create(
                business=self.business,
                integration_source=src,
                name=f"{src.name} Conn",
                is_mock=True,
                status="CONNECTED",
                config={"provider_settings": {"tracking": {"enabled": True}}},
                created_at=NOW,
            )

        url = f"/api/businesses/{self.business.pk}/integrations/tracking/summary/"
        # Bounded query ceiling (<= 12 for three connections)
        with self.assertNumQueries(7):
            resp = self.client_owner.get(url)
            self.assertEqual(resp.status_code, 200)
