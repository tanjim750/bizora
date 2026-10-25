from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from app.models import FailedRecord, IntegrationError
from .access import require_access
from .policies import safe_details
from .services import audit, scoped_connection


@transaction.atomic
def transition_record(business_id, target_type, target_id, status, note, actor):
    require_access(actor, business_id, manage=True)
    model = {'error': IntegrationError, 'failed_record': FailedRecord}.get(target_type)
    if model is None:
        raise ValidationError('Unsupported lifecycle target.')
    try:
        row = model.objects.get(pk=target_id, business_id=business_id)
    except model.DoesNotExist as exc:
        raise ValidationError('Lifecycle target does not belong to this business.') from exc
    connection = scoped_connection(business_id, row.connection_id, lock=True)
    row.refresh_from_db()
    allowed = ({'ACTIVE': {'ACKNOWLEDGED', 'RESOLVED', 'IGNORED'},
                'ACKNOWLEDGED': {'RESOLVED', 'IGNORED'}, 'RESOLVED': {'ACTIVE'}, 'IGNORED': {'ACTIVE'}}
               if target_type == 'error' else
               {'OPEN': {'REVIEWING', 'RESOLVED', 'IGNORED'}, 'REVIEWING': {'OPEN', 'RESOLVED', 'IGNORED'},
                'RESOLVED': {'OPEN'}, 'IGNORED': {'OPEN', 'REVIEWING'}})
    if status not in allowed.get(row.status, set()):
        raise ValidationError('Invalid lifecycle transition.')
    if status in {'RESOLVED', 'IGNORED'} and not note.strip():
        raise ValidationError('Resolution/ignore requires a review note.')
    before = row.status
    row.status = status
    row.resolved_at = timezone.now() if status == 'RESOLVED' else None
    if target_type == 'failed_record':
        row.resolution = safe_details(note)
        row.resolution_method = 'MANUAL' if status == 'RESOLVED' else ''
    row.save()
    audit(connection, target_type, row.pk, 'TRANSITION', before, status, actor=actor, note=note)
    return row
