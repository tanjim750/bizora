from rest_framework.test import APIClient

from app.tests.observability_helpers import setup_businesses


def setup_configuration(test):
    setup_businesses(test)
    test.client = APIClient()
    test.client.force_authenticate(test.user)
    test.base = f'/api/businesses/{test.business.pk}/configuration/'
