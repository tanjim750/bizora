"""Bizora persistence boundary for confirmed Steadfast consignments."""
from datetime import timedelta
from urllib.parse import urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import APIException, NotFound, ValidationError

from app.configuration.integrations import CredentialUnavailable, resolve_credentials
from app.models import IntegrationConnection, Order, Shipment, ShipmentEvent
from app.observability.models import OperationAttempt

from .client import SteadfastClient, SteadfastError
from .services import OrderRequest, SteadfastService


class SubmissionPending(APIException):
    status_code = 409
    default_detail = 'Steadfast submission outcome is uncertain. Check the invoice with Steadfast before retrying.'


def service_for(connection, *, operation='read', transport=None, sleep=None):
    if connection.integration_source.key.lower() != 'steadfast' or connection.is_mock or connection.status == 'DISABLED':
        raise ValidationError('An active live Steadfast connection is required.')
    config = connection.config if isinstance(connection.config, dict) else {}
    required_scope = 'CREATE_SHIPMENTS' if operation == 'write' else 'READ_SHIPMENTS'
    if 'scopes' in config and required_scope not in config['scopes']:
        raise ValidationError('Steadfast shipment access is disabled by integration configuration.')
    credentials = resolve_credentials(connection)
    if not credentials.get('api_key') or not credentials.get('secret_key'):
        raise CredentialUnavailable('Steadfast API key and secret key are required.')
    provider_settings = config.get('provider_settings') or {}
    base_url = provider_settings.get('base_url', SteadfastClient.DEFAULT_BASE_URL)
    try:
        parsed = urlsplit(base_url) if isinstance(base_url, str) else None
        official = (parsed is not None and parsed.scheme == 'https' and parsed.hostname == 'portal.packzy.com'
                    and parsed.port in (None, 443) and not parsed.username and not parsed.password
                    and not parsed.query and not parsed.fragment and parsed.path.rstrip('/') == '/api/v1')
    except ValueError:
        official = False
    if not official:
        raise ValidationError('Steadfast provider base URL must be the official HTTPS API v1 endpoint.')
    options = {'base_url': base_url}
    if transport is not None:
        options['transport'] = transport
    if sleep is not None:
        options['sleep'] = sleep
    return SteadfastService(SteadfastClient(credentials['api_key'], credentials['secret_key'], **options))


def connection_for(business_id, connection_id):
    connection = IntegrationConnection.objects.select_related('integration_source').filter(
        pk=connection_id, business_id=business_id).first()
    if connection is None:
        raise NotFound('Integration connection not found.')
    return connection


def status_name(provider_status):
    value = provider_status.strip().lower().replace('-', '_').replace(' ', '_')
    if value == 'delivered':
        return 'DELIVERED'
    if value in {'cancelled', 'canceled'}:
        return 'CANCELLED'
    if value == 'returned':
        return 'RETURNED'
    if value in {'returning', 'return_rider_assigned', 'cancelled_return_rider_assigned'}:
        return 'RETURNING'
    if value in {'failed', 'delivery_failed'}:
        return 'FAILED'
    if value in {'picked_up', 'pickup_done'}:
        return 'PICKED_UP'
    if value == 'out_for_delivery':
        return 'OUT_FOR_DELIVERY'
    if value == 'in_transit':
        return 'IN_TRANSIT'
    return 'SUBMITTED' if value in {'', 'pending', 'created', 'submitted', 'in_review'} else 'PENDING'


