from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase

from app.models import ConfigurationEvent, ConfigurationRecord, MetricSnapshot, MonitoringConfiguration, MonitoringPolicy
from app.overview.configuration import configuration
from app.tests.configuration_helpers import setup_configuration
from app.tests.observability_helpers import NOW
from app.tests.overview_helpers import END, metric, snapshot


@patch('app.configuration.views.timezone.now', return_value=NOW)
class ConfigurationMonitoringTests(TestCase):
    def setUp(self):
        setup_configuration(self)
        self.business.timezone = 'UTC'
        self.business.save(update_fields=['timezone'])

    def test_default_reporting_inheritance_explicit_override_and_business_week(self, _):
        result = self.client.put(self.base+'general/', {'reporting_period': 'WEEK', 'week_start': 6}, format='json')
        self.assertEqual(result.status_code, 200)
        config = configuration(self.business.pk)
        self.assertEqual((config['period'], config['week_start']), ('WEEK', 6))
        response = self.client.get(f'/api/businesses/{self.business.pk}/overview/kpis/')
        self.assertEqual(response.data['window']['end'], '2026-10-25T00:00:00+00:00')
        self.client.put(self.base+'monitoring/', {'period': 'MONTH'}, format='json')
        self.assertEqual(configuration(self.business.pk)['period'], 'MONTH')
        self.client.put(self.base+'monitoring/', {'inherit_reporting_period': True}, format='json')
        self.assertEqual(configuration(self.business.pk)['period'], 'WEEK')

    def test_old_monitoring_records_keep_their_explicit_period(self, _):
        MonitoringConfiguration.objects.create(business=self.business, settings={'period': 'DAY'})
        self.client.put(self.base+'general/', {'reporting_period': 'MONTH'}, format='json')
        self.assertEqual(configuration(self.business.pk)['period'], 'DAY')

    def test_target_baseline_and_no_comparison_are_consumed_by_kpi_views(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition, '120')
        for mode, value, expected in [('TARGET', '100', '20.000000'), ('BASELINE', '80', '40.000000')]:
            field = 'target_value' if mode == 'TARGET' else 'baseline_value'
            result = self.client.put(self.base+'monitoring/', {'comparison_mode': mode,
                'kpis': [{'key': definition.key, 'direction': 'HIGHER', field: value}]}, format='json')
            self.assertEqual(result.status_code, 200, result.data)
            card = self.client.get(f'/api/businesses/{self.business.pk}/overview/kpis/').data['results'][0]
            self.assertEqual(card['comparison']['delta'], expected)
            self.assertEqual(card['comparison']['mode'], mode)
            self.assertIsNone(card['comparison']['previous_value'])
        self.client.put(self.base+'monitoring/', {'comparison_mode': 'NONE'}, format='json')
        card = self.client.get(f'/api/businesses/{self.business.pk}/overview/kpis/').data['results'][0]
        self.assertEqual(card['comparison']['reason'], 'COMPARISON_DISABLED')

    def test_rolling_windows_require_exact_upstream_snapshots(self, _):
        definition = metric(self.business)
        self.client.put(self.base+'monitoring/', {'period': 'ROLLING_7D', 'kpis': [{'key': definition.key}]}, format='json')
        point = MetricSnapshot.objects.create(business=self.business, metric=definition, value='500',
            period_start=END-timedelta(days=7), period_end=END, period_type='ROLLING_7D', calculated_at=END, created_at=END)
        result = self.client.get(f'/api/businesses/{self.business.pk}/overview/kpis/').data
        self.assertEqual(result['results'][0]['snapshot_id'], point.pk)
        self.assertEqual(result['window']['period'], 'ROLLING_7D')

    def test_freshness_settings_are_shared_and_have_change_history(self, _):
        body = {'connection_id': self.connection.pk, 'entity_type': 'ORDER', 'delayed_seconds': 300,
                'stale_seconds': 600, 'enabled': True}
        result = self.client.put(self.base+'freshness/', body, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(MonitoringPolicy.objects.get().stale_seconds, 600)
        self.assertTrue(ConfigurationRecord.objects.filter(kind='FRESHNESS').exists())
        legacy = self.client.put(f'/api/businesses/{self.business.pk}/observability/policies/',
            {**body, 'stale_seconds': 900}, format='json')
        self.assertEqual(legacy.status_code, 200)
        record = ConfigurationRecord.objects.get(kind='FRESHNESS')
        self.assertEqual(record.version, 2)
        self.assertEqual(record.revisions.count(), 2)
        self.assertEqual(record.data['stale_seconds'], 900)
        self.assertEqual(ConfigurationEvent.objects.filter(section='FRESHNESS').count(), 2)

    def test_target_assessment_does_not_claim_a_temporal_trend(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition, '80')
        result = self.client.put(self.base+'monitoring/', {'domains': ['sales'], 'comparison_mode': 'TARGET',
            'kpis': [{'key': definition.key, 'direction': 'HIGHER', 'target_value': '100', 'warning_severity': 'HIGH'}]}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        health = self.client.get(f'/api/businesses/{self.business.pk}/overview/health/').data
        self.assertEqual(health['status'], 'WARNING')
        self.assertEqual(health['trend'], 'UNKNOWN')
        self.assertEqual(health['domains']['sales']['evidence'][0]['severity'], 'HIGH')
