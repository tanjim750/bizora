from datetime import timedelta

from rest_framework.test import APIClient

from app.models import BusinessIssue, BusinessMetric, MetricSnapshot
from app.tests.observability_helpers import NOW, setup_businesses


START = NOW.replace(hour=0) - timedelta(days=1)
END = START + timedelta(days=1)


def setup_overview(test):
    setup_businesses(test)
    test.business.timezone = 'UTC'
    test.business.save(update_fields=['timezone'])
    test.client = APIClient()
    test.client.force_authenticate(test.user)
    test.base = f'/api/businesses/{test.business.pk}/overview/'


def metric(business, key='total_revenue', category='SALES', **kwargs):
    return BusinessMetric.objects.create(business=business, key=key, name=key.replace('_', ' ').title(),
        category=category, created_at=NOW, updated_at=NOW, **kwargs)


def snapshot(business, definition, value='100', start=START, end=END, **kwargs):
    return MetricSnapshot.objects.create(business=business, metric=definition, value=value,
        period_start=start, period_end=end, period_type=kwargs.pop('period_type', 'DAY'),
        calculated_at=kwargs.pop('calculated_at', END), created_at=END, **kwargs)


def issue(business, **kwargs):
    return BusinessIssue.objects.create(business=business, issue_type=kwargs.pop('issue_type', 'HIGH_DELIVERY_FAILURE'),
        title=kwargs.pop('title', 'Delivery needs attention'), severity=kwargs.pop('severity', 'HIGH'),
        metadata=kwargs.pop('metadata', {'domains': ['delivery'], 'trend': 'WORSENING'}),
        detected_at=NOW - timedelta(hours=1), created_at=NOW - timedelta(hours=1), updated_at=NOW, **kwargs)
