import hashlib
import hmac
import io
import json
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError

from app.models import Business, BusinessMembership, IntegrationConnection, IntegrationSource, Order, Shipment, ShipmentEvent

from .client import SteadfastClient, SteadfastError, SteadfastNetworkError
from .integration import apply_status, service_for, submit_order
from .services import SteadfastService
from .webhooks import parse_webhook, verify_webhook


class _Response:
    def __init__(self, status, payload, headers=None):
        self.status = status
        self.payload = json.dumps(payload).encode()
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.payload


class SteadfastClientTests(SimpleTestCase):
    def setUp(self):
        self.calls = []
        self.responses = []

        def transport(request, timeout):
            self.calls.append((request, timeout))
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        self.client = SteadfastClient('api-key', 'secret-key', transport=transport, sleep=lambda value: self.delays.append(value))
        self.delays = []

    def test_auth_ping_and_endpoint_restriction(self):
        self.responses = [_Response(200, {'status': 200})]
        self.assertEqual(self.client.ping(), {'status': 200})
        request = self.calls[0][0]
        self.assertEqual(request.full_url, 'https://portal.packzy.com/api/v1/ping')
        self.assertIsNone(request.get_header('Api-key'))
        for endpoint in ('https://evil.example/', '//evil.example/', '../escape', '?a=1'):
            with self.assertRaises(ValueError):
                self.client.get(endpoint)

    def test_retry_after_and_error_details(self):
        self.responses = [_Response(429, {'message': 'slow'}, {'Retry-After': '2'}),
                          _Response(422, {'message': 'invalid', 'errors': {'phone': ['invalid']}})]
        with self.assertRaises(SteadfastError) as ctx:
            self.client.get('/status_by_cid/1')
        self.assertEqual(ctx.exception.status, 422)
        self.assertEqual(ctx.exception.errors['phone'], ['invalid'])
        self.assertEqual(self.delays, [2.0])
        self.assertEqual(self.calls[0][0].get_header('Api-key'), 'api-key')
        self.assertEqual(self.calls[0][0].get_header('Secret-key'), 'secret-key')

    def test_network_retry_and_post_is_not_retried_by_default(self):
        self.responses = [URLError('down'), _Response(200, {'ok': True})]
        self.assertEqual(self.client.get('/get_balance'), {'ok': True})
        self.assertEqual(len(self.calls), 2)
        self.responses = [URLError('down')]
        with self.assertRaises(SteadfastNetworkError):
            self.client.post('/create_pickup_request', {})
        self.assertEqual(len(self.calls), 3)

    def test_http_error_does_not_follow_redirect(self):
        self.responses = [HTTPError('https://example.invalid', 302, 'redirect', {}, io.BytesIO(b'{}'))]
        with self.assertRaises(SteadfastError) as ctx:
            self.client.get('/ping')
        self.assertEqual(ctx.exception.status, 302)


