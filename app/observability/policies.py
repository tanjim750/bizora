"""Deterministic policies; no database, provider, or wall-clock side effects."""
import re
from datetime import datetime


SENSITIVE = re.compile(r'token|secret|password|authorization|api.?key|cookie|credential', re.I)
SECRET_TEXT = re.compile(
    r'(?i)(\b(?:bearer|basic)\s+)\S+'
    r'|(\b(?:authorization|proxy-authorization)\s*[=:]\s*(?:(?:bearer|basic)\s+)?)\S+'
    r'|(\b(?:access[_-]?token|refresh[_-]?token|api[_-]?key|password|secret|token|cookie|credentials?)\s*[=:]\s*)[^\s&,;]+')


def safe_details(value, depth=0):
    """Bound diagnostic data and remove common credential representations."""
    if depth > 8:
        return '[TRUNCATED]'
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k)[:100]: '[REDACTED]' if SENSITIVE.search(str(k)) else safe_details(v, depth + 1)
                for k, v in list(value.items())[:100]}
    if isinstance(value, (list, tuple)):
        return [safe_details(item, depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return SECRET_TEXT.sub(lambda m: (m[1] or m[2] or m[3]) + '[REDACTED]', value)[:2000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return '[UNSUPPORTED]'


def freshness(coverage_at, now, delayed_seconds=900, stale_seconds=1800):
    if delayed_seconds <= 0 or stale_seconds < delayed_seconds:
        raise ValueError('Freshness thresholds must satisfy 0 < delayed <= stale.')
    result = {'as_of': now, 'coverage_at': coverage_at, 'age_seconds': None,
              'delayed_seconds': delayed_seconds, 'stale_seconds': stale_seconds}
    if coverage_at is None:
        return {**result, 'status': 'UNAVAILABLE', 'reason': 'NO_CONFIRMED_DATA'}
    age = (now - coverage_at).total_seconds()
    if age < 0:
        return {**result, 'status': 'UNAVAILABLE', 'reason': 'FUTURE_WATERMARK'}
    status = 'STALE' if age > stale_seconds else 'DELAYED' if age > delayed_seconds else 'FRESH'
    return {**result, 'age_seconds': age, 'status': status,
            'reason': 'WITHIN_EXPECTATION' if status == 'FRESH' else 'EXPECTED_UPDATE_OVERDUE'}


def provider_health(rows, min_samples=3, min_connections=2, error_ratio=0.25, latency_ms=2000):
    eligible = [r for r in rows if r['outcome'] != 'AUTH_ERROR' and not (
        r['outcome'] == 'RATE_LIMIT' and r.get('quota_scope', 'PROVIDER') == 'CONNECTION')]
    count = len(eligible)
    connections = len({r['connection_id'] for r in eligible})
    failed = sum(r['outcome'] in {'PROVIDER_ERROR', 'TIMEOUT', 'CONNECTIVITY_ERROR'} for r in eligible)
    latencies = [r['latency_ms'] for r in eligible if r.get('latency_ms') is not None]
    average = sum(latencies) / len(latencies) if latencies else None
    return classify_provider(count, connections, failed, sum(r['outcome'] == 'RATE_LIMIT' for r in eligible),
                             average, min_samples, min_connections, error_ratio, latency_ms)


def classify_provider(count, connections, failed, limited, average,
                      min_samples=3, min_connections=2, error_ratio=0.25, latency_ms=2000):
    ratio = failed / count if count else None
    result = {'sample_count': count, 'error_rate': ratio, 'average_latency_ms': average}
    if count < min_samples or connections < min_connections:
        return {**result, 'status': 'UNKNOWN', 'reason': 'INSUFFICIENT_SCOPED_EVIDENCE'}
    if ratio >= 0.8:
        return {**result, 'status': 'UNAVAILABLE', 'reason': 'PROVIDER_REQUEST_FAILURES'}
    if ratio >= error_ratio or limited or (
            average is not None and average > latency_ms):
        return {**result, 'status': 'DEGRADED', 'reason': 'ERROR_LATENCY_OR_RATE_LIMIT'}
    return {**result, 'status': 'HEALTHY', 'reason': 'WITHIN_EXPECTATION'}
