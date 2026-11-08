import json

from django.test import Client, TestCase
from django.contrib.auth import get_user_model

from app.models import Business, BusinessMembership


class FrontendAuthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('frontend-user', password='safe-password-123')
        self.business = Business.objects.create(name='North shop', slug='north-shop')
        BusinessMembership.objects.create(user=self.user, business=self.business, role='MANAGER')
        self.client = Client(enforce_csrf_checks=True)

    def test_session_login_and_logout_require_csrf(self):
        session = self.client.get('/api/frontend/session/')
        self.assertEqual(session.status_code, 200)
        self.assertFalse(session.json()['authenticated'])
        self.assertEqual(self.client.cookies['csrftoken']['samesite'], 'Lax')
        token = self.client.cookies['csrftoken'].value
        body = json.dumps({'username': 'frontend-user', 'password': 'safe-password-123'})
        self.assertEqual(self.client.post('/api/frontend/login/', body, content_type='application/json').status_code, 403)
        login = self.client.post('/api/frontend/login/', body, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()['businesses'][0]['id'], self.business.pk)
        self.assertEqual(login.json()['businesses'][0]['role'], 'MANAGER')
        self.assertTrue(self.client.cookies['sessionid']['httponly'])
        self.assertEqual(self.client.post('/api/frontend/logout/').status_code, 403)
        new_token = self.client.cookies['csrftoken'].value
        self.assertEqual(self.client.post('/api/frontend/logout/', HTTP_X_CSRFTOKEN=new_token).status_code, 200)
        self.assertFalse(self.client.get('/api/frontend/session/').json()['authenticated'])

    def test_login_does_not_disclose_other_memberships(self):
        other = Business.objects.create(name='Private shop', slug='private-shop')
        BusinessMembership.objects.create(user=self.user, business=other, role='VIEWER', is_active=False)
        self.client.get('/api/frontend/session/')
        token = self.client.cookies['csrftoken'].value
        body = json.dumps({'username': 'frontend-user', 'password': 'safe-password-123'})
        response = self.client.post('/api/frontend/login/', body, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertNotIn('Private shop', response.content.decode())
