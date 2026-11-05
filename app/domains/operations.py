"""Operations compose authoritative records; they never calculate BI or invent AI outputs."""
from django.db import transaction
from django.utils import timezone
from app import models as m
from .common import require, related, authorize, create, audit


@transaction.atomic
def assign(business, actor, conversation_id, assignee_type, assignee_id=None, reason=''):
    authorize(actor, business, write=True)
    m.Business.objects.select_for_update().get(pk=business.pk)
    obj = related(m.Conversation, conversation_id, business)
    require(obj.status in ('OPEN', 'PENDING'), 'INVALID_TRANSITION', 'Only active conversations can be assigned.')
    require(assignee_type in ('AGENT', 'TEAM', 'AI', 'UNASSIGNED'), 'INVALID_ASSIGNEE', 'Unknown assignee type.')
    if assignee_type == 'AGENT':
        require(m.BusinessMembership.objects.filter(business=business, user_id=assignee_id, user__is_active=True,
                is_active=True, role__in=['OPERATOR', 'MANAGER', 'OWNER']).exists(), 'INVALID_ASSIGNEE', 'Agent must be an active support-capable business member.')
    elif assignee_type == 'TEAM':
        related(m.SupportTeam, assignee_id, business)
    else:
        require(assignee_id is None, 'INVALID_ASSIGNEE', 'AI/unassigned must not have an actor ID.')
    old = m.ConversationAssignment.objects.filter(conversation=obj, status='ACTIVE').first()
    if old and old.assignee_type == assignee_type and old.assignee_id == assignee_id:
        return old
    if not old and assignee_type == 'UNASSIGNED':
        return None
    if old:
        old.status, old.unassigned_at = 'RELEASED', timezone.now()
        old.save(update_fields=['status', 'unassigned_at'])
    new = None
    if assignee_type != 'UNASSIGNED':
        new = create(m.ConversationAssignment, conversation=obj, assignee_type=assignee_type,
                     assignee_id=assignee_id, assigned_by_type='AGENT', assigned_by_id=actor.pk,
                     assigned_at=timezone.now(), metadata={'reason': reason})
    obj.ai_handover_state = 'AI' if assignee_type == 'AI' else None if assignee_type == 'UNASSIGNED' else 'HUMAN'
    obj.updated_at = timezone.now()
    obj.save(update_fields=['ai_handover_state', 'updated_at'])
    m.ConversationEvent.objects.create(conversation=obj, actor=actor, event_type='ASSIGNMENT',
        from_state=old.assignee_type if old else 'UNASSIGNED', to_state=assignee_type, reason=reason,
        context={'assignment_id': new.pk if new else None})
    audit(business, actor, 'ASSIGNED', obj, {'assignment_id': new.pk if new else None, 'reason': reason})
    return new


@transaction.atomic
def handover(business, actor, conversation_id, target, assignee_id=None, reason='', summary=''):
    authorize(actor, business, write=True)
    m.Business.objects.select_for_update().get(pk=business.pk)
    obj = related(m.Conversation, conversation_id, business)
    require(target in ('HUMAN', 'AI') and reason.strip(), 'INVALID_HANDOVER', 'Target and reason are required.')
    require(target != 'AI' or assignee_id is None, 'INVALID_ASSIGNEE', 'AI must not have a user ID.')
    if obj.ai_handover_state == target:
        active = m.ConversationAssignment.objects.filter(conversation=obj, status='ACTIVE').first()
        require(active and active.assignee_type == ('AI' if target == 'AI' else 'AGENT') and active.assignee_id == assignee_id,
                'HANDOVER_CONFLICT', 'Repeated handover has different ownership; use reassignment.')
        return obj
    previous = obj.ai_handover_state
    assign(business, actor, obj.pk, 'AI' if target == 'AI' else 'AGENT', assignee_id, reason)
    obj.ai_handover_state, obj.updated_at = target, timezone.now()
    obj.save(update_fields=['ai_handover_state', 'updated_at'])
    m.ConversationEvent.objects.create(conversation=obj, actor=actor, event_type='HANDOVER',
        from_state=previous, to_state=target, reason=reason,
        context={'summary': summary, 'summary_source': 'HUMAN_PROVIDED',
                 'customer_id': obj.customer_id, 'customer_notification': 'UNAVAILABLE_PROVIDER_TRANSPORT'})
    audit(business, actor, 'HANDOVER', obj, {'target': target, 'reason': reason})
    return obj


