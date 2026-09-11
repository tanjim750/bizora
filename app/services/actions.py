"""
Action Lifecycle and Approval Service.
Enforces the mandatory Human-in-the-Loop boundary:
No AI action can execute without explicit user approval and audit trail.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from app.events.dispatcher import dispatch
from app.models import AiAction


class ActionApprovedEvent:
    def __init__(self, action_id, business_id, approved_by_id):
        self.type = "ai.action.approved"
        self.payload = {
            "action_id": action_id,
            "business_id": business_id,
            "approved_by_id": approved_by_id,
        }


def approve_action(action: AiAction, user, approval_note: str) -> AiAction:
    """
    Approves an action with full user identity audit trail (SEC-004)
    and dispatches a deferred on_commit audit event (COR-001).
    """
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication required to approve actions.")

    if action.status not in ("SUGGESTED", "REJECTED"):
        raise ValidationError(
            f"Action cannot be approved from state '{action.status}'."
        )

    now = timezone.now()
    action.status = "APPROVED"
    action.approved_by = user
    action.approved_at = now
    action.approval_note = approval_note
    action.save()

    # Dispatch audit event
    dispatch(ActionApprovedEvent(action.id, action.business_id, user.id))
    return action


def execute_action(action: AiAction, executor_fn=None) -> AiAction:
    """
    Executes an approved action.
    Fails fast if unapproved (SEC-005).
    Captures integration errors and transitions status to FAILED (COR-011).
    Wrapped in transaction.atomic to prevent stuck EXECUTING state on partial failure.
    """
    if not action.approved_at or action.status != "APPROVED":
        raise ValidationError(
            "AiAction cannot execute without approval (approved_at must be set)."
        )

    with transaction.atomic():
        action.status = "EXECUTING"
        action.save()

        now = timezone.now()
        action.executed_at = now

        try:
            if executor_fn:
                result = executor_fn(action.action_payload)
                action.execution_result = result
            else:
                action.execution_result = {
                    "status": "success",
                    "message": "Simulated execution completed successfully",
                }

            if isinstance(action.execution_result, dict) and (
                "error" in action.execution_result or "errors" in action.execution_result
            ):
                action.status = "FAILED"
            else:
                action.status = "EXECUTED"
        except Exception as exc:  # noqa: BLE001 - intentional safety guardrail for arbitrary action execution
            action.execution_result = {"error": f"Execution failed: {exc!s}"}
            action.status = "FAILED"

        action.save()
    return action
