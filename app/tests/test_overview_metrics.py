from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase

from app.models import MonitoringConfiguration
from app.tests.observability_helpers import NOW
from app.tests.overview_helpers import END, START, metric, setup_overview, snapshot


@patch('app.overview.views.timezone.now', return_value=NOW)
class OverviewMetricTests(TestCase):
    def setUp(self):
        setup_overview(self)

    def get(self, route='kpis/', **params):
        return self.client.get(self.base + route, params)

    def test_empty_business_is_unknown_and_read_does_not_create_configuration(self, _):
        result = self.get('summary/')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['health']['status'], 'UNKNOWN')
        self.assertEqual(result.data['business_status'], 'UNKNOWN')
        self.assertTrue(all(k['value'] is None for k in result.data['kpis']))
        self.assertFalse(MonitoringConfiguration.objects.exists())

    def test_exact_snapshot_revision_comparison_and_decimal_precision(self, _):
        definition = metric(self.business, unit='BDT')
        snapshot(self.business, definition, '100000001.123456')
        latest = snapshot(self.business, definition, '100000002.123456', calculated_at=NOW)
        snapshot(self.business, definition, '1', calculated_at=NOW + timedelta(seconds=1))
        snapshot(self.business, definition, '50000000', start=START-timedelta(days=1), end=START)
        # A dimensional snapshot and mismatched period are never added to the total.
        snapshot(self.business, definition, '999', dimension_type='region', dimension_value='Gazipur')
        snapshot(self.business, definition, '888', start=START-timedelta(hours=1))
        result = self.get(metric='total_revenue').data['results'][0]
        self.assertEqual(result['value'], '100000002.123456')
        self.assertEqual(result['snapshot_id'], latest.pk)
        self.assertEqual(result['comparison']['direction'], 'UP')
        self.assertEqual(result['comparison']['delta'], '50000002.123456')

    def test_foreign_metric_snapshot_is_excluded_even_with_local_business_fk(self, _):
        definition = metric(self.other_business)
        snapshot(self.business, definition)
        self.assertEqual(self.get(metric='total_revenue').data['results'][0]['status'], 'UNAVAILABLE')

    def test_zero_baseline_never_divides_by_zero(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition, '10')
        snapshot(self.business, definition, '0', start=START-timedelta(days=1), end=START)
        result = self.get(metric='total_revenue').data['results'][0]['comparison']
        self.assertIsNone(result['percent_change'])
        self.assertEqual(result['reason'], 'ZERO_BASELINE')

    def test_dimension_requires_pair_and_filters_exactly(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition, '20', dimension_type='region', dimension_value='Gazipur')
        self.assertEqual(self.get(dimension_type='region').status_code, 400)
        result = self.get(metric='total_revenue', dimension_type='region', dimension_value='Gazipur')
        self.assertEqual(result.data['results'][0]['value'], '20.000000')

    def test_trends_deduplicate_revisions_without_aggregating_rates(self, _):
        definition = metric(self.business, 'delivery_failure_rate', 'DELIVERY', unit='%')
        snapshot(self.business, definition, '9', start=START-timedelta(days=1), end=START)
        snapshot(self.business, definition, '19')
        snapshot(self.business, definition, '20', calculated_at=NOW)
        result = self.get('trends/', metric=definition.key).data['results'][0]
        self.assertEqual([p['value'] for p in result['points']], ['9.000000', '20.000000'])
        self.assertEqual(result['comparison']['delta'], '11.000000')
        self.assertEqual(result['comparison']['change_unit'], 'PERCENTAGE_POINTS')

    def test_stale_metrics_cannot_establish_healthy_state(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition, calculated_at=END)
        self.client.put(self.base+'configuration/', {'snapshot_ttl_seconds': 60, 'kpis': [
            {'key': definition.key, 'direction': 'HIGHER', 'warning': '50', 'critical': '10'}]}, format='json')
        result = self.get('health/').data
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(self.get(metric=definition.key).data['results'][0]['status'], 'STALE')

    def test_invalid_windows_filters_and_future_ranges_are_rejected(self, _):
        for params in ({'from': '2026-10-25'}, {'from': END.isoformat(), 'to': START.isoformat()},
                       {'from': START.isoformat(), 'to': (NOW+timedelta(days=1)).isoformat()},
                       {'domain': 'secrets'}, {'unknown': 'x'}, {'page_size': 1000},
                       {'from': START.replace(tzinfo=None).isoformat(), 'to': END.isoformat()}):
            with self.subTest(params=params):
                self.assertEqual(self.get(**params).status_code, 400)

    def test_default_calendar_window_uses_business_timezone(self, _):
        self.business.timezone = 'Asia/Dhaka'
        self.business.save(update_fields=['timezone'])
        result = self.get().data['window']
        self.assertEqual(result['start'], '2026-10-23T18:00:00+00:00')
        self.assertEqual(result['end'], '2026-10-24T18:00:00+00:00')
        self.assertEqual(result['timezone'], 'Asia/Dhaka')

    def test_explicit_window_is_used_for_exact_kpis(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition)
        result = self.get(metric=definition.key, **{'from': START.isoformat(), 'to': END.isoformat()})
        self.assertEqual(result.data['results'][0]['value'], '100.000000')

    def test_partial_calculation_does_not_stand_in_for_a_completed_period(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition, calculated_at=END-timedelta(hours=1))
        result = self.get(metric=definition.key).data['results'][0]
        self.assertEqual(result['status'], 'UNAVAILABLE')

    def test_blank_and_null_total_dimensions_share_one_revision_group(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition, '10', dimension_type=None, dimension_value=None)
        snapshot(self.business, definition, '20', dimension_type='', dimension_value='', calculated_at=NOW)
        result = self.get('trends/', metric=definition.key).data['results'][0]
        self.assertEqual(len(result['points']), 1)
        self.assertEqual(result['points'][0]['value'], '20.000000')
