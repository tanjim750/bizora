"""
Dialyra Telephony & SIP Trunk Integration Service for Bizora.

Implements the official Dialyra API specifications (v2 & v3):
- v3 Runtime Call Origination (`POST /api/v3/runtime/calls/originate`) with Access-Token / API Key authentication
- v3 SIP Trunk Management (`/api/v3/sip-trunks`, status, reload, test, health)
- v2 Call Sessions & IVR Flows (`/api/v2/flows`, `/api/v2/calls`)
- Webhook Event Ingestion for real-time call states (answered, ended, recording, transcript)
- Deterministic canonical mapping to Bizora models (Call, CallEvent, CallTranscript, IntegrationConnection)
"""

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from app.models import (
    Business,
    Call,
    CallEvent,
    CallTranscript,
    Customer,
    IntegrationConnection,
    IntegrationSource,
)

logger = logging.getLogger(__name__)

DEFAULT_DIALYRA_BASE_URL = "https://api.dialyra.com"


# ==============================================================================
# Custom Exceptions
# ==============================================================================


class DialyraError(Exception):
    """Base exception for all Dialyra integration errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}


class DialyraAuthError(DialyraError):
    """Raised when authentication with Dialyra fails or permissions are insufficient."""
    pass


class DialyraValidationError(DialyraError):
    """Raised when request payload fails validation rules per Dialyra schema."""
    pass


class DialyraNotFoundError(DialyraError):
    """Raised when a requested Dialyra resource does not exist."""
    pass


class DialyraTrunkNotReadyError(DialyraError):
    """Raised when a SIP trunk is not ready or ineligible to originate calls (HTTP 409)."""
    pass


class DialyraBillingError(DialyraError):
    """Raised when credit is insufficient or billing policy blocks call origination (HTTP 402)."""
    pass


class DialyraConnectionError(DialyraError):
    """Raised when Dialyra or Asterisk AMI network transport fails (HTTP 502/503/timeout)."""
    pass


# ==============================================================================
# Dialyra Service Client
# ==============================================================================


class DialyraService:
    """
    Dedicated, isolated service for interacting with Dialyra Telephony API.
    Supports environment-based credentials with per-business connection overrides.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        business: Optional[Business] = None,
        timeout: int = 15,
    ):
        self.business = business
        self.timeout = timeout

        # 1. Check passed credentials
        # 2. Check per-business IntegrationConnection config
        # 3. Check environment variables
        env_key = os.environ.get("DIALYRA_API_KEY") or os.environ.get("DIALYRA_ACCESS_TOKEN")
        env_base = os.environ.get("DIALYRA_BASE_URL") or DEFAULT_DIALYRA_BASE_URL

        conn_key = None
        conn_base = None
        if business:
            conn = self.get_or_create_connection(business)
            if conn and conn.config:
                conn_key = conn.config.get("api_key") or conn.config.get("access_token")
                conn_base = conn.config.get("base_url")

        self.api_key = api_key or conn_key or env_key or ""
        self.base_url = (base_url or conn_base or env_base).rstrip("/")

    @classmethod
    def get_or_create_source(cls) -> IntegrationSource:
        """Ensures the Dialyra IntegrationSource exists in Bizora."""
        source, _ = IntegrationSource.objects.get_or_create(
            key="dialyra",
            defaults={
                "name": "Dialyra Voice & Telephony",
                "category": "TELEPHONY",
                "connection_type": "API_KEY",
            },
        )
        return source

    @classmethod
    def get_or_create_connection(cls, business: Business) -> IntegrationConnection:
        """Gets or creates the Dialyra IntegrationConnection for a given business."""
        source = cls.get_or_create_source()
        connection, _ = IntegrationConnection.objects.get_or_create(
            business=business,
            integration_source=source,
            defaults={
                "name": f"Dialyra ({business.name})",
                "status": "CONNECTED",
                "is_mock": False,
                "config": {},
            },
        )
        return connection

    @property
    def is_configured(self) -> bool:
        """Checks if the service has an API key/token available."""
        return bool(self.api_key)

    def _get_headers(self) -> Dict[str, str]:
        """Constructs request headers following Dialyra v2/v3 authentication rules."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Bizora-Dialyra-Integration/1.0",
        }
        if self.api_key:
            headers["X-Dialyra-Access-Token"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes an HTTP request to Dialyra API with robust error handling and structured parsing.
        Uses standard library urllib for zero external runtime dependencies.
        """
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = f"{self.base_url}{endpoint}"
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}
            if clean_params:
                url = f"{url}?{urllib.parse.urlencode(clean_params)}"

        headers = self._get_headers()
        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method.upper())

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_body = resp.read().decode("utf-8")
                if not resp_body:
                    return {}
                try:
                    return json.loads(resp_body)
                except json.JSONDecodeError:
                    return {"raw": resp_body}

        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8")
            err_data = {}
            try:
                err_data = json.loads(err_body)
            except Exception:
                err_data = {"error": err_body}

            error_msg = (
                err_data.get("error")
                or err_data.get("message")
                or f"Dialyra API error with status {exc.code}"
            )
            code = err_data.get("code")

            if exc.code in (401, 403):
                raise DialyraAuthError(error_msg, status_code=exc.code, response_data=err_data)
            elif exc.code == 400:
                raise DialyraValidationError(error_msg, status_code=exc.code, response_data=err_data)
            elif exc.code == 404:
                raise DialyraNotFoundError(error_msg, status_code=exc.code, response_data=err_data)
            elif exc.code == 402 or code == "INSUFFICIENT_CREDIT":
                raise DialyraBillingError(error_msg, status_code=exc.code, response_data=err_data)
            elif exc.code == 409 or code in ("TRUNK_NOT_READY", "NO_SIP_AVAILABLE"):
                raise DialyraTrunkNotReadyError(error_msg, status_code=exc.code, response_data=err_data)
            elif exc.code in (502, 503, 504):
                raise DialyraConnectionError(error_msg, status_code=exc.code, response_data=err_data)
            else:
                raise DialyraError(error_msg, status_code=exc.code, response_data=err_data)

        except urllib.error.URLError as exc:
            raise DialyraConnectionError(
                f"Failed to connect to Dialyra API at {self.base_url}: {exc.reason}",
                response_data={"reason": str(exc.reason)},
            )
        except Exception as exc:
            raise DialyraConnectionError(f"Unexpected error communicating with Dialyra: {str(exc)}")

    # ==========================================================================
    # Health & Diagnostics
    # ==========================================================================

    def check_health(self) -> Dict[str, Any]:
        """Checks Dialyra v2 health endpoint: GET /api/v2/health."""
        return self._request("GET", "/api/v2/health")

    # ==========================================================================
    # Runtime Call Origination (v3)
    # ==========================================================================

    def originate_call(
        self,
        phone: str,
        sip_trunk_id: Optional[int] = None,
        flow_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        campaign_flow_id: Optional[int] = None,
        webhook_variables: Optional[Dict[str, Any]] = None,
        customer: Optional[Customer] = None,
        user: Any = None,
    ) -> Dict[str, Any]:
        """
        Starts an outbound call via Dialyra v3 runtime API:
        POST /api/v3/runtime/calls/originate

        Validates payload per Dialyra v3 schema, executes call origination,
        and saves a canonical Call record in the Bizora database.
        """
        clean_phone = (phone or "").strip()
        if not clean_phone:
            raise DialyraValidationError("Phone number is required to originate a call.")

        if webhook_variables is not None:
            if not isinstance(webhook_variables, dict):
                raise DialyraValidationError("webhook_variables must be a JSON dictionary.")
            if len(webhook_variables) > 100:
                raise DialyraValidationError("webhook_variables cannot exceed 100 keys.")
            for k in webhook_variables.keys():
                if len(k) > 64 or not k.replace("_", "").isalnum():
                    raise DialyraValidationError(f"Invalid webhook_variable key '{k}': must match [A-Za-z0-9_].")

        payload: Dict[str, Any] = {"phone": clean_phone}
        if sip_trunk_id is not None:
            payload["sip_trunk_id"] = int(sip_trunk_id)
        if flow_id is not None:
            payload["flow_id"] = int(flow_id)
        if campaign_id is not None:
            payload["campaign_id"] = int(campaign_id)
        if campaign_flow_id is not None:
            payload["campaign_flow_id"] = int(campaign_flow_id)
        if webhook_variables:
            payload["webhook_variables"] = webhook_variables

        # Execute remote call to Dialyra
        response_data = self._request("POST", "/api/v3/runtime/calls/originate", data=payload)

        # Deterministically create or update canonical Call in Bizora
        call_log_uuid = response_data.get("call_log_uuid") or str(response_data.get("call_session_id", ""))
        caller_number = response_data.get("caller") or response_data.get("sip_endpoint") or "Dialyra Gateway"

        with transaction.atomic():
            connection = self.get_or_create_connection(self.business) if self.business else None
            call = Call.objects.create(
                business=self.business,
                customer=customer,
                integration_connection=connection,
                external_call_id=call_log_uuid or f"dialyra-{timezone.now().timestamp()}",
                direction="OUTGOING",
                caller_number=caller_number,
                receiver_number=clean_phone,
                status="INITIATED",
                started_at=timezone.now(),
                source_metadata={
                    "dialyra_response": response_data,
                    "sip_trunk_id": sip_trunk_id,
                    "flow_id": flow_id,
                    "initiated_by_user_id": getattr(user, "id", None),
                },
            )
            CallEvent.objects.create(
                call=call,
                event_type="INITIATED",
                event_at=timezone.now(),
                metadata={"source": "dialyra_v3_originate", "response": response_data},
            )

        return {
            "success": True,
            "call_id": call.pk,
            "external_call_id": call.external_call_id,
            "dialyra": response_data,
        }

    # ==========================================================================
    # Calls & Sessions (v2)
    # ==========================================================================

    def list_calls(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Lists call logs from Dialyra v2: GET /api/v2/calls."""
        return self._request("GET", "/api/v2/calls", params={"limit": limit, "offset": offset})

    def get_call(self, call_id: Union[int, str]) -> Dict[str, Any]:
        """Fetches a specific call log from Dialyra v2: GET /api/v2/calls/:id."""
        return self._request("GET", f"/api/v2/calls/{call_id}")

    # ==========================================================================
    # SIP Trunks (v3)
    # ==========================================================================

    def list_sip_trunks(self) -> Dict[str, Any]:
        """Lists SIP trunks: GET /api/v3/sip-trunks."""
        return self._request("GET", "/api/v3/sip-trunks")

    def get_sip_trunk(self, trunk_id: int) -> Dict[str, Any]:
        """Gets a SIP trunk: GET /api/v3/sip-trunks/:id."""
        return self._request("GET", f"/api/v3/sip-trunks/{trunk_id}")

    def get_sip_trunk_status(self, trunk_id: int) -> Dict[str, Any]:
        """Gets real-time Asterisk/PJSIP status: GET /api/v3/sip-trunks/:id/status."""
        return self._request("GET", f"/api/v3/sip-trunks/{trunk_id}/status")

    def create_sip_trunk(self, trunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a softphone-like SIP trunk via v3 schema:
        POST /api/v3/sip-trunks
        """
        required = ["name", "provider_name", "trunk_mode", "host", "max_concurrent_calls"]
        for field in required:
            if field not in trunk_data or trunk_data[field] is None:
                raise DialyraValidationError(f"Field '{field}' is required.")

        mode = trunk_data["trunk_mode"]
        if mode not in ("registration", "ip_auth"):
            raise DialyraValidationError("trunk_mode must be 'registration' or 'ip_auth'.")

        if mode == "registration" and (not trunk_data.get("username") or not trunk_data.get("password")):
            raise DialyraValidationError("username and password are required for registration trunk_mode.")

        return self._request("POST", "/api/v3/sip-trunks", data=trunk_data)

    def test_sip_trunk(self, trunk_id: int) -> Dict[str, Any]:
        """Tests SIP trunk connectivity and credentials: POST /api/v3/sip-trunks/:id/test."""
        return self._request("POST", f"/api/v3/sip-trunks/{trunk_id}/test")

    def reload_sip_trunk(self, trunk_id: int, enable_inbound: bool = False) -> Dict[str, Any]:
        """Syncs and reloads SIP trunk in Asterisk: POST /api/v3/sip-trunks/:id/reload."""
        return self._request("POST", f"/api/v3/sip-trunks/{trunk_id}/reload", data={"enable_inbound": enable_inbound})

    def get_realtime_health(self) -> Dict[str, Any]:
        """Checks Asterisk PJSIP realtime health: GET /api/v3/sip-trunks/realtime/health."""
        return self._request("GET", "/api/v3/sip-trunks/realtime/health")

    def get_drift(self) -> Dict[str, Any]:
        """Detects database vs Asterisk realtime row drift: GET /api/v3/sip-trunks/drift."""
        return self._request("GET", "/api/v3/sip-trunks/drift")

    # ==========================================================================
    # IVR Flows (v2)
    # ==========================================================================

    def list_flows(self) -> Dict[str, Any]:
        """Lists configured IVR call flows: GET /api/v2/flows."""
        return self._request("GET", "/api/v2/flows")

    # ==========================================================================
    # Webhook Event Processing
    # ==========================================================================

    def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes inbound Dialyra call webhooks and synchronizes
        state to Bizora Call, CallEvent, and CallTranscript models.
        """
        event_type = (event_data.get("event") or event_data.get("type") or "call.updated").upper()
        call_uuid = (
            event_data.get("call_log_uuid")
            or event_data.get("call_uuid")
            or event_data.get("call_session_id")
            or event_data.get("external_call_id")
        )

        if not call_uuid:
            return {"status": "ignored", "reason": "No call identifier in payload"}

        call = Call.objects.filter(external_call_id=str(call_uuid)).first()
        if not call:
            # Check by source_metadata
            call = Call.objects.filter(
                source_metadata__dialyra_response__call_log_uuid=str(call_uuid)
            ).first()

        now = timezone.now()

        with transaction.atomic():
            if call:
                # Update status
                new_status = event_data.get("status") or event_type
                if new_status:
                    call.status = str(new_status).upper()

                if "answered_at" in event_data and not call.answered_at:
                    call.answered_at = event_data["answered_at"]
                if "ended_at" in event_data:
                    call.ended_at = event_data["ended_at"]
                if "duration_seconds" in event_data:
                    call.duration_seconds = int(event_data["duration_seconds"])
                if "recording_url" in event_data:
                    call.recording_url = event_data["recording_url"]

                call.save()

                # Record CallEvent
                CallEvent.objects.create(
                    call=call,
                    event_type=event_type,
                    event_at=now,
                    metadata=event_data,
                )

                # Process transcript if provided
                if "transcript" in event_data or "summary" in event_data:
                    CallTranscript.objects.update_or_create(
                        call=call,
                        defaults={
                            "transcript": event_data.get("transcript"),
                            "summary": event_data.get("summary"),
                            "language": event_data.get("language", "en"),
                            "provider": "dialyra",
                            "confidence": event_data.get("confidence", 1.0),
                        },
                    )

                return {"status": "processed", "call_id": call.pk, "call_status": call.status}
            else:
                logger.info(f"Dialyra webhook received for unknown call {call_uuid}")
                return {"status": "unmatched_call", "call_uuid": str(call_uuid)}
