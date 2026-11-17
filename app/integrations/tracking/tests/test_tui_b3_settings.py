"""Tests for tracking connection settings PATCH endpoint (TUI-B3)."""
from datetime import datetime, timezone
import json

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
from app.integrations.tracking.config import get_tracking_config
from app.integrations.tracking.service import process_tracking_event
from app.tests.bi_graph_helpers import client_for, make_member

NOW = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)


class TrackingSettingsPatchApiTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(
            name="Alpha Corp", slug="alpha-corp", currency="BDT", created_at=NOW
        )
        self.other_business = Business.objects.create(
            name="Beta Corp", slug="beta-corp", currency="BDT", created_at=NOW
        )

        self.owner = make_member(self.business, role="OWNER")
        self.manager = make_member(self.business, role="MANAGER")
        self.operator = make_member(self.business, role="OPERATOR")
        self.viewer = make_member(self.business, role="VIEWER")
        self.outsider = make_member(self.other_business, role="OWNER")

        self.source_meta = IntegrationSource.objects.create(
            key="meta_ads", name="Meta Ads", category="ADVERTISING", created_at=NOW
        )
        self.source_ga4 = IntegrationSource.objects.create(
            key="ga4", name="Google Analytics 4", category="ANALYTICS", created_at=NOW
        )
        self.source_tiktok = IntegrationSource.objects.create(
            key="tiktok", name="TikTok Events", category="ADVERTISING", created_at=NOW
        )
        self.source_slack = IntegrationSource.objects.create(
            key="slack", name="Slack", category="COMMUNICATION", created_at=NOW
        )

        self.conn_meta = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            name="Meta Pixel",
            is_mock=True,
            status="CONNECTED",
            config={
                "provider_settings": {
                    "keep": 1,
                    "tracking": {
                        "api_version": "v18.0",
                        "enabled": False,
                    },
                },
                "other": 2,
            },
            created_at=NOW,
        )
        self.conn_ga4 = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_ga4,
            name="GA4 Live",
            is_mock=False,
            status="CONNECTED",
            config={"provider_settings": {"tracking": {}}},
            created_at=NOW,
        )
        self.conn_tiktok = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_tiktok,
            name="TikTok Live",
            is_mock=False,
            status="CONNECTED",
            config={},
            created_at=NOW,
        )
        self.conn_slack = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_slack,
            name="Slack Alert",
            is_mock=False,
            status="CONNECTED",
            config={},
            created_at=NOW,
        )
        self.other_conn = IntegrationConnection.objects.create(
            business=self.other_business,
            integration_source=self.source_meta,
            name="Other Meta",
            is_mock=True,
            status="CONNECTED",
            config={},
            created_at=NOW,
        )

        self.client_owner = client_for(self.owner)
        self.client_manager = client_for(self.manager)
        self.client_operator = client_for(self.operator)
        self.client_viewer = client_for(self.viewer)
        self.client_outsider = client_for(self.outsider)

    def test_owner_and_manager_can_save_writable_keys_and_preserve_others(self):
        url = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_meta.pk}/settings/"
        patch_data = {
            "enabled": True,
            "test_mode": True,
            "events": ["PURCHASE", "PAGE_VIEW"],
            "test_event_code": "TEST12345",
            "api_version": "v19.0",
        }
        resp = self.client_manager.patch(url, data=patch_data)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], self.conn_meta.pk)
        self.assertEqual(data["settings"]["enabled"], True)
        self.assertEqual(data["settings"]["test_mode"], True)
        self.assertEqual(data["settings"]["events"], ["PURCHASE", "PAGE_VIEW"])
        self.assertEqual(data["settings"]["test_event_code"], "TEST12345")
        self.assertEqual(data["settings"]["api_version"], "v19.0")
        self.assertEqual(data["settings"]["send_pii"], False)

        # Verify DB
        self.conn_meta.refresh_from_db()
        self.assertEqual(self.conn_meta.config["other"], 2)
        self.assertEqual(self.conn_meta.config["provider_settings"]["keep"], 1)
        tracking_cfg = self.conn_meta.config["provider_settings"]["tracking"]
        self.assertEqual(tracking_cfg["enabled"], True)
        self.assertEqual(tracking_cfg["test_mode"], True)
        self.assertEqual(tracking_cfg["events"], ["PURCHASE", "PAGE_VIEW"])
        self.assertEqual(tracking_cfg["test_event_code"], "TEST12345")
        self.assertEqual(tracking_cfg["api_version"], "v19.0")

    def test_null_removes_nullable_keys(self):
        url = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_meta.pk}/settings/"
        patch_data = {
            "test_event_code": None,
            "api_version": None,
        }
        resp = self.client_owner.patch(url, data=patch_data)
        self.assertEqual(resp.status_code, 200)
        self.conn_meta.refresh_from_db()
        tracking_cfg = self.conn_meta.config["provider_settings"]["tracking"]
        self.assertNotIn("test_event_code", tracking_cfg)
        self.assertNotIn("api_version", tracking_cfg)

    def test_ga4_measurement_id_and_tiktok_test_event_code(self):
        # GA4 valid measurement_id
        url_ga4 = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_ga4.pk}/settings/"
        r_ga4 = self.client_manager.patch(
            url_ga4,
            data={"measurement_id": "G-12345678"},
        )
        self.assertEqual(r_ga4.status_code, 200)
        self.conn_ga4.refresh_from_db()
        self.assertEqual(self.conn_ga4.config["provider_settings"]["tracking"]["measurement_id"], "G-12345678")

        # TikTok valid test_event_code
        url_tt = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_tiktok.pk}/settings/"
        r_tt = self.client_owner.patch(
            url_tt,
            data={"test_event_code": "TEST_TT_99"},
        )
        self.assertEqual(r_tt.status_code, 200)
        self.conn_tiktok.refresh_from_db()
        self.assertEqual(self.conn_tiktok.config["provider_settings"]["tracking"]["test_event_code"], "TEST_TT_99")

    def test_rejections_and_validation_errors_400(self):
        url_meta = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_meta.pk}/settings/"

        # Empty body
        r = self.client_owner.patch(url_meta, data={})
        self.assertEqual(r.status_code, 400)

        # Non-object body
        r = self.client_owner.patch(url_meta, data=["enabled"])
        self.assertEqual(r.status_code, 400)

        # Unknown / forbidden keys
        for bad_key in ("send_pii", "is_mock", "credentials", "api_secret", "access_token", "bogus"):
            r = self.client_owner.patch(
                url_meta,
                data={bad_key: True},
            )
            self.assertEqual(r.status_code, 400, f"Key {bad_key} should return 400")
            self.assertEqual(r.json()["code"], "INVALID_DATA")
            self.assertIn(bad_key, r.json()["fields"])

        # Wrong type: enabled not bool
        r = self.client_owner.patch(url_meta, data={"enabled": "yes"})
        self.assertEqual(r.status_code, 400)

        # Bad event name
        r = self.client_owner.patch(url_meta, data={"events": ["BOGUS_EVENT"]})
        self.assertEqual(r.status_code, 400)

        # Too many events (> 30)
        r = self.client_owner.patch(url_meta, data={"events": ["PURCHASE"] * 31})
        self.assertEqual(r.status_code, 400)

        # Provider specific key on wrong provider: measurement_id on Meta
        r = self.client_owner.patch(url_meta, data={"measurement_id": "G-12345"})
        self.assertEqual(r.status_code, 400)

        # Provider specific key on wrong provider: api_version on GA4
        url_ga4 = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_ga4.pk}/settings/"
        r = self.client_owner.patch(url_ga4, data={"api_version": "v18.0"})
        self.assertEqual(r.status_code, 400)

        # Bad measurement_id format
        r = self.client_owner.patch(url_ga4, data={"measurement_id": "NOT-G-ID"})
        self.assertEqual(r.status_code, 400)

        # Bad api_version format
        r = self.client_owner.patch(url_meta, data={"api_version": "version18"})
        self.assertEqual(r.status_code, 400)

    def test_permissions_roles(self):
        url = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_meta.pk}/settings/"
        patch_data = {"enabled": True}

        # OPERATOR gets 403
        r_op = self.client_operator.patch(url, data=patch_data)
        self.assertEqual(r_op.status_code, 403)

        # VIEWER gets 403
        r_view = self.client_viewer.patch(url, data=patch_data)
        self.assertEqual(r_view.status_code, 403)

        # Outsider gets 403
        r_out = self.client_outsider.patch(url, data=patch_data)
        self.assertEqual(r_out.status_code, 403)

        # Verify nothing was changed by failed role attempts
        self.conn_meta.refresh_from_db()
        self.assertEqual(self.conn_meta.config["provider_settings"]["tracking"]["enabled"], False)

    def test_foreign_and_non_tracking_connections_return_404(self):
        # Foreign connection
        url_other = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.other_conn.pk}/settings/"
        r1 = self.client_owner.patch(url_other, data={"enabled": True})
        self.assertEqual(r1.status_code, 404)

        # Non-tracking connection (Slack)
        url_slack = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_slack.pk}/settings/"
        r2 = self.client_owner.patch(url_slack, data={"enabled": True})
        self.assertEqual(r2.status_code, 404)

    def test_response_matches_summary_entry(self):
        url_summary = f"/api/businesses/{self.business.pk}/integrations/tracking/summary/"
        url_patch = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_meta.pk}/settings/"

        r_patch = self.client_owner.patch(url_patch, data={"enabled": True})
        self.assertEqual(r_patch.status_code, 200)
        patch_entry = r_patch.json()

        r_summary = self.client_owner.get(url_summary)
        self.assertEqual(r_summary.status_code, 200)
        summary_entries = r_summary.json()["connections"]
        matched_entry = next(c for c in summary_entries if c["id"] == self.conn_meta.pk)

        self.assertEqual(patch_entry, matched_entry)

    def test_real_round_trip_with_adapter_and_unsupported_filtering(self):
        # Configure connection to only allow PURCHASE
        url = f"/api/businesses/{self.business.pk}/integrations/tracking/connections/{self.conn_meta.pk}/settings/"
        r = self.client_owner.patch(
            url,
            data={"enabled": True, "events": ["PURCHASE"]},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.status_code, 200)

        self.conn_meta.refresh_from_db()
        cfg = get_tracking_config(self.conn_meta)
        self.assertEqual(cfg["enabled"], True)
        self.assertEqual(cfg["events"], ["PURCHASE"])

        # Setup event PAGE_VIEW (not in allowed list)
        visitor = WebsiteVisitor.objects.create(business=self.business, visitor_key="v-1", first_seen_at=NOW)
        session = WebsiteSession.objects.create(business=self.business, visitor=visitor, started_at=NOW)
        page_event = WebsiteEvent.objects.create(
            session=session, visitor=visitor, event_type="PAGE_VIEW", occurred_at=NOW
        )

        # Process tracking event: PAGE_VIEW should record an UNSUPPORTED attempt
        attempt = process_tracking_event(self.conn_meta, page_event)
        self.assertEqual(attempt.status, "UNSUPPORTED")
        self.assertEqual(attempt.result.get("reason"), "EVENT_NOT_IN_ALLOW_LIST")

