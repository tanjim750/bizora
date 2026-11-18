"""
Dialyra Telephony API Views for Bizora.

Provides authenticated endpoints for:
- Dialyra integration status & diagnostics
- Outbound Call Origination (v3 runtime)
- SIP Trunk management & real-time Asterisk status (v3)
- IVR Flow listings (v2)
- Dialyra Webhook callback ingestion
"""

import logging
import os
from secrets import compare_digest
from typing import Any

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app import models as m
from app.domain_views import DomainAPIView
from app.domains.common import require
from app.services.dialyra_service import (
    DialyraAuthError,
    DialyraBillingError,
    DialyraConnectionError,
    DialyraError,
    DialyraNotFoundError,
    DialyraService,
    DialyraTrunkNotReadyError,
    DialyraValidationError,
)

logger = logging.getLogger(__name__)


class DialyraBaseView(DomainAPIView):
    """Base API view for Dialyra endpoints with unified error mapping."""

    def get_service(self, business: m.Business) -> DialyraService:
        return DialyraService(business=business)

    def handle_exception(self, exc: Exception) -> Response:
        if isinstance(exc, DialyraAuthError):
            return Response(
                {"error": exc.message, "code": "DIALYRA_AUTH_ERROR", "details": exc.response_data},
                status=status.HTTP_403_FORBIDDEN,
            )
        if isinstance(exc, DialyraValidationError):
            return Response(
                {"error": exc.message, "code": "DIALYRA_VALIDATION_ERROR", "details": exc.response_data},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(exc, DialyraNotFoundError):
            return Response(
                {"error": exc.message, "code": "DIALYRA_NOT_FOUND", "details": exc.response_data},
                status=status.HTTP_404_NOT_FOUND,
            )
        if isinstance(exc, DialyraBillingError):
            return Response(
                {"error": exc.message, "code": "DIALYRA_BILLING_ERROR", "details": exc.response_data},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        if isinstance(exc, DialyraTrunkNotReadyError):
            return Response(
                {"error": exc.message, "code": "DIALYRA_TRUNK_NOT_READY", "details": exc.response_data},
                status=status.HTTP_409_CONFLICT,
            )
        if isinstance(exc, DialyraConnectionError):
            return Response(
                {"error": exc.message, "code": "DIALYRA_CONNECTION_ERROR", "details": exc.response_data},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if isinstance(exc, DialyraError):
            http_status = exc.status_code if exc.status_code and 400 <= exc.status_code < 600 else 400
            return Response(
                {"error": exc.message, "code": "DIALYRA_ERROR", "details": exc.response_data},
                status=http_status,
            )
        return super().handle_exception(exc)


class DialyraStatusView(DialyraBaseView):
    """
    GET /api/businesses/:business_id/dialyra/status/
    Returns Dialyra configuration, connection health, and capabilities.
    """

    def get(self, request, business_id: int):
        business = self.business(request, business_id)
        service = self.get_service(business)
        connection = DialyraService.get_or_create_connection(business)

        health_data = None
        health_error = None
        if service.is_configured:
            try:
                health_data = service.check_health()
            except Exception as e:
                health_error = str(e)

        return Response(
            {
                "configured": service.is_configured,
                "base_url": service.base_url,
                "auth_mode": "API_KEY" if service.is_configured else "NONE",
                "connection": {
                    "id": connection.pk,
                    "name": connection.name,
                    "status": connection.status,
                    "last_synced_at": connection.last_synced_at,
                },
                "health": health_data,
                "health_error": health_error,
                "supported_capabilities": [
                    "originate_calls_v3",
                    "sip_trunks_v3",
                    "realtime_asterisk_status",
                    "ivr_flows_v2",
                    "webhook_events",
                    "call_transcripts",
                ],
            }
        )


class DialyraOriginateCallView(DialyraBaseView):
    """
    POST /api/businesses/:business_id/dialyra/calls/originate/
    Starts an outbound call via Dialyra v3 runtime API and records the canonical Call.
    """

    def post(self, request, business_id: int):
        business = self.business(request, business_id, write=True)
        service = self.get_service(business)

        data = request.data or {}
        require(isinstance(data, dict), "INVALID_DATA", "Payload must be a JSON object.")
        phone = data.get("phone")
        require(bool(phone), "INVALID_PHONE", "Phone number is required.")

        sip_trunk_id = data.get("sip_trunk_id")
        flow_id = data.get("flow_id")
        campaign_id = data.get("campaign_id")
        campaign_flow_id = data.get("campaign_flow_id")
        webhook_variables = data.get("webhook_variables")
        customer_id = data.get("customer_id")

        customer = None
        if customer_id:
            customer = m.Customer.objects.filter(pk=customer_id, business=business).first()

        result = service.originate_call(
            phone=phone,
            sip_trunk_id=sip_trunk_id,
            flow_id=flow_id,
            campaign_id=campaign_id,
            campaign_flow_id=campaign_flow_id,
            webhook_variables=webhook_variables,
            customer=customer,
            user=request.user,
        )

        return Response(result, status=status.HTTP_201_CREATED)


class DialyraSipTrunkListView(DialyraBaseView):
    """
    GET /api/businesses/:business_id/dialyra/trunks/
    POST /api/businesses/:business_id/dialyra/trunks/
    List or create SIP trunks in Dialyra.
    """

    def get(self, request, business_id: int):
        business = self.business(request, business_id)
        service = self.get_service(business)
        result = service.list_sip_trunks()
        return Response(result)

    def post(self, request, business_id: int):
        business = self.business(request, business_id, write=True, manager=True)
        service = self.get_service(business)
        trunk_data = dict(request.data or {})
        trunk_data.setdefault("business_id", business.pk)
        result = service.create_sip_trunk(trunk_data)
        return Response(result, status=status.HTTP_201_CREATED)


class DialyraSipTrunkStatusView(DialyraBaseView):
    """
    GET /api/businesses/:business_id/dialyra/trunks/:trunk_id/status/
    Returns live Asterisk/PJSIP status, registration, and originate eligibility.
    """

    def get(self, request, business_id: int, trunk_id: int):
        business = self.business(request, business_id)
        service = self.get_service(business)
        result = service.get_sip_trunk_status(trunk_id)
        return Response(result)


class DialyraSipTrunkTestView(DialyraBaseView):
    """
    POST /api/businesses/:business_id/dialyra/trunks/:trunk_id/test/
    Tests SIP trunk connectivity and credentials.
    """

    def post(self, request, business_id: int, trunk_id: int):
        business = self.business(request, business_id, write=True, manager=True)
        service = self.get_service(business)
        result = service.test_sip_trunk(trunk_id)
        return Response(result)


class DialyraSipTrunkReloadView(DialyraBaseView):
    """
    POST /api/businesses/:business_id/dialyra/trunks/:trunk_id/reload/
    Syncs and reloads SIP trunk in Asterisk.
    """

    def post(self, request, business_id: int, trunk_id: int):
        business = self.business(request, business_id, write=True, manager=True)
        service = self.get_service(business)
        enable_inbound = bool(request.data.get("enable_inbound", False))
        result = service.reload_sip_trunk(trunk_id, enable_inbound=enable_inbound)
        return Response(result)


class DialyraFlowListView(DialyraBaseView):
    """
    GET /api/businesses/:business_id/dialyra/flows/
    Lists available IVR flows from Dialyra.
    """

    def get(self, request, business_id: int):
        business = self.business(request, business_id)
        service = self.get_service(business)
        result = service.list_flows()
        return Response(result)


@method_decorator(csrf_exempt, name="dispatch")
class DialyraWebhookView(APIView):
    """
    POST /api/businesses/:business_id/dialyra/webhook/
    Provider callback authenticated by a business-specific bearer secret.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, business_id=None):
        if business_id is None:
            return Response({"error": "Use the business-scoped Dialyra webhook URL."}, status=410)
        secret = os.environ.get(f"BIZORA_BUSINESS_{business_id}_DIALYRA_WEBHOOK_SECRET")
        if not secret:
            return Response({"error": "Dialyra webhook is not configured."}, status=503)
        authorization = request.headers.get("Authorization", "")
        if not compare_digest(authorization.encode(), f"Bearer {secret}".encode()):
            return Response({"error": "Invalid webhook authentication."}, status=401)
        business = m.Business.objects.filter(pk=business_id).first()
        if business is None:
            return Response({"error": "Business not found."}, status=404)
        payload = request.data
        if not isinstance(payload, dict):
            return Response({"error": "Payload must be a JSON object."}, status=status.HTTP_400_BAD_REQUEST)

        service = DialyraService(business=business)
        result = service.handle_webhook_event(payload)
        return Response(result, status=status.HTTP_200_OK)
