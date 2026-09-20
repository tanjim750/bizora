from django.core.exceptions import PermissionDenied

from app.models import BusinessMembership


def require_business_access(user, business, *, roles=None):
    """Fail closed for tenant access; the dynamic attribute is test/legacy-only."""
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication required.")
    if getattr(user, "is_superuser", False):
        return
    if getattr(user, "business_id", None) == business.id:
        return
    membership = BusinessMembership.objects.filter(
        user=user, business=business, is_active=True
    ).first()
    if not membership or (roles and membership.role not in roles):
        raise PermissionDenied("Business access is required.")


def ensure_same_business(business, *entities):
    for entity in entities:
        if entity is not None and getattr(entity, "business_id", business.id) != business.id:
            raise PermissionDenied("Cross-business data access is prohibited.")
