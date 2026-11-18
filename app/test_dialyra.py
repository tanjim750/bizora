"""
Comprehensive unit tests for the Dialyra Telephony integration in Bizora.
Tests DialyraService, error handling, model synchronization, and REST endpoints
with mocked external HTTP responses per Dialyra-docs v2/v3 schemas.
"""

import json
import os
from unittest.mock import MagicMock, patch
import urllib.error

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from app.models import (
    Business,
    BusinessMembership,
    Call,
    CallEvent,
    CallTranscript,
    Customer,
    IntegrationConnection,
    IntegrationSource,
)
from app.services.dialyra_service import (
    DialyraAuthError,
    DialyraBillingError,
    DialyraConnectionError,
    DialyraNotFoundError,
    DialyraService,
    DialyraTrunkNotReadyError,
    DialyraValidationError,
)

User = get_user_model()


class DialyraServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testoperator", password="testpassword123")
        self.business = Business.objects.create(name="Test Telephony Business", slug="test-telephony-biz")
        self.membership = BusinessMembership.objects.create(
            user=self.user, business=self.business, role="OWNER", is_active=True
        )
        self.customer = Customer.objects.create(
            business=self.business, display_name="Rahim Buyer"
        )
        self.service = DialyraService(api_key="test-dialyra-key", business=self.business)

    def test_service_initialization_and_configuration(self):
        """Test API key resolution from argument, connection config, and environment."""
        # 1. Direct key
        srv1 = DialyraService(api_key="custom-key")
        self.assertTrue(srv1.is_configured)
        self.assertEqual(srv1.api_key, "custom-key")

        # 2. Connection config
        conn = DialyraService.get_or_create_connection(self.business)
        conn.config = {"api_key": "conn-key", "base_url": "https://custom.dialyra.com"}
        conn.save()

        srv2 = DialyraService(business=self.business)
        self.assertTrue(srv2.is_configured)
        self.assertEqual(srv2.api_key, "conn-key")
        self.assertEqual(srv2.base_url, "https://custom.dialyra.com")

    @patch("urllib.request.urlopen")
    def test_check_health_success(self, mock_urlopen):
        """Test health check success (GET /api/v2/health)."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = self.service.check_health()
        self.assertEqual(res, {"status": "ok"})
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_originate_call_v3_success(self, mock_urlopen):
        """Test v3 runtime call origination and canonical Call model creation."""
        mock_dialyra_resp = {
            "status": "initiated",
            "phone": "01712345678",
            "business_id": 1,
            "call_log_uuid": "3abaf575-5980-4db2-a2c3-1338ec44a4ee",
            "call_session_id": 170,
            "action_id": "102bae32-7661-4161-95e0-bd0b9d535af4",
            "sip_trunk_id": 20,
            "sip_endpoint": "dialyra_b1_t20_trizync_ep",
            "selected_by": "requested",
            "selected_flow_id": 7,
            "flow_selected_by": "explicit_flow_id",
            "api_version_used": "v3",
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_dialyra_resp).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = self.service.originate_call(
            phone="01712345678",
            sip_trunk_id=20,
            flow_id=7,
            webhook_variables={"customer_name": "Rahim", "order_id": "1001"},
            customer=self.customer,
            user=self.user,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["external_call_id"], "3abaf575-5980-4db2-a2c3-1338ec44a4ee")

        # Verify database Call record
        call = Call.objects.get(pk=result["call_id"])
        self.assertEqual(call.business, self.business)
        self.assertEqual(call.customer, self.customer)
        self.assertEqual(call.receiver_number, "01712345678")
        self.assertEqual(call.status, "INITIATED")
        self.assertEqual(call.direction, "OUTGOING")
        self.assertEqual(call.external_call_id, "3abaf575-5980-4db2-a2c3-1338ec44a4ee")

        # Verify CallEvent record
        event = CallEvent.objects.filter(call=call).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "INITIATED")

    def test_originate_call_validation_errors(self):
        """Test client-side validation before network call."""
        # Missing phone
        with self.assertRaises(DialyraValidationError):
            self.service.originate_call(phone="")

        # Invalid webhook_variables type
        with self.assertRaises(DialyraValidationError):
            self.service.originate_call(phone="01712345678", webhook_variables="not-a-dict")

        # Invalid webhook key
        with self.assertRaises(DialyraValidationError):
            self.service.originate_call(phone="01712345678", webhook_variables={"invalid-key!": "val"})

    @patch("urllib.request.urlopen")
    def test_originate_call_trunk_not_ready_409(self, mock_urlopen):
        """Test HTTP 409 TRUNK_NOT_READY mapping."""
        err_body = json.dumps({
            "status": "warning",
            "code": "TRUNK_NOT_READY",
            "message": "registration_not_ready",
            "trunk_diagnostics": {"originate_eligible": False},
        }).encode("utf-8")

        mock_err = urllib.error.HTTPError(
            url="http://test", code=409, msg="Conflict", hdrs={}, fp=MagicMock(read=lambda: err_body)
        )
        mock_urlopen.side_effect = mock_err

        with self.assertRaises(DialyraTrunkNotReadyError) as ctx:
            self.service.originate_call(phone="01712345678", sip_trunk_id=20)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("registration_not_ready", ctx.exception.message)

    @patch("urllib.request.urlopen")
    def test_originate_call_insufficient_credit_402(self, mock_urlopen):
        """Test HTTP 402 INSUFFICIENT_CREDIT mapping."""
        err_body = json.dumps({
            "error": "insufficient credits",
            "code": "INSUFFICIENT_CREDIT",
            "required_credit": "2.000000",
            "available_credit": "1.000000",
        }).encode("utf-8")

        mock_err = urllib.error.HTTPError(
            url="http://test", code=402, msg="Payment Required", hdrs={}, fp=MagicMock(read=lambda: err_body)
        )
        mock_urlopen.side_effect = mock_err

        with self.assertRaises(DialyraBillingError) as ctx:
            self.service.originate_call(phone="01712345678")

        self.assertEqual(ctx.exception.status_code, 402)
        self.assertIn("insufficient credits", ctx.exception.message)

    @patch("urllib.request.urlopen")
    def test_originate_call_auth_error_401(self, mock_urlopen):
        """Test HTTP 401 unauthorized mapping."""
        err_body = json.dumps({"error": "Invalid or expired access token"}).encode("utf-8")
        mock_err = urllib.error.HTTPError(
            url="http://test", code=401, msg="Unauthorized", hdrs={}, fp=MagicMock(read=lambda: err_body)
        )
        mock_urlopen.side_effect = mock_err

        with self.assertRaises(DialyraAuthError) as ctx:
            self.service.originate_call(phone="01712345678")

        self.assertEqual(ctx.exception.status_code, 401)

    @patch("urllib.request.urlopen")
    def test_sip_trunk_operations_v3(self, mock_urlopen):
        """Test listing, status, testing, and reloading SIP trunks."""
        # 1. List trunks
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"items": [{"id": 20, "name": "Trizync Trunk"}]}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        trunks = self.service.list_sip_trunks()
        self.assertEqual(len(trunks["items"]), 1)

        # 2. Get status
        mock_resp.read.return_value = json.dumps({
            "trunk_id": 20,
            "status": "active",
            "originate_eligible": True,
            "registration_status": "registered",
        }).encode("utf-8")

        status_data = self.service.get_sip_trunk_status(20)
        self.assertTrue(status_data["originate_eligible"])

        # 3. Test trunk
        mock_resp.read.return_value = json.dumps({"success": True, "message": "Test successful"}).encode("utf-8")
        test_res = self.service.test_sip_trunk(20)
        self.assertTrue(test_res["success"])

        # 4. Reload trunk
        mock_resp.read.return_value = json.dumps({"reload": {"status": "reloaded"}}).encode("utf-8")
        reload_res = self.service.reload_sip_trunk(20, enable_inbound=True)
        self.assertEqual(reload_res["reload"]["status"], "reloaded")

    def test_create_sip_trunk_validation(self):
        """Test create SIP trunk schema validation."""
        # Missing required field
        with self.assertRaises(DialyraValidationError):
            self.service.create_sip_trunk({"name": "Trunk"})

        # Invalid mode
        with self.assertRaises(DialyraValidationError):
            self.service.create_sip_trunk({
                "name": "Trunk",
                "provider_name": "Carrier",
                "trunk_mode": "invalid_mode",
                "host": "sip.carrier.com",
                "max_concurrent_calls": 10,
            })

        # Registration mode requires username and password
        with self.assertRaises(DialyraValidationError):
            self.service.create_sip_trunk({
                "name": "Trunk",
                "provider_name": "Carrier",
                "trunk_mode": "registration",
                "host": "sip.carrier.com",
                "max_concurrent_calls": 10,
            })

    def test_handle_webhook_event(self):
        """Test processing webhook event updates Call status, events, and transcripts."""
        # Create an existing Call
        call = Call.objects.create(
            business=self.business,
            integration_connection=DialyraService.get_or_create_connection(self.business),
            customer=self.customer,
            external_call_id="call-uuid-12345",
            direction="OUTGOING",
            receiver_number="01712345678",
            status="INITIATED",
        )

        webhook_payload = {
            "event": "call.completed",
            "call_log_uuid": "call-uuid-12345",
            "status": "COMPLETED",
            "duration_seconds": 125,
            "recording_url": "https://storage.dialyra.com/recordings/call-12345.wav",
            "transcript": "Hello, thank you for confirming the tea order.",
            "summary": "Customer confirmed order delivery address.",
        }

        res = self.service.handle_webhook_event(webhook_payload)
        self.assertEqual(res["status"], "processed")
        self.assertEqual(res["call_id"], call.pk)

        # Verify Call is updated
        call.refresh_from_db()
        self.assertEqual(call.status, "COMPLETED")
        self.assertEqual(call.duration_seconds, 125)
        self.assertEqual(call.recording_url, "https://storage.dialyra.com/recordings/call-12345.wav")

        # Verify CallTranscript is created
        transcript = CallTranscript.objects.get(call=call)
        self.assertEqual(transcript.summary, "Customer confirmed order delivery address.")
        self.assertEqual(transcript.provider, "dialyra")


class DialyraViewsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="apiuser", password="apipassword123")
        self.business = Business.objects.create(name="View Test Business", slug="view-test-biz")
        self.membership = BusinessMembership.objects.create(
            user=self.user, business=self.business, role="OWNER", is_active=True
        )
        self.client.force_authenticate(user=self.user)

    def test_status_endpoint(self):
        """GET /api/businesses/:id/dialyra/status/"""
        url = reverse("dialyra-status", kwargs={"business_id": self.business.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("supported_capabilities", response.data)
        self.assertIn("connection", response.data)

    @patch("app.services.dialyra_service.DialyraService.originate_call")
    def test_originate_call_endpoint(self, mock_originate):
        """POST /api/businesses/:id/dialyra/calls/originate/"""
        mock_originate.return_value = {
            "success": True,
            "call_id": 99,
            "external_call_id": "test-uuid-99",
            "dialyra": {"status": "initiated"},
        }

        url = reverse("dialyra-originate-call", kwargs={"business_id": self.business.pk})
        response = self.client.post(url, {"phone": "01711223344", "sip_trunk_id": 10}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["call_id"], 99)
        mock_originate.assert_called_once()

    def test_originate_call_missing_phone_400(self):
        """POST /api/businesses/:id/dialyra/calls/originate/ with missing phone returns 400."""
        url = reverse("dialyra-originate-call", kwargs={"business_id": self.business.pk})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("urllib.request.urlopen")
    def test_originate_call_rejects_malformed_inputs_without_transport(self, mock_urlopen):
        url = reverse("dialyra-originate-call", kwargs={"business_id": self.business.pk})
        for payload in (["phone"], {"phone": 123}, {"phone": {"number": "01711223344"}}):
            with self.subTest(payload=payload):
                response = self.client.post(url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_urlopen.assert_not_called()

    @patch("app.services.dialyra_service.DialyraService.list_sip_trunks")
    def test_trunks_list_endpoint(self, mock_list):
        """GET /api/businesses/:id/dialyra/trunks/"""
        mock_list.return_value = {"items": [{"id": 1, "name": "Primary Trunk"}]}
        url = reverse("dialyra-trunks", kwargs={"business_id": self.business.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 1)

    @patch("app.services.dialyra_service.DialyraService.handle_webhook_event")
    def test_webhook_endpoint(self, mock_handle):
        """Provider callbacks require the secret belonging to the URL business."""
        self.client.logout()  # Unauthenticated webhook caller
        mock_handle.return_value = {"status": "processed", "call_id": 42}

        url = reverse("dialyra-business-webhook", kwargs={"business_id": self.business.pk})
        with patch.dict(os.environ, {f"BIZORA_BUSINESS_{self.business.pk}_DIALYRA_WEBHOOK_SECRET": "test-secret"}):
            response = self.client.post(
                url,
                {"event": "call.completed", "call_log_uuid": "ext-123", "status": "COMPLETED"},
                format="json", HTTP_AUTHORIZATION="Bearer test-secret",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "processed")
        mock_handle.assert_called_once()
