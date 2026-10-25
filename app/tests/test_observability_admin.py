from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from app.models import BusinessAccess, IntegrationPayload, MonitoringPolicy, ObservationReceipt


class ObservabilityAdminTests(TestCase):
    def test_operational_evidence_is_registered_read_only_and_payloads_are_not_exposed(self):
        self.assertIn(ObservationReceipt, admin.site._registry)
        self.assertNotIn(IntegrationPayload, admin.site._registry)
        request = RequestFactory().get('/admin/')
        request.user = get_user_model().objects.create_superuser(username='admin')
        model_admin = admin.site._registry[ObservationReceipt]
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
        self.assertTrue(model_admin.has_view_permission(request))

    def test_business_grants_and_policy_administration_require_superuser(self):
        user = get_user_model().objects.create_user(username='staff', is_staff=True)
        request = RequestFactory().get('/admin/')
        request.user = user
        for model in [BusinessAccess, MonitoringPolicy, ObservationReceipt]:
            self.assertIn(model, admin.site._registry)
            model_admin = admin.site._registry[model]
            self.assertFalse(model_admin.has_module_permission(request))
            self.assertFalse(model_admin.has_view_permission(request))
            self.assertFalse(model_admin.has_change_permission(request))
