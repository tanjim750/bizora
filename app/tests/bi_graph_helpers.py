"""Shared fixtures for the Business Intelligence and Business Graph HTTP API tests."""

from itertools import count

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from app import models

_users = count(1)


def make_user(**extra):
    return get_user_model().objects.create_user(username=f"bi-graph-user-{next(_users)}", password="x", **extra)


def make_member(business, role="OWNER", is_active=True, **extra):
    """Create a user with a membership of ``role`` in ``business``."""
    user = make_user(**extra)
    models.BusinessMembership.objects.create(business=business, user=user, role=role, is_active=is_active)
    return user


class JSONClient(APIClient):
    """APIClient that sends JSON bodies whatever the active REST_FRAMEWORK test format is."""

    def post(self, path, data=None, format="json", **extra):
        return super().post(path, data, format=format, **extra)

    def patch(self, path, data=None, format="json", **extra):
        return super().patch(path, data, format=format, **extra)


def client_for(user=None):
    client = JSONClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def intelligence_url(business_id, tail=""):
    return f"/api/businesses/{business_id}/intelligence/{tail}"


def graph_url(business_id, tail=""):
    return f"/api/businesses/{business_id}/graph/{tail}"
