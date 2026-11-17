"""Authenticated business operations and signed courier webhook."""
from decimal import Decimal

from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from app.configuration.integrations import CredentialUnavailable, resolve_credentials
from app.models import Shipment
from app.observability.access import require_access

from .client import SteadfastError
from .integration import apply_status, connection_for, service_for, submit_order
from .webhooks import parse_webhook, verify_webhook


def _shipment_data(shipment):
    return {'id': shipment.pk, 'order_id': shipment.order_id, 'status': shipment.status,
            'tracking_code': shipment.tracking_code, 'consignment_id': shipment.external_shipment_id}


@api_view(['POST'])
def create_shipment(request, business_id, connection_id):
    require_access(request.user, business_id, manage=True)
    connection = connection_for(business_id, connection_id)
    order_id = serializers.IntegerField(min_value=1).run_validation(request.data.get('order_id'))
    try:
        shipment, created = submit_order(connection, order_id, request.data)
    except (CredentialUnavailable, SteadfastError) as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response({'shipment': _shipment_data(shipment), 'created': created},
                    status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['POST'])
def refresh_shipment(request, business_id, connection_id, shipment_id):
    require_access(request.user, business_id, manage=True)
    connection = connection_for(business_id, connection_id)
    shipment = Shipment.objects.filter(pk=shipment_id, business_id=business_id, integration_connection=connection).first()
    if shipment is None:
        raise NotFound('Shipment not found.')
    try:
        result = service_for(connection).status_by_tracking_code(shipment.tracking_code)
    except (CredentialUnavailable, SteadfastError) as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    shipment, changed = apply_status(shipment, result['delivery_status'])
    return Response({'shipment': _shipment_data(shipment), 'changed': changed})


@csrf_exempt
def webhook(request, business_id, connection_id):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    try:
        connection = connection_for(business_id, connection_id)
        if connection.integration_source.key.lower() != 'steadfast' or connection.is_mock or connection.status == 'DISABLED':
            return JsonResponse({'detail': 'Webhook unavailable.'}, status=404)
        config = connection.config or {}
        webhook_config = config.get('webhooks') or {}
        if not webhook_config.get('enabled'):
            return JsonResponse({'detail': 'Webhook unavailable.'}, status=404)
        if 'scopes' in config and 'READ_SHIPMENTS' not in config['scopes']:
            return JsonResponse({'detail': 'Shipment access is disabled.'}, status=403)
        token = resolve_credentials(connection).get('webhook_secret')
        if not token or not verify_webhook(request.body, token=token,
                                           signature=request.headers.get('X-Steadfast-Signature'),
                                           authorization=request.headers.get('Authorization')):
            return JsonResponse({'detail': 'Invalid webhook authentication.'}, status=401)
        event = parse_webhook(request.body)
        if event['notification_type'] not in webhook_config.get('events', []):
            return JsonResponse({'detail': 'Event is not subscribed.'}, status=403)
        consignment = event.get('consignment') if isinstance(event.get('consignment'), dict) else event
        external_id = consignment.get('consignment_id')
        tracking_code = consignment.get('tracking_code')
        shipment = None
        if external_id is not None:
            shipment = Shipment.objects.filter(business_id=business_id, integration_connection=connection,
                                               external_shipment_id=str(external_id)).first()
        if shipment is None and external_id is None and tracking_code:
            shipment = Shipment.objects.filter(business_id=business_id, integration_connection=connection,
                                               tracking_code=tracking_code).first()
        if tracking_code and external_id is not None and (shipment is None or shipment.tracking_code != tracking_code):
            return JsonResponse({'detail': 'Conflicting consignment identifiers.'}, status=400)
        provider_status = consignment.get('delivery_status') or consignment.get('status') or event.get('delivery_status')
        if shipment is None or not isinstance(provider_status, str):
            return JsonResponse({'accepted': True, 'updated': False})
        updated_at = consignment.get('updated_at', event.get('updated_at'))
        if updated_at is not None:
            try:
                occurred_at = parse_datetime(updated_at)
            except (TypeError, ValueError):
                occurred_at = None
            if occurred_at is None:
                raise ValidationError({'updated_at': 'A valid date and time is required.'})
        else:
            occurred_at = None
        charge = consignment.get('delivery_charge', event.get('delivery_charge'))
        if charge is not None:
            charge = serializers.DecimalField(max_digits=18, decimal_places=2,
                                              min_value=Decimal('0')).run_validation(charge)
        _, changed = apply_status(shipment, provider_status, event_type='WEBHOOK_STATUS',
                                  occurred_at=occurred_at, delivery_charge=charge)
        return JsonResponse({'accepted': True, 'updated': changed})
    except NotFound:
        return JsonResponse({'detail': 'Integration connection not found.'}, status=404)
    except (CredentialUnavailable, SteadfastError, ValidationError) as exc:
        return JsonResponse({'detail': str(exc)}, status=400)
