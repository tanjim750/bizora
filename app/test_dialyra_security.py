"""Local-only regressions for webhook authentication and call ownership."""
import os
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from app.models import Business, Call, CallEvent, CallTranscript
from app.services.dialyra_service import DialyraService, DialyraValidationError


class DialyraWebhookSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.business = Business.objects.create(name="Webhook tenant", slug="webhook-tenant")
        self.other = Business.objects.create(name="Other tenant", slug="other-webhook-tenant")
        self.service = DialyraService(business=self.business)
        self.other_service = DialyraService(business=self.other)
        self.call = self.make_call(self.business)
        self.other_call = self.make_call(self.other)
        self.payload = {"event": "call.completed", "call_log_uuid": "shared-provider-id",
                        "status": "COMPLETED", "transcript": "Verified provider transcript"}
        self.url = f"/api/businesses/{self.business.pk}/dialyra/webhook/"
        self.env = patch.dict(os.environ, {
            f"BIZORA_BUSINESS_{self.business.pk}_DIALYRA_WEBHOOK_SECRET": "tenant-one-test-secret",
            f"BIZORA_BUSINESS_{self.other.pk}_DIALYRA_WEBHOOK_SECRET": "tenant-two-test-secret",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def make_call(self, business):
        return Call.objects.create(business=business,
            integration_connection=DialyraService.get_or_create_connection(business),
            external_call_id="shared-provider-id", direction="OUTGOING", status="INITIATED")

    def test_legacy_public_webhook_cannot_modify_calls(self):
        response = self.client.post("/api/dialyra/webhook/", self.payload, format="json")
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, "INITIATED")
        self.assertFalse(CallEvent.objects.exists())
        self.assertFalse(CallTranscript.objects.exists())
        self.assertEqual(response.status_code, 410)

    def test_scoped_webhook_requires_correct_tenant_secret(self):
        for token in (None, "Bearer wrong", "Bearer tenant-two-test-secret", "Bearer non-ascii-\u00e9"):
            with self.subTest(token=token):
                headers = {"HTTP_AUTHORIZATION": token} if token else {}
                response = self.client.post(self.url, self.payload, format="json", **headers)
                self.assertEqual(response.status_code, 401)
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, "INITIATED")
        self.assertFalse(CallEvent.objects.exists())

    def test_webhook_is_disabled_without_configured_secret(self):
        with patch.dict(os.environ, {f"BIZORA_BUSINESS_{self.business.pk}_DIALYRA_WEBHOOK_SECRET": ""}):
            response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(CallEvent.objects.exists())

    def test_authenticated_event_updates_only_its_business(self):
        response = self.client.post(self.url, self.payload, format="json",
                                    HTTP_AUTHORIZATION="Bearer tenant-one-test-secret")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["call_id"], self.call.pk)
        self.call.refresh_from_db()
        self.other_call.refresh_from_db()
        self.assertEqual(self.call.status, "COMPLETED")
        self.assertEqual(self.other_call.status, "INITIATED")
        self.assertEqual(CallEvent.objects.get().call_id, self.call.pk)
        self.assertEqual(CallTranscript.objects.get().call_id, self.call.pk)

    def test_service_never_selects_another_tenants_matching_call(self):
        result = self.other_service.handle_webhook_event(self.payload)
        self.assertEqual(result["call_id"], self.other_call.pk)
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, "INITIATED")

    def test_service_ignores_matching_call_from_another_provider(self):
        self.call.integration_connection = None
        self.call.save(update_fields=["integration_connection"])
        result = self.service.handle_webhook_event(self.payload)
        self.assertEqual(result["status"], "unmatched_call")
        self.assertFalse(CallEvent.objects.exists())

    def test_unscoped_service_cannot_process_webhooks(self):
        with self.assertRaises(DialyraValidationError):
            DialyraService().handle_webhook_event(self.payload)
