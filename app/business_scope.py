"""Shared tenant seam for the Business Intelligence and Business Graph HTTP APIs.

The business is always taken from the URL (``businesses/<business_id>/...``) and the
caller must hold an active membership (or an equivalent ``BusinessAccess`` grant) for it,
exactly like the Overview and Observability domains:

* safe methods (GET/HEAD/OPTIONS): any member role may read;
* every other method (writes, pipeline runs, graph rebuilds, snapshot creation):
  OWNER or MANAGER only.

A caller that is not a member of the business gets the same 403 whether the business
exists or not, so the response never reveals another tenant's identifiers. Every error
leaves these views as ``{"code": ..., "detail": ...}`` (plus ``fields`` for validation).
"""

from __future__ import annotations

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import Business
from app.observability.access import require_access

NOT_FOUND_DETAIL = "The requested resource was not found or access is denied."

_CODE_BY_DRF_CODE = {
    "permission_denied": "FORBIDDEN",
    "not_authenticated": "NOT_AUTHENTICATED",
    "authentication_failed": "NOT_AUTHENTICATED",
    "parse_error": "INVALID_DATA",
    "not_found": "NOT_FOUND",
}


def error_response(code: str, detail: str, http_status: int, **extra) -> Response:
    """Build the uniform ``{code, detail}`` error body used by both APIs."""
    return Response({"code": code, "detail": detail, **extra}, status=http_status)


class HasAuthorizedBusiness(permissions.BasePermission):
    """Membership check for the business id in the URL; managers only for unsafe methods."""

    def has_permission(self, request, view):
        business_id = view.kwargs.get("business_id")
        if not isinstance(business_id, int) or isinstance(business_id, bool):
            return False
        # Raises PermissionDenied (403) for non-members, wrong roles and inactive users.
        require_access(request.user, business_id, manage=request.method not in permissions.SAFE_METHODS)
        return True


class BusinessScopedAPIView(APIView):
    """Base view: authenticated, member of the URL business, uniform error shape."""

    permission_classes = [permissions.IsAuthenticated, HasAuthorizedBusiness]

    def get_authorized_business(self) -> Business:
        cached = getattr(self, "_authorized_business", None)
        if cached is None:
            cached = self._authorized_business = get_object_or_404(Business, pk=self.kwargs["business_id"])
        return cached

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return error_response("NOT_FOUND", NOT_FOUND_DETAIL, status.HTTP_404_NOT_FOUND)
        response = super().handle_exception(exc)
        if response is None or not isinstance(exc, exceptions.APIException):
            return response
        if isinstance(exc, exceptions.ValidationError):
            response.data = {"code": "INVALID_DATA", "detail": "The request is invalid.", "fields": response.data}
            return response
        codes = exc.get_codes()
        key = codes if isinstance(codes, str) else exc.default_code
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.default_detail)
        response.data = {"code": _CODE_BY_DRF_CODE.get(key, str(key).upper()), "detail": str(detail)}
        return response
