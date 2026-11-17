"""Tests for tracking event builder, prepared-only service, and tenant isolation (Phase 2).

Verifies:
- Q1: Prepared-only mode by default (mock connections, zero network calls).
- Q2: Personal identifiers are never sent.
- Q3: OperationAttempt and record_observation receipts are created.
- Idempotency: duplicate processing returns existing attempt.
- Tenant isolation: cross-business event processing raises ValidationError.
- Event allow-list filtering.
"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from app.models import (
    Business,
    Customer,
    CustomerContact,
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

from ..builder import build_tracking_payload, extract_event_contents, identify_provider
from ..service import is_event_allowed, process_tracking_event, should_send_live

NOW = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)


class TrackingServicePreparedTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(
            name="Bizora Store",
            slug="bizora-store",
            currency="BDT",
            created_at=NOW,
            updated_at=NOW,
        )
        self.other_business = Business.objects.create(
            name="Other Store",
            slug="other-store",
            currency="USD",
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

        self.conn_meta = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            name="Meta Pixel Connection",
            is_mock=True,
            external_account_id="pixel_meta_123",
            config={"tracking": {"enabled": True, "api_version": "v18.0"}},
            created_at=NOW,
            updated_at=NOW,
        )
        self.conn_tiktok = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_tiktok,
            name="TikTok Connection",
            is_mock=True,
            external_account_id="pixel_tt_456",
            config={"tracking": {"enabled": True, "partner_name": "Bizora"}},
            created_at=NOW,
            updated_at=NOW,
        )
        self.conn_ga4 = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_ga4,
            name="GA4 Connection",
            is_mock=True,
            external_account_id="G-GA4XYZ123",
            config={"tracking": {"enabled": True, "api_secret": "sec_789"}},
            created_at=NOW,
            updated_at=NOW,
        )

        self.customer = Customer.objects.create(
            business=self.business,
            first_name="Rahim",
            last_name="Uddin",
            display_name="Rahim Uddin",
            status="ACTIVE",
        )
        CustomerContact.objects.create(
            customer=self.customer,
            contact_type="EMAIL",
            value="rahim@example.com",
            normalized_value="rahim@example.com",
        )
        CustomerContact.objects.create(
            customer=self.customer,
            contact_type="PHONE",
            value="+8801712345678",
            normalized_value="8801712345678",
        )
        self.visitor = WebsiteVisitor.objects.create(
            business=self.business,
            customer=self.customer,
            visitor_key="vis_key_001",
            first_seen_at=NOW,
            is_anonymous=False,
        )
        self.session = WebsiteSession.objects.create(
            business=self.business,
            visitor=self.visitor,
            customer=self.customer,
            started_at=NOW,
            landing_page_url="https://bizora.shop/products/panjabi-deluxe",
        )

        self.product = Product.objects.create(
            business=self.business,
            name="Panjabi Deluxe",
            sku="PANJ-001",
            price=Decimal("2500.00"),
            currency="BDT",
            created_at=NOW,
            updated_at=NOW,
        )

    def test_identify_provider(self):
        self.assertEqual(identify_provider(self.conn_meta), "meta")
        self.assertEqual(identify_provider(self.conn_tiktok), "tiktok")
        self.assertEqual(identify_provider(self.conn_ga4), "ga4")

    @patch("urllib.request.urlopen")
    def test_prepared_mock_meta_page_view(self, mock_urlopen):
        """Mock connection generates prepared OperationAttempt and zero network calls."""
        event = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            customer=self.customer,
            event_type="PAGE_VIEW",
            page_url="https://bizora.shop/home",
            occurred_at=NOW,
        )

        attempt = process_tracking_event(self.conn_meta, event)

        mock_urlopen.assert_not_called()
        self.assertEqual(attempt.status, "SUCCEEDED")
        self.assertEqual(attempt.action, "TRACKING_EVENT")
        self.assertEqual(attempt.target_id, event.pk)
        self.assertEqual(attempt.result["mode"], "PREPARED")
        self.assertEqual(attempt.result["provider"], "meta")
        self.assertIn("v18.0", attempt.result["endpoint_url"])

        # Check payload
        payload = attempt.result["payload"]
        self.assertIn("data", payload)
        self.assertEqual(len(payload["data"]), 1)
        item = payload["data"][0]
        self.assertEqual(item["event_name"], "PageView")
        self.assertEqual(item["event_id"], f"bizora_we_{event.pk}")
        self.assertEqual(item["event_source_url"], "https://bizora.shop/home")

        # Verify observation receipt created
        receipt = ObservationReceipt.objects.filter(
            connection=self.conn_meta,
            key=f"tracking:event:{event.pk}:prepared",
        ).first()
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.kind, "provider_request")

    @patch("urllib.request.urlopen")
    def test_prepared_mock_tiktok_view_content_with_product(self, mock_urlopen):
        """TikTok ViewContent properly maps linked product to contents list."""
        event = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            product=self.product,
            event_type="VIEW_ITEM",
            page_url="https://bizora.shop/products/panjabi-deluxe",
            event_value=Decimal("2500.00"),
            currency="BDT",
            occurred_at=NOW,
        )

        attempt = process_tracking_event(self.conn_tiktok, event)

        mock_urlopen.assert_not_called()
        self.assertEqual(attempt.status, "SUCCEEDED")
        self.assertEqual(attempt.result["mode"], "PREPARED")
        self.assertEqual(attempt.result["provider"], "tiktok")

        payload = attempt.result["payload"]
        self.assertIn("data", payload)
        self.assertEqual(len(payload["data"]), 1)
        event_item = payload["data"][0]
        self.assertEqual(event_item["event"], "ViewContent")
        self.assertEqual(event_item["event_id"], f"bizora_we_{event.pk}")
        props = event_item["properties"]
        self.assertEqual(props["currency"], "BDT")
        self.assertEqual(props["value"], 2500.0)
        self.assertEqual(props["contents"][0]["content_id"], "PANJ-001")
        self.assertEqual(props["contents"][0]["content_name"], "Panjabi Deluxe")

    @patch("urllib.request.urlopen")
    def test_prepared_mock_ga4_purchase_with_order(self, mock_urlopen):
        """GA4 purchase event extracts order and order items."""
        order = Order.objects.create(
            business=self.business,
            customer=self.customer,
            order_number="ORD-2026-99",
            status="CONFIRMED",
            currency="BDT",
            total_amount=Decimal("5000.00"),
            ordered_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name="Panjabi Deluxe",
            sku="PANJ-001",
            quantity=2,
            unit_price=Decimal("2500.00"),
            total_amount=Decimal("5000.00"),
        )

        event = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            customer=self.customer,
            order=order,
            event_type="PURCHASE",
            page_url="https://bizora.shop/checkout/success",
            event_value=Decimal("5000.00"),
            currency="BDT",
            occurred_at=NOW,
        )

        attempt = process_tracking_event(self.conn_ga4, event)

        mock_urlopen.assert_not_called()
        self.assertEqual(attempt.status, "SUCCEEDED")
        self.assertEqual(attempt.result["provider"], "ga4")

        payload = attempt.result["payload"]
        self.assertEqual(payload["client_id"], "vis_key_001")
        events = payload["events"]
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["name"], "purchase")
        params = ev["params"]
        self.assertEqual(params["transaction_id"], "ORD-2026-99")
        self.assertEqual(params["value"], 5000.0)
        self.assertEqual(params["currency"], "BDT")
        self.assertEqual(len(params["items"]), 1)
        self.assertEqual(params["items"][0]["item_id"], "PANJ-001")
        self.assertEqual(params["items"][0]["quantity"], 2)

    def test_idempotency_returns_existing_attempt(self):
        """Calling process_tracking_event repeatedly returns existing attempt without duplicate DB rows."""
        event = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            event_type="PAGE_VIEW",
            occurred_at=NOW,
        )

        attempt1 = process_tracking_event(self.conn_meta, event)
        attempt2 = process_tracking_event(self.conn_meta, event)

        self.assertEqual(attempt1.pk, attempt2.pk)
        self.assertEqual(
            OperationAttempt.objects.filter(connection=self.conn_meta, key=f"tracking:event:{event.pk}").count(),
            1,
        )

    def test_tenant_boundary_violation_raises(self):
        """Event belonging to another business raises ValidationError."""
        other_visitor = WebsiteVisitor.objects.create(
            business=self.other_business,
            visitor_key="other_vis",
            first_seen_at=NOW,
        )
        other_session = WebsiteSession.objects.create(
            business=self.other_business,
            visitor=other_visitor,
            started_at=NOW,
        )
        cross_event = WebsiteEvent.objects.create(
            session=other_session,
            visitor=other_visitor,
            event_type="PAGE_VIEW",
            occurred_at=NOW,
        )

        with self.assertRaises(ValidationError) as ctx:
            process_tracking_event(self.conn_meta, cross_event)

        self.assertIn("Tenant boundary violation", str(ctx.exception))

    def test_allow_list_filters_disallowed_events(self):
        """When tracking.events specifies an allow-list, non-matching events return UNSUPPORTED."""
        conn_filtered = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            name="Filtered Connection",
            is_mock=True,
            external_account_id="pixel_filtered",
            config={"tracking": {"enabled": True, "events": ["PURCHASE"]}},
            created_at=NOW,
            updated_at=NOW,
        )
        event = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            event_type="PAGE_VIEW",
            occurred_at=NOW,
        )

        attempt = process_tracking_event(conn_filtered, event)

        self.assertEqual(attempt.status, "UNSUPPORTED")
        self.assertEqual(attempt.result["reason"], "EVENT_NOT_IN_ALLOW_LIST")

    def test_pii_suppressed_under_decision_q2(self):
        """Verify that customer PII (email, phone) is NOT present in prepared payload."""
        event = WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            customer=self.customer,
            event_type="PAGE_VIEW",
            occurred_at=NOW,
        )

        attempt = process_tracking_event(self.conn_meta, event)
        meta_payload = attempt.result["payload"]["data"][0]

        # Meta user_data must not contain raw or hashed email/phone when send_pii is False
        user_data = meta_payload.get("user_data", {})
        self.assertNotIn("em", user_data)
        self.assertNotIn("ph", user_data)
        self.assertNotIn("email", str(attempt.result))
        self.assertNotIn("rahim@example.com", str(attempt.result))

    def test_should_send_live_conditions(self):
        """Verify should_send_live strictly adheres to Q1."""
        # 1. Mock connection -> False
        self.assertFalse(should_send_live(self.conn_meta))

        # 2. Non-mock, but tracking not enabled in config -> False
        conn_real_no_tracking = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            is_mock=False,
            config={},
            created_at=NOW,
            updated_at=NOW,
        )
        self.assertFalse(should_send_live(conn_real_no_tracking))

        # 3. Non-mock, tracking enabled, but credentials unavailable (no ConfigurationRecord) -> False
        conn_real_no_creds = IntegrationConnection.objects.create(
            business=self.business,
            integration_source=self.source_meta,
            is_mock=False,
            config={"tracking": {"enabled": True}},
            created_at=NOW,
            updated_at=NOW,
        )
        self.assertFalse(should_send_live(conn_real_no_creds))

        # 4. Non-mock, tracking enabled, ConfigurationRecord exists with env var -> True
        from app.models import ConfigurationRecord
        import os

        env_var_name = f"BIZORA_BUSINESS_{self.business.pk}_ACCESS_TOKEN"
        os.environ[env_var_name] = "test-token-value-12345"
        try:
            ConfigurationRecord.objects.create(
                business=self.business,
                kind="INTEGRATION",
                key=str(conn_real_no_creds.pk),
                data={
                    "enabled": True,
                    "credentials": {
                        "access_token": f"env:{env_var_name}",
                    },
                },
            )
            self.assertTrue(should_send_live(conn_real_no_creds))
        finally:
            os.environ.pop(env_var_name, None)