@transaction.atomic
def review_action(business, actor, action_id, decision, reason):
    authorize(actor, business, manager=True)
    m.Business.objects.select_for_update().get(pk=business.pk)
    obj = related(m.AiAction, action_id, business)
    require(obj.ai_recommendation.business_id == business.pk, 'INVALID_RELATION', 'Recommendation business differs.')
    require(decision in ('APPROVED', 'REJECTED') and reason.strip(), 'INVALID_REVIEW', 'Decision and reason required.')
    if decision == 'APPROVED':
        from .contracts import recommendation_supported
        require(recommendation_supported(obj.ai_recommendation, business), 'EVIDENCE_REQUIRED', 'Approval requires current, tenant-safe verified evidence and a valid recommendation.')
    require(obj.status in ('SUGGESTED', decision), 'INVALID_TRANSITION', 'Action already reviewed/executed.')
    if obj.status == decision:
        return obj
    obj.status, obj.approval_note, obj.updated_at = decision, reason, timezone.now()
    obj.approved_at = timezone.now() if decision == 'APPROVED' else None
    obj.save(update_fields=['status', 'approval_note', 'approved_at', 'updated_at'])
    audit(business, actor, 'ACTION_' + decision, obj, {'reason': reason})
    return obj


def unavailable(owner):
    return {'status': 'UNAVAILABLE', 'owner': owner, 'reason': 'No authoritative provider contract is registered.'}


@transaction.atomic
def mark_read(business, actor, message_id):
    authorize(actor, business, write=True)
    m.Business.objects.select_for_update().get(pk=business.pk)
    obj = related(m.Message, message_id, business)
    if obj.read_status != 'READ':
        obj.read_status, obj.read_at, obj.updated_at = 'READ', timezone.now(), timezone.now()
        obj.save(update_fields=['read_status', 'read_at', 'updated_at'])
        audit(business, actor, 'MESSAGE_READ', obj)
    return obj


@transaction.atomic
def set_priority(business, actor, conversation_id, priority, reason):
    authorize(actor, business, write=True)
    m.Business.objects.select_for_update().get(pk=business.pk)
    obj = related(m.Conversation, conversation_id, business)
    require(priority in ('LOW', 'NORMAL', 'HIGH', 'URGENT') and isinstance(reason, str) and reason.strip(), 'INVALID_PRIORITY', 'Priority and reason are required.')
    if obj.priority != priority:
        previous = obj.priority
        obj.priority, obj.updated_at = priority, timezone.now()
        obj.save(update_fields=['priority', 'updated_at'])
        m.ConversationEvent.objects.create(conversation=obj, actor=actor, event_type='PRIORITY', from_state=previous, to_state=priority, reason=reason)
        audit(business, actor, 'PRIORITY_CHANGED', obj, {'from': previous, 'to': priority, 'reason': reason})
    return obj


@transaction.atomic
def schedule_callback(business, actor, callback_id, scheduled_at):
    authorize(actor, business, write=True)
    m.Business.objects.select_for_update().get(pk=business.pk)
    obj = related(m.CallbackRequest, callback_id, business)
    require(obj.status == 'PENDING' and timezone.is_aware(scheduled_at) and scheduled_at > timezone.now(),
            'INVALID_CALLBACK', 'Only pending requests can be scheduled at a future offset-aware time.')
    if obj.scheduled_at != scheduled_at:
        obj.scheduled_at = scheduled_at
        obj.save(update_fields=['scheduled_at'])
        audit(business, actor, 'CALLBACK_SCHEDULED', obj, {'scheduled_at': scheduled_at.isoformat()})
    return obj
