from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from app.models import Business, BusinessAccess, BusinessMembership
from app.observability.access import require_access


class ModuleMembershipAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='module-reader')
        self.business = Business.objects.create(name='Scoped shop', slug='scoped-shop')
        self.other = Business.objects.create(name='Other shop', slug='other-shop')
        self.membership = BusinessMembership.objects.create(
            user=self.user, business=self.business, role='VIEWER', is_active=True,
        )

    def test_active_membership_grants_only_scoped_reads(self):
        require_access(self.user, self.business.pk)
        with self.assertRaises(PermissionDenied):
            require_access(self.user, self.other.pk)
        with self.assertRaises(PermissionDenied):
            require_access(self.user, self.business.pk, manage=True)

    def test_manager_write_and_inactive_revocation(self):
        self.membership.role = 'MANAGER'
        self.membership.save(update_fields=['role'])
        require_access(self.user, self.business.pk, manage=True)
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        with self.assertRaises(PermissionDenied):
            require_access(self.user, self.business.pk)

    def test_membership_role_and_revocation_override_legacy_grant(self):
        BusinessAccess.objects.create(user=self.user, business=self.business, role='MANAGER')
        with self.assertRaises(PermissionDenied):
            require_access(self.user, self.business.pk, manage=True)
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        with self.assertRaises(PermissionDenied):
            require_access(self.user, self.business.pk)