class SteadfastServiceTests(SimpleTestCase):
    def setUp(self):
        self.client = SimpleNamespace(post=self.post, get=self.get)
        self.calls = []
        self.service = SteadfastService(self.client)

    def post(self, endpoint, payload, **options):
        self.calls.append(('POST', endpoint, payload, options))
        return {'status': 200, 'message': 'Created', 'consignment': {
            'consignment_id': 5, 'invoice': 'ORD_1', 'tracking_code': 'ABC',
            'tracking_link': 'https://example.test/track/ABC', 'status': 'pending', 'created_at': '2026-11-16'}}

    def get(self, endpoint):
        self.calls.append(('GET', endpoint))
        return {'status': 200, 'delivery_status': 'delivered'}

    def test_order_validation_and_wire_payload(self):
        order = {'invoice': 'ORD_1', 'recipient_name': 'Customer', 'recipient_phone': '01712345678',
                 'recipient_address': 'Dhaka', 'cod_amount': '250.00'}
        self.service.create_order(order)
        self.assertEqual(self.calls[0][1], '/create_order')
        self.assertEqual(self.calls[0][2]['cod_amount'], 250.0)
        self.assertEqual(self.calls[0][2]['delivery_type'], 0)
        with self.assertRaises(ValidationError):
            self.service.create_order({**order, 'recipient_phone': '123'})
        with self.assertRaises(ValidationError):
            self.service.create_bulk([])

    def test_create_rejects_mismatched_provider_invoice(self):
        order = {'invoice': 'OTHER', 'recipient_name': 'Customer', 'recipient_phone': '01712345678',
                 'recipient_address': 'Dhaka', 'cod_amount': '250.00'}
        with self.assertRaises(SteadfastError):
            self.service.create_order(order)

    def test_operation_endpoints_and_validation(self):
        self.service.status_by_invoice('ORD_1')
        self.service.status_by_consignment_id(3, with_return=True)
        self.service.history_by_invoice('ORD_1')
        self.service.create_return({'invoice': 'ORD_1', 'reason': 'Damaged'})
        self.service.create_pickup({'address_id': 1, 'police_station_id': 2, 'address': 'Dhaka',
                                    'contact_number': '01712345678', 'estim_qty': 3})
        self.service.balance()
        self.service.list_payments()
        self.service.get_payment('pay/1')
        self.service.police_stations()
        self.service.fraud_score('01712345678')
        paths = [call[1] for call in self.calls]
        self.assertIn('/status_with_return_status_by_cid/3', paths)
        self.assertIn('/payments/pay%2F1', paths)
        self.assertIn('/fraud_check/score/01712345678', paths)
        with self.assertRaises(ValidationError):
            self.service.create_return({'invoice': 'ORD_1', 'tracking_code': 'X', 'reason': 'Damaged'})

    def test_webhook_authentication_and_parsing(self):
        raw = b'{"notification_type":"delivery_status"}'
        signature = hmac.new(b'token', raw, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook(raw, token='token', signature=signature))
        self.assertTrue(verify_webhook(raw, token='token', authorization='Bearer token'))
        self.assertFalse(verify_webhook(raw, token='token', signature='bad'))
        self.assertEqual(parse_webhook(raw)['notification_type'], 'delivery_status')
        with self.assertRaises(SteadfastError):
            parse_webhook(b'[]')


class SteadfastIntegrationTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name='Shop', slug='steadfast-shop')
        self.other = Business.objects.create(name='Other', slug='steadfast-other')
        source, _ = IntegrationSource.objects.get_or_create(key='steadfast', defaults={'name': 'Steadfast', 'category': 'COURIER'})
        self.connection = IntegrationConnection.objects.create(business=self.business, integration_source=source,
                                                                is_mock=False, config={'webhooks': {'enabled': True, 'events': ['delivery_status']}})
        self.order = Order.objects.create(business=self.business, total_amount='250.00')
        self.user = get_user_model().objects.create_user(username='steadfast-user', password='test-password')
        BusinessMembership.objects.create(user=self.user, business=self.business, role='MANAGER')
        self.client.force_login(self.user)

    def test_submit_once_and_apply_status(self):
        service = SimpleNamespace(create_order=lambda payload: {'consignment': {
            'consignment_id': 47, 'tracking_code': 'TRACK47', 'status': 'pending'}})
        details = {'recipient_name': 'A Person', 'recipient_phone': '01712345678', 'recipient_address': 'Dhaka'}
        shipment, created = submit_order(self.connection, self.order.pk, details, service=service)
        self.assertTrue(created)
        self.assertEqual(shipment.status, 'SUBMITTED')
        self.assertEqual(shipment.cod_amount, self.order.total_amount)
        self.assertEqual(shipment.source_metadata['invoice'], f'BIZORA-{self.order.pk}')
        self.assertEqual(ShipmentEvent.objects.count(), 1)
        again, created = submit_order(self.connection, self.order.pk, details, service=service)
        self.assertFalse(created)
        self.assertEqual(again.pk, shipment.pk)
        shipment, changed = apply_status(shipment, 'delivered')
        self.assertTrue(changed)
        self.assertIsNotNone(shipment.delivered_at)
        _, changed = apply_status(shipment, 'delivered')
        self.assertFalse(changed)
        self.assertEqual(ShipmentEvent.objects.count(), 2)

    def test_business_boundary_and_webhook_signature(self):
        url = f'/api/businesses/{self.business.pk}/integrations/steadfast/{self.connection.pk}/webhook/'
        raw = json.dumps({'notification_type': 'delivery_status', 'consignment_id': 99, 'status': 'delivered'}).encode()
        with patch('app.integrations.steadfast.views.resolve_credentials', return_value={'webhook_secret': 'token'}):
            self.assertEqual(self.client.post(url, raw, content_type='application/json').status_code, 401)
            signature = hmac.new(b'token', raw, hashlib.sha256).hexdigest()
            result = self.client.post(url, raw, content_type='application/json', HTTP_X_STEADFAST_SIGNATURE=signature)
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()['updated'])
        foreign_url = f'/api/businesses/{self.other.pk}/integrations/steadfast/{self.connection.pk}/webhook/'
        self.assertEqual(self.client.post(foreign_url, raw, content_type='application/json').status_code, 404)

    def test_signed_webhook_updates_only_matching_shipment(self):
        shipment = Shipment.objects.create(business=self.business, order=self.order,
                                           integration_connection=self.connection, external_shipment_id='99',
                                           tracking_code='TRACK99', provider='Steadfast', status='SUBMITTED')
        url = f'/api/businesses/{self.business.pk}/integrations/steadfast/{self.connection.pk}/webhook/'
        raw = json.dumps({'notification_type': 'delivery_status', 'consignment_id': 99,
                          'status': 'delivered'}).encode()
        signature = hmac.new(b'token', raw, hashlib.sha256).hexdigest()
        with patch('app.integrations.steadfast.views.resolve_credentials', return_value={'webhook_secret': 'token'}):
            first = self.client.post(url, raw, content_type='application/json', HTTP_X_STEADFAST_SIGNATURE=signature)
            second = self.client.post(url, raw, content_type='application/json', HTTP_X_STEADFAST_SIGNATURE=signature)
        shipment.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()['updated'])
        self.assertFalse(second.json()['updated'])
        self.assertEqual(shipment.status, 'DELIVERED')
        self.assertEqual(ShipmentEvent.objects.filter(shipment=shipment).count(), 1)

    def test_create_and_refresh_routes_require_business_access(self):
        base = f'/api/businesses/{self.business.pk}/integrations/steadfast/{self.connection.pk}/'
        response = {'consignment': {'consignment_id': 10, 'tracking_code': 'TRACK10', 'status': 'pending'}}
        service = SimpleNamespace(create_order=lambda payload: response,
                                  status_by_tracking_code=lambda code: {'status': 200, 'delivery_status': 'delivered'})
        with patch('app.integrations.steadfast.integration.service_for', return_value=service), \
             patch('app.integrations.steadfast.views.service_for', return_value=service):
            body = {'order_id': self.order.pk, 'recipient_name': 'A Person',
                    'recipient_phone': '01712345678', 'recipient_address': 'Dhaka'}
            created = self.client.post(base + 'shipments/', body, content_type='application/json')
            self.assertEqual(created.status_code, 201, created.content)
            self.assertTrue(created.json()['created'])
            repeated = self.client.post(base + 'shipments/', body, content_type='application/json')
            self.assertEqual(repeated.status_code, 200)
            self.assertFalse(repeated.json()['created'])
            shipment_id = created.json()['shipment']['id']
            refreshed = self.client.post(base + f'shipments/{shipment_id}/refresh/')
            self.assertEqual(refreshed.status_code, 200)
            self.assertEqual(refreshed.json()['shipment']['status'], 'DELIVERED')
            invalid = self.client.post(base + 'shipments/', {**body, 'order_id': 'invalid'}, content_type='application/json')
            self.assertEqual(invalid.status_code, 400)
        self.client.logout()
        self.assertEqual(self.client.post(base + 'shipments/', body, content_type='application/json').status_code, 403)

    def test_live_client_uses_secret_references_and_official_host(self):
        with patch('app.integrations.steadfast.integration.resolve_credentials',
                   return_value={'api_key': 'api-value', 'secret_key': 'secret-value'}):
            service = service_for(self.connection)
            self.assertEqual(service.client.api_key, 'api-value')
            self.connection.config = {'provider_settings': {'base_url': 'http://localhost:8080/api/v1'}}
            with self.assertRaises(ValidationError):
                service_for(self.connection)
