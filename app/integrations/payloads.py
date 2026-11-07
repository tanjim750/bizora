"""Integration-owned immutable source capture, never a public diagnostic serializer."""
import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from app.models import IntegrationConnection, IntegrationPayload


@transaction.atomic
def capture_payload(connection_id, key, body, *, signature_verified=False, received_at=None, source_at=None):
    if not isinstance(key, str) or not 0 < len(key) <= 200 or not isinstance(body, dict):
        raise ValidationError('A bounded capture key and JSON object are required.')
    if not isinstance(signature_verified, bool):
        raise ValidationError('Signature verification must be supplied by the integration owner.')
    try:
        encoded = json.dumps(body, sort_keys=True, allow_nan=False).encode()
    except (ValueError, TypeError) as exc:
        raise ValidationError('Source payload must be JSON.') from exc
    if len(encoded) > 262144:
        raise ValidationError('Source payload exceeds the prototype capture limit of 256 KiB.')
    fingerprint = hashlib.sha256(encoded).hexdigest()
    from app.observability.services import timestamp
    received_at = timestamp(received_at or timezone.now(), 'received_at')
    source_at = timestamp(source_at, 'source_at') if source_at is not None else None
    try:
        connection = IntegrationConnection.objects.select_for_update().get(pk=connection_id)
    except IntegrationConnection.DoesNotExist as exc:
        raise ValidationError('Unknown integration connection.') from exc
    prior = IntegrationPayload.objects.filter(connection=connection, key=key).first()
    if prior:
        if prior.digest != fingerprint or prior.signature_verified != signature_verified or prior.source_at != source_at:
            raise ValidationError('Captured content and its validation evidence cannot be rebound.')
        return prior
    return IntegrationPayload.objects.create(connection=connection, key=key, body=body, digest=fingerprint,
        signature_verified=signature_verified, received_at=received_at, source_at=source_at)
