from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from app.observability.policies import freshness, provider_health, safe_details


NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


class FreshnessPolicyTests(SimpleTestCase):
    def test_exact_thresholds_and_missing_coverage(self):
        for seconds, expected in [(0, 'FRESH'), (900, 'FRESH'), (901, 'DELAYED'),
                                  (1800, 'DELAYED'), (1801, 'STALE')]:
            with self.subTest(seconds=seconds):
                result = freshness(NOW - timedelta(seconds=seconds), NOW, 900, 1800)
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['age_seconds'], seconds)
        self.assertEqual(freshness(None, NOW, 900, 1800)['status'], 'UNAVAILABLE')

    def test_future_coverage_is_explained_not_negative(self):
        result = freshness(NOW + timedelta(seconds=1), NOW, 900, 1800)
        self.assertEqual(result['status'], 'UNAVAILABLE')
        self.assertEqual(result['reason'], 'FUTURE_WATERMARK')
        self.assertIsNone(result['age_seconds'])

    def test_invalid_policy_is_rejected(self):
        for delayed, stale in [(0, 10), (30, 20), (-1, 30)]:
            with self.subTest(delayed=delayed, stale=stale), self.assertRaises(ValueError):
                freshness(NOW, NOW, delayed, stale)


class ProviderPolicyTests(SimpleTestCase):
    def test_no_samples_or_insufficient_connections_is_unknown(self):
        self.assertEqual(provider_health([])['status'], 'UNKNOWN')
        rows = [dict(connection_id=1, outcome='PROVIDER_ERROR', latency_ms=10)] * 3
        self.assertEqual(provider_health(rows)['status'], 'UNKNOWN')

    def test_auth_failure_is_not_provider_outage(self):
        rows = [dict(connection_id=i, outcome='AUTH_ERROR', latency_ms=10) for i in [1, 2, 1]]
        self.assertEqual(provider_health(rows)['status'], 'UNKNOWN')

    def test_scoped_outage_degradation_rate_limits_and_recovery(self):
        for outcome, latency, expected in [('PROVIDER_ERROR', 10, 'UNAVAILABLE'),
                                            ('RATE_LIMIT', 10, 'DEGRADED'),
                                            ('SUCCESS', 3000, 'DEGRADED'),
                                            ('SUCCESS', 10, 'HEALTHY')]:
            rows = [dict(connection_id=i, outcome=outcome, latency_ms=latency) for i in [1, 2, 1]]
            with self.subTest(outcome=outcome, latency=latency):
                self.assertEqual(provider_health(rows)['status'], expected)


class SafeDetailsTests(SimpleTestCase):
    def test_common_inline_tokens_and_basic_authorization_are_redacted(self):
        result = safe_details('GET /?token=private-inline-token Authorization: Basic private-basic-credential')
        self.assertNotIn('private-inline-token', result)
        self.assertNotIn('private-basic-credential', result)

    def test_recursive_case_insensitive_redaction_and_safe_text(self):
        result = safe_details({'Authorization': 'Bearer abc', 'nested': [{'Access_Token': 'secret'}],
                               'message': 'request failed api_key=shh password=pwd', 'ok': 1})
        self.assertNotIn('abc', str(result))
        self.assertNotIn('secret', str(result))
        self.assertNotIn('shh', str(result))
        self.assertNotIn('pwd', str(result))
        self.assertEqual(result['ok'], 1)
