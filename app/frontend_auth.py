"""Session endpoints for the separate Next.js operations client."""
import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from app.models import BusinessMembership


def session_payload(request):
    if not request.user.is_authenticated or not request.user.is_active:
        return {'authenticated': False, 'businesses': []}
    memberships = BusinessMembership.objects.filter(
        user=request.user, is_active=True,
    ).select_related('business').order_by('business__name')
    return {
        'authenticated': True,
        'username': request.user.get_username(),
        'businesses': [
            {'id': item.business_id, 'name': item.business.name, 'role': item.role,
             'currency': item.business.currency, 'timezone': item.business.timezone}
            for item in memberships
        ],
    }


@require_GET
@ensure_csrf_cookie
def frontend_session(request):
    return JsonResponse(session_payload(request))


@require_POST
@csrf_protect
def frontend_login(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'detail': 'Invalid sign-in request.'}, status=400)
    if not isinstance(data, dict) or not isinstance(data.get('username'), str) or not isinstance(data.get('password'), str):
        return JsonResponse({'detail': 'Username and password are required.'}, status=400)
    user = authenticate(request, username=data['username'], password=data['password'])
    if user is None or not user.is_active:
        return JsonResponse({'detail': 'Invalid username or password.'}, status=401)
    login(request, user)
    return JsonResponse(session_payload(request))


@require_POST
@csrf_protect
def frontend_logout(request):
    logout(request)
    return JsonResponse({'authenticated': False})
