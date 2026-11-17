"""Tests for tracking configuration resolver (TRK-1)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.exceptions import ValidationError as DRFValidationError

from app.configuration.integrations import save_connection
from app.integrations.tracking.config import get_tracking_config
from app.models import IntegrationConnection
from app.tests.observability_helpers import NOW, setup_businesses


class TrackingConfigUnitTests(TestCase):
    """Unit tests for get_tracking_config precedence, copies, and fallback."""

    def test_provider_settings_wins_over_legacy(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.config = {
            "provider_settings": {
                "tracking": {"enabled": True, "pixel_id": "ps_123"}
            },
            "tracking": {"enabled": False, "pixel_id": "legacy_999"},
        }
        cfg = get_tracking_config(conn)
        self.assertEqual(cfg, {"enabled": True, "pixel_id": "ps_123"})

    def test_legacy_still_works_alone(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.config = {
            "tracking": {"enabled": True, "pixel_id": "legacy_alone"}
        }
        cfg = get_tracking_config(conn)
        self.assertEqual(cfg, {"enabled": True, "pixel_id": "legacy_alone"})

    def test_neither_gives_empty_dict(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.config = {"other": 123}
        self.assertEqual(get_tracking_config(conn), {})

    def test_non_dict_values_give_empty_dict(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.config = None
        self.assertEqual(get_tracking_config(conn), {})

        conn.config = {"tracking": "not_a_dict"}
        self.assertEqual(get_tracking_config(conn), {})

        conn.config = {"provider_settings": {"tracking": "not_a_dict"}}
        self.assertEqual(get_tracking_config(conn), {})

        conn.config = {"provider_settings": "not_a_dict", "tracking": None}
        self.assertEqual(get_tracking_config(conn), {})

    def test_returned_dict_is_a_copy(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.config = {
            "provider_settings": {
                "tracking": {"enabled": True, "events": ["PURCHASE"]}
            }
        }
        cfg = get_tracking_config(conn)
        cfg["enabled"] = False
        cfg["events"].append("PAGE_VIEW")

        # Mutating cfg should not affect the stored config
        self.assertTrue(conn.config["provider_settings"]["tracking"]["enabled"])


class TrackingConfigApiIntegrationTests(TestCase):
    """Integration test through app.configuration.integrations.save_connection."""

    def setUp(self):
        setup_businesses(self)

    def test_save_connection_with_provider_settings_tracking(self):
        saved = save_connection(
            self.business.pk,
            self.user,
            {"provider_settings": {"tracking": {"enabled": True, "events": ["PURCHASE"]}}},
            NOW,
            pk=self.connection.pk,
        )
        self.connection.refresh_from_db()
        cfg = get_tracking_config(self.connection)
        self.assertEqual(cfg, {"enabled": True, "events": ["PURCHASE"]})

    def test_top_level_tracking_key_rejected_by_api(self):
        with self.assertRaises((ValidationError, DRFValidationError)):
            save_connection(
                self.business.pk,
                self.user,
                {"tracking": {"enabled": True, "events": ["PURCHASE"]}},
                NOW,
                pk=self.connection.pk,
            )
