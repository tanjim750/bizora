from decimal import Decimal, InvalidOperation
import re
import json
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.utils import timezone
from app import models as m


class DomainError(ValueError):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)


def require(condition, code, message):
    if not condition:
        raise DomainError(code, message)


def money(value):
    try:
        result = Decimal(str(value))
        require(result.is_finite() and result >= 0 and result == result.quantize(Decimal('.01')),
                'INVALID_MONEY', 'Money must be finite, nonnegative and have at most two decimal places.')
        require(result < Decimal('10000000000000000'), 'INVALID_MONEY', 'Amount exceeds storage precision.')
        return result.quantize(Decimal('.01'))
    except (InvalidOperation, ValueError, TypeError):
        raise DomainError('INVALID_MONEY', 'Invalid monetary amount.')


def normalize_contact(kind, value):
    kind = str(kind).upper()
    require(isinstance(value, str) and value.strip(), 'INVALID_CONTACT', 'A contact value is required.')
    value = value.strip()
    if kind == 'EMAIL':
        value = value.casefold()
        try:
            validate_email(value)
        except ValidationError:
            raise DomainError('INVALID_CONTACT', 'Invalid email address.')
    elif kind in ('PHONE', 'WHATSAPP_PHONE'):
        value = re.sub(r'[\s()\-]', '', value)
        if value.startswith('00'):
            value = '+' + value[2:]
        if re.fullmatch(r'01[3-9]\d{8}', value):
            value = '+88' + value
        require(bool(re.fullmatch(r'\+[1-9]\d{7,14}', value)), 'INVALID_CONTACT',
                'Use an international number; Bangladesh local mobile numbers are supported.')
    else:
        require(kind in ('PSID', 'TELEGRAM_USER_ID', 'INSTAGRAM_USER_ID', 'CLIENT_ID', 'EXTERNAL_CUSTOMER_ID', 'EXTERNAL_PRODUCT_ID',
                         'EXTERNAL_ORDER_ID', 'EXTERNAL_PAYMENT_ID', 'EXTERNAL_CAMPAIGN_ID',
                         'EXTERNAL_SESSION_ID', 'EXTERNAL_CONVERSATION_ID', 'EXTERNAL_CALL_ID',
                         'EXTERNAL_SHIPMENT_ID', 'SKU'), 'INVALID_CONTACT', 'Unsupported identity type.')
    return value


def stamp(data, model):
    names = {f.name for f in model._meta.fields}
    now = timezone.now()
    return {**({'created_at': now} if 'created_at' in names else {}),
            **({'updated_at': now} if 'updated_at' in names else {}), **data}


def create(model, **data):
    obj = model(**stamp(data, model))
    validate(obj)
    obj.save()
    return obj


def validate(obj):
    model = type(obj)
    # Existing nullable fields are not blank=True. Missing optional data is legitimate.
    excluded = [f.name for f in model._meta.fields if (f.null and getattr(obj, f.attname) is None) or isinstance(f, models.JSONField)]
    try:
        for f in model._meta.fields:
            if isinstance(f, models.JSONField):
                json.dumps(getattr(obj, f.name), allow_nan=False)
    except (TypeError, ValueError):
        raise DomainError('INVALID_DATA', 'Metadata must be valid JSON.')
    try:
        obj.full_clean(exclude=excluded)
    except ValidationError as exc:
        raise DomainError('INVALID_DATA', str(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages))
    return obj


def business_id(obj):
    if isinstance(obj, m.Business):
        return obj.pk
    if hasattr(obj, 'business_id'):
        return obj.business_id
    # Deliberately explicit: do not accidentally accept arbitrary polymorphic records.
    for attr in ('product', 'customer', 'order', 'payment', 'conversation', 'message',
                 'campaign', 'ad_set', 'shipment', 'call', 'session', 'canonical_identity',
                 'ai_recommendation', 'business_fact', 'business_issue', 'metric_snapshot',
                 'relationship', 'source_node', 'knowledge_chunk', 'knowledge_document',
                 'knowledge_source', 'metric', 'ai_conversation'):
        field = next((f for f in obj._meta.fields if f.name == attr and isinstance(f, models.ForeignKey)), None)
        if field and getattr(obj, field.attname):
            return business_id(getattr(obj, attr))
    raise DomainError('INVALID_RELATION', 'Cannot establish business ownership.')


def related(model, pk, business):
    require(isinstance(pk, int) and not isinstance(pk, bool) and pk > 0, 'INVALID_RELATION', 'Related identifier must be a positive integer.')
    try:
        obj = model.objects.get(pk=pk)
    except (model.DoesNotExist, ValueError, TypeError):
        raise DomainError('INVALID_RELATION', 'Related object is unavailable.')
    ensure_owned(obj, business)
    return obj


def audit(business, actor, action, obj, evidence=None):
    return m.DomainAudit.objects.create(business=business, actor=actor, action=action,
                                       entity_type=obj.__class__.__name__, entity_id=obj.pk,
                                       evidence=evidence or {})


def authorize(user, business, write=False, manager=False):
    require(user is not None and user.is_authenticated and user.is_active,
            'FORBIDDEN', 'Authentication is required.')
    membership = m.BusinessMembership.objects.filter(business=business, user=user, is_active=True).first()
    require(membership is not None, 'FORBIDDEN', 'Business access is denied.')
    allowed = ('OWNER', 'MANAGER') if manager else ('OWNER', 'MANAGER', 'OPERATOR') if write else ('OWNER', 'MANAGER', 'OPERATOR', 'VIEWER')
    require(membership.role in allowed, 'FORBIDDEN', 'Your business role cannot perform this operation.')
    return membership


def ensure_owned(obj, business, seen=None):
    """Reject legacy-corrupt parent graphs too, not just the first business column."""
    seen = set() if seen is None else seen
    key = (obj._meta.label_lower, obj.pk)
    if key in seen:
        return obj
    seen.add(key)
    require(business_id(obj) == business.pk, 'INVALID_RELATION', 'Related object is unavailable.')
    if isinstance(obj, m.Business):
        return obj
    from .identity import ENTITY_MODELS
    for prefix in ('', 'source_', 'target_', 'subject_'):
        kind = getattr(obj, prefix + 'entity_type', None)
        entity_pk = getattr(obj, prefix + 'entity_id', None)
        if kind and entity_pk and str(kind).upper() in ENTITY_MODELS:
            model = ENTITY_MODELS[str(kind).upper()]
            target = model.objects.filter(pk=entity_pk).first()
            require(target is not None, 'INVALID_RELATION', 'Referenced entity is unavailable.')
            ensure_owned(target, business, seen)
    for field in obj._meta.fields:
        if (isinstance(field, models.ForeignKey) and field.related_model._meta.app_label == 'app'
                and field.related_model is not m.IntegrationSource and getattr(obj, field.attname)):
            ensure_owned(getattr(obj, field.name), business, seen)
    return obj


def external_identifier(value):
    require(isinstance(value,(str,int)) and not isinstance(value,bool) and 0<len(str(value).strip())<=255,
        'INVALID_IDENTIFIER','External identifiers must be nonempty text or integer values, max 255 characters.')
    return str(value).strip()
