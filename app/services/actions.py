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
from app.services.authorization import require_business_access


class ActionApprovedEvent:
    def __init__(self, action_id, business_id, approved_by_id):
        self.type = "ai.action.approved"
        self.payload = {
            "action_id": action_id,
            "business_id": business_id,
            "approved_by_id": approved_by_id,
        }


def _record_action_audit(action, event_name, user=None, result=None):
    from app.models import AiConversation, AiMessage
    now = timezone.now()
    conversation = AiConversation.objects.create(
        business_id=action.business_id, conversation_type="ACTION_AUDIT",
        status="COMPLETED", title=event_name, started_at=now, ended_at=now,
    )
    AiMessage.objects.create(
        ai_conversation=conversation, role="SYSTEM", content=event_name,
        model="lifecycle", context_reference={
            "action_id": action.id, "user_id": getattr(user, "id", None), "result": result or {}
        }, response_metadata={"event": event_name},
    )


def approve_action(action: AiAction, user, approval_note: str) -> AiAction:
    """
    Approves an action with full user identity audit trail (SEC-004)
    and dispatches a deferred on_commit audit event (COR-001).
    """
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication required to approve actions.")

    with transaction.atomic():
        action = AiAction.objects.select_for_update().get(pk=action.pk)
        require_business_access(user, action.business, roles={"OWNER", "ADMIN", "OPERATOR"})
        if action.status == "APPROVED" and action.approved_by_id == user.id:
            return action
        if action.status not in ("SUGGESTED", "REJECTED"):
            raise ValidationError(f"Action cannot be approved from state '{action.status}'.")
        now = timezone.now()
        action.status = "APPROVED"
        action.approved_by = user
        action.approved_at = now
        action.approval_note = approval_note
        action.save()

    # Dispatch audit event
    dispatch(ActionApprovedEvent(action.id, action.business_id, user.id))
    _record_action_audit(action, "ACTION_APPROVED", user, {"approval_note": approval_note})
    return action


def reject_action(action: AiAction, user, note: str) -> AiAction:
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication required to reject actions.")
    with transaction.atomic():
        locked = AiAction.objects.select_for_update().get(pk=action.pk)
        require_business_access(user, locked.business, roles={"OWNER", "ADMIN", "OPERATOR"})
        if locked.status == "REJECTED" and locked.rejected_by_id == user.id:
            return locked
        if locked.status not in ("SUGGESTED", "APPROVED"):
            raise ValidationError(f"Action cannot be rejected from state '{locked.status}'.")
        locked.status = "REJECTED"
        locked.rejected_by = user
        locked.rejected_at = timezone.now()
        locked.approval_note = note
        locked.save(update_fields=["status", "rejected_by", "rejected_at", "approval_note", "updated_at"])
        _record_action_audit(locked, "ACTION_REJECTED", user, {"approval_note": note})
        return locked


def execute_action(action: AiAction, executor_fn=None) -> AiAction:
    """
    Executes an approved action.
    Fails fast if unapproved (SEC-005).
    Captures integration errors and transitions status to FAILED (COR-011).
    Claims execution before calling a provider, so a later database failure cannot
    make an external action eligible for automatic retry.
    """
    enclosing_transaction = transaction.get_connection().in_atomic_block
    with transaction.atomic():
        action = AiAction.objects.select_for_update().get(pk=action.pk)
        if not action.approved_at or action.status != "APPROVED":
            if action.status == "EXECUTED":
                return action
            raise ValidationError("AiAction cannot execute without approval (approved_at must be set).")
        if not action.is_simulated and executor_fn is None:
            raise ValidationError("A provider executor is required for non-simulated actions.")
        if not action.is_simulated and enclosing_transaction:
            raise ValidationError("External actions must execute outside an enclosing database transaction.")
        action.status = "EXECUTING"
        action.save(update_fields=["status", "updated_at"])

    try:
        # shortcut: interrupted calls remain EXECUTING for manual reconciliation; automatic retries need provider idempotency.
        if executor_fn:
            result = executor_fn(action.action_payload)
        else:
            result = {
                "status": "success",
                "message": "Simulated execution completed successfully",
            }
        failed = (
            not isinstance(result, dict)
            or result.get("status") in {"failed", "error"}
            or result.get("success") is False
            or "error" in result
            or "errors" in result
        )
    except Exception as exc:  # noqa: BLE001 - provider errors are recorded as failed actions
        result = {"error": f"Execution failed: {exc!s}"}
        failed = True

    with transaction.atomic():
        action = AiAction.objects.select_for_update().get(pk=action.pk)
        if action.status != "EXECUTING":
            raise ValidationError("Action execution state changed during the provider call.")
        action.executed_at = timezone.now()
        action.execution_result = result
        action.status = "FAILED" if failed else "EXECUTED"
        action.save()

    _record_action_audit(action, f"ACTION_{action.status}", result=action.execution_result)
    return action
