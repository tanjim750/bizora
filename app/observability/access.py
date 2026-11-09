from rest_framework.exceptions import PermissionDenied

from app.models import BusinessAccess, BusinessMembership


def require_access(user, business_id, manage=False):
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied('Authentication is required.')
    if user.is_superuser:
        return
    membership = BusinessMembership.objects.filter(user=user, business_id=business_id).first()
    if membership is not None:
        membership_roles = ['OWNER', 'MANAGER'] if manage else ['OWNER', 'MANAGER', 'OPERATOR', 'VIEWER']
        if membership.is_active and membership.role in membership_roles:
            return
        raise PermissionDenied('No permission for this business operation.')
    grants = BusinessAccess.objects.filter(user=user, business_id=business_id, role__in=['READER', 'MANAGER'])
    if manage:
        grants = grants.filter(role='MANAGER')
    if not grants.exists():
        raise PermissionDenied('No permission for this business operation.')
