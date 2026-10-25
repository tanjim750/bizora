from datetime import datetime, timezone

from django.contrib.auth import get_user_model

from app.models import Business, IntegrationConnection, IntegrationSource


NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def setup_businesses(test):
    from app.models import BusinessAccess
    test.business = Business.objects.create(name='Shop', slug='shop', created_at=NOW, updated_at=NOW)
    test.other_business = Business.objects.create(name='Other', slug='other', created_at=NOW, updated_at=NOW)
    test.source = IntegrationSource.objects.create(key='woocommerce', name='WooCommerce', category='COMMERCE',
                                                   created_at=NOW, updated_at=NOW)
    test.connection = make_connection(test.business, test.source)
    test.other_connection = make_connection(test.other_business, test.source)
    test.user = get_user_model().objects.create_user(username='manager')
    test.reader = get_user_model().objects.create_user(username='reader')
    BusinessAccess.objects.create(business=test.business, user=test.user, role='MANAGER')
    BusinessAccess.objects.create(business=test.business, user=test.reader, role='READER')


def make_connection(business, source, **kwargs):
    return IntegrationConnection.objects.create(business=business, integration_source=source,
                                                created_at=NOW, updated_at=NOW, **kwargs)


def observe(test, kind, data, key='event-1', **kwargs):
    from app.observability.services import record_observation
    at = kwargs.pop('observed_at', NOW)
    received = at if at.tzinfo is not None and at > NOW else NOW
    return record_observation(business_id=test.business.pk, connection_id=test.connection.pk,
                              key=key, kind=kind, data=data, observed_at=at,
                              received_at=kwargs.pop('received_at', received), **kwargs)
