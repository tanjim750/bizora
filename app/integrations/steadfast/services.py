"""Validated Steadfast operations, adapted from the sibling PHP SDK."""
import re
from decimal import Decimal
from urllib.parse import quote

from rest_framework import serializers

from .client import SteadfastClient, SteadfastError


PHONE = r'^01[0-9]{9}$'
INVOICE = r'^[A-Za-z0-9_-]{1,100}$'


class OrderRequest(serializers.Serializer):
    invoice = serializers.RegexField(INVOICE)
    recipient_name = serializers.CharField(max_length=100)
    recipient_phone = serializers.RegexField(PHONE)
    recipient_address = serializers.CharField(max_length=490)
    cod_amount = serializers.DecimalField(max_digits=9, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('1000000'))
    note = serializers.CharField(max_length=480, required=False, allow_blank=True)
    alternative_phone = serializers.RegexField(PHONE, required=False)
    recipient_email = serializers.EmailField(required=False)
    item_description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    total_lot = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'), default=1)
    delivery_type = serializers.ChoiceField(choices=[0, 1], default=0)


class ReturnRequest(serializers.Serializer):
    consignment_id = serializers.IntegerField(min_value=1, required=False)
    invoice = serializers.RegexField(INVOICE, required=False)
    tracking_code = serializers.CharField(required=False)
    reason = serializers.CharField()

    def validate(self, attrs):
        if sum(key in attrs for key in ('consignment_id', 'invoice', 'tracking_code')) != 1:
            raise serializers.ValidationError({'identifier': 'Exactly one parcel identifier is required.'})
        return attrs


class PickupRequest(serializers.Serializer):
    address_id = serializers.IntegerField(min_value=1)
    police_station_id = serializers.IntegerField(min_value=1)
    address = serializers.CharField()
    contact_number = serializers.RegexField(PHONE)
    estim_qty = serializers.IntegerField(min_value=1)


def _validated(schema, value):
    serializer = schema(data=value)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.data)
    if schema is OrderRequest:
        # The courier's JSON contract uses numbers for these fields.
        data['cod_amount'] = float(serializer.validated_data['cod_amount'])
        data['total_lot'] = float(serializer.validated_data['total_lot'])
    return data


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise serializers.ValidationError({label: 'A nonempty identifier is required.'})
    return quote(value, safe='')


def _invoice(value):
    if not isinstance(value, str) or not re.fullmatch(INVOICE, value):
        raise serializers.ValidationError({'invoice': 'Invoice may contain only letters, digits, hyphens, and underscores (up to 100 characters).'})
    return value


class SteadfastService:
    def __init__(self, client: SteadfastClient):
        self.client = client

    def create_order(self, order):
        payload = _validated(OrderRequest, order)
        data = self.client.post('/create_order', payload, retry=False)
        consignment = data.get('consignment') if isinstance(data, dict) else None
        if (not isinstance(data, dict) or data.get('status') != 200
                or not isinstance(data.get('message'), str) or not isinstance(consignment, dict)
                or not isinstance(consignment.get('consignment_id'), int)
                or not all(isinstance(consignment.get(key), str) for key in
                           ('invoice', 'tracking_code', 'tracking_link', 'status', 'created_at'))
                or not consignment['tracking_code'] or consignment['invoice'] != payload['invoice']):
            raise SteadfastError('Steadfast returned an unusable create-order response.', response=data)
        return data

    def create_bulk(self, orders, *, extended=False):
        if not isinstance(orders, list) or not 1 <= len(orders) <= 500:
            raise serializers.ValidationError({'data': 'Provide between 1 and 500 orders.'})
        payload = {'data': [_validated(OrderRequest, order) for order in orders]}
        endpoint = '/create_order/bulk-order/extended' if extended else '/create_order/bulk-order'
        return self.client.post(endpoint, payload, retry=False)

    def status_by_consignment_id(self, consignment_id, *, with_return=False):
        if isinstance(consignment_id, bool) or not isinstance(consignment_id, int) or consignment_id <= 0:
            raise serializers.ValidationError({'consignment_id': 'A positive integer is required.'})
        prefix = '/status_with_return_status_by_cid/' if with_return else '/status_by_cid/'
        return self._status(prefix + str(consignment_id))

    def status_by_invoice(self, invoice):
        return self._status('/status_by_invoice/' + _invoice(invoice))

    def status_by_tracking_code(self, tracking_code):
        return self._status('/status_by_trackingcode/' + _identifier(tracking_code, 'tracking_code'))

    def _status(self, endpoint):
        result = self.client.get(endpoint)
        if not isinstance(result, dict) or not isinstance(result.get('status'), int) or not isinstance(result.get('delivery_status'), str):
            raise SteadfastError('Steadfast returned an unusable tracking-status response.', response=result)
        return result

    def history_by_invoice(self, invoice):
        return self.client.get('/trackings_by_invoice/' + _invoice(invoice))

    def create_return(self, request):
        return self.client.post('/create_return_request', _validated(ReturnRequest, request))

    def list_returns(self):
        return self.client.get('/get_return_requests')

    def get_return(self, request_id):
        return self.client.get('/get_return_request/' + _identifier(str(request_id) if request_id is not None else '', 'id'))

    def create_pickup(self, request):
        return self.client.post('/create_pickup_request', _validated(PickupRequest, request))

    def balance(self):
        return self.client.get('/get_balance')

    def list_payments(self):
        return self.client.get('/payments')

    def get_payment(self, payment_id):
        return self.client.get('/payments/' + _identifier(payment_id, 'payment_id'))

    def police_stations(self):
        return self.client.get('/police_stations')

    def fraud_score(self, phone):
        if not isinstance(phone, str) or not re.fullmatch(PHONE, phone):
            raise serializers.ValidationError({'phone': 'Phone must be an 11-digit number beginning with 01.'})
        return self.client.get('/fraud_check/score/' + phone)