def submit_order(connection, order_id, details, *, service=None):
    """Record the attempt before contacting Steadfast, then save a confirmed consignment."""
    if isinstance(order_id, bool) or not isinstance(order_id, int) or order_id <= 0:
        raise ValidationError({'order_id': 'A positive integer is required.'})
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(pk=order_id, business_id=connection.business_id).first()
        if order is None:
            raise NotFound('Order not found.')
        existing = Shipment.objects.filter(order=order, integration_connection=connection).first()
        if existing:
            return existing, False
        if order.currency != 'BDT':
            raise ValidationError('Steadfast shipment COD must be in BDT.')
        invoice = f'BIZORA-{order.pk}'
        payload = {'invoice': invoice, 'recipient_name': details.get('recipient_name'),
                   'recipient_phone': details.get('recipient_phone'), 'recipient_address': details.get('recipient_address'),
                   'cod_amount': details.get('cod_amount', str(order.total_amount))}
        payload.update({key: details[key] for key in ('note', 'alternative_phone', 'recipient_email', 'item_description', 'total_lot', 'delivery_type') if key in details})
        client = service or service_for(connection, operation='write')
        validator = OrderRequest(data=payload)
        validator.is_valid(raise_exception=True)
        pending = OperationAttempt.objects.filter(connection=connection, action='CREATE_SHIPMENT',
                                                  target_id=order.pk, status='RUNNING').first()
        if pending:
            if (details.get('confirmed_absent') is not True or
                    (pending.result.get('outcome') != 'UNKNOWN' and
                     timezone.now() - pending.created_at < timedelta(seconds=60))):
                raise SubmissionPending(f'Check invoice {invoice} with Steadfast before retrying.')
            pending.status = 'FAILED'
            pending.completed_at = timezone.now()
            pending.result = {'invoice': invoice, 'resolution': 'confirmed_absent_by_manager'}
            pending.save(update_fields=['status', 'completed_at', 'result'])
        attempt = OperationAttempt.objects.create(
            business_id=connection.business_id, connection=connection,
            key=f'steadfast:create:{order.pk}:{uuid4().hex}', action='CREATE_SHIPMENT',
            target_id=order.pk, status='RUNNING', result={'invoice': invoice, 'outcome': 'IN_FLIGHT'})
    try:
        result = client.create_order(payload)
    except SteadfastError:
        attempt.result = {'invoice': invoice, 'outcome': 'UNKNOWN'}
        attempt.save(update_fields=['result'])
        raise
    consignment = result['consignment']
    with transaction.atomic():
        shipment = Shipment.objects.create(
            business_id=connection.business_id, order=order, customer=order.customer,
            integration_connection=connection, external_shipment_id=str(consignment['consignment_id']),
            tracking_code=consignment['tracking_code'], provider='Steadfast',
            status=status_name(consignment.get('status', '')), cod_amount=payload['cod_amount'],
            recipient_name=payload['recipient_name'], recipient_phone=payload['recipient_phone'],
            delivery_address=payload['recipient_address'], submitted_at=timezone.now(),
            source_metadata={'invoice': invoice, 'tracking_link': consignment.get('tracking_link')},
        )
        ShipmentEvent.objects.create(shipment=shipment, event_type='SUBMITTED', status=shipment.status,
                                     description='Submitted to Steadfast', occurred_at=shipment.submitted_at)
        attempt.status = 'SUCCEEDED'
        attempt.completed_at = timezone.now()
        attempt.result = {'invoice': invoice, 'shipment_id': shipment.pk}
        attempt.save(update_fields=['status', 'completed_at', 'result'])
    return shipment, True


@transaction.atomic
def apply_status(shipment, provider_status, *, event_type='STATUS_UPDATED', metadata=None,
                 occurred_at=None, delivery_charge=None):
    shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
    occurred_at = occurred_at or timezone.now()
    if timezone.is_naive(occurred_at):
        # Steadfast sends Bangladesh local timestamps without an offset.
        occurred_at = timezone.make_aware(occurred_at, ZoneInfo('Asia/Dhaka'))
    source_metadata = shipment.source_metadata or {}
    last_status_at = parse_datetime(source_metadata['provider_status_at']) if source_metadata.get('provider_status_at') else None
    if last_status_at and occurred_at <= last_status_at:
        return shipment, False
    new_status = status_name(provider_status)
    status_changed = not (shipment.status == new_status or (new_status == 'PENDING' and shipment.status != 'PENDING')
                          or shipment.status in {'DELIVERED', 'RETURNED', 'CANCELLED'})
    charge_changed = delivery_charge is not None and shipment.delivery_charge != delivery_charge
    source_metadata['provider_status_at'] = occurred_at.isoformat()
    shipment.source_metadata = source_metadata
    update_fields = ['source_metadata', 'updated_at']
    if status_changed:
        shipment.status = new_status
        if new_status == 'PICKED_UP' and shipment.picked_up_at is None:
            shipment.picked_up_at = occurred_at
        if new_status == 'DELIVERED' and shipment.delivered_at is None:
            shipment.delivered_at = occurred_at
        if new_status == 'RETURNED' and shipment.returned_at is None:
            shipment.returned_at = occurred_at
        update_fields += ['status', 'picked_up_at', 'delivered_at', 'returned_at']
    if charge_changed:
        shipment.delivery_charge = delivery_charge
        update_fields.append('delivery_charge')
    shipment.save(update_fields=update_fields)
    if status_changed or charge_changed:
        event_metadata = dict(metadata or {})
        if charge_changed:
            event_metadata['delivery_charge'] = str(delivery_charge)
        ShipmentEvent.objects.create(shipment=shipment, event_type=event_type, status=shipment.status,
                                     description=provider_status, occurred_at=occurred_at, metadata=event_metadata)
    return shipment, status_changed or charge_changed
