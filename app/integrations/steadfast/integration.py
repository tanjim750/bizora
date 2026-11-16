"""Bizora persistence boundary for confirmed Steadfast consignments."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError
from urllib.parse import urlsplit

from app.configuration.integrations import CredentialUnavailable, resolve_credentials
from app.models import IntegrationConnection, Order, Shipment, ShipmentEvent

from .client import SteadfastClient
from .services import SteadfastService


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


@transaction.atomic
def submit_order(connection, order_id, details, *, service=None):
    """Submit one Bizora order and save the confirmed consignment once."""
    if isinstance(order_id, bool) or not isinstance(order_id, int) or order_id <= 0:
        raise ValidationError({'order_id': 'A positive integer is required.'})
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
    result = (service or service_for(connection, operation='write')).create_order(payload)
    consignment = result['consignment']
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
    return shipment, True


@transaction.atomic
def apply_status(shipment, provider_status, *, event_type='STATUS_UPDATED', metadata=None):
    shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
    new_status = status_name(provider_status)
    if (shipment.status == new_status or (new_status == 'PENDING' and shipment.status != 'PENDING')
            or shipment.status in {'DELIVERED', 'RETURNED', 'CANCELLED'}):
        return shipment, False
    now = timezone.now()
    shipment.status = new_status
    if new_status == 'PICKED_UP' and shipment.picked_up_at is None:
        shipment.picked_up_at = now
    if new_status == 'DELIVERED' and shipment.delivered_at is None:
        shipment.delivered_at = now
    if new_status == 'RETURNED' and shipment.returned_at is None:
        shipment.returned_at = now
    shipment.save(update_fields=['status', 'picked_up_at', 'delivered_at', 'returned_at', 'updated_at'])
    ShipmentEvent.objects.create(shipment=shipment, event_type=event_type, status=new_status,
                                 description=provider_status, occurred_at=now, metadata=metadata or {})
    return shipment, True
