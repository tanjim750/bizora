"""Persisted observations. Canonical business records remain in their owning models."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def options(values):
    return [(value, value) for value in values.split()]


class BusinessAccess(models.Model):
    business = models.ForeignKey('Business', models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE)
    role = models.CharField(max_length=10, choices=options('READER MANAGER'))

    class Meta:
        constraints = [models.UniqueConstraint(fields=['business', 'user'], name='obs_business_user_unique')]


class MonitoringPolicy(models.Model):
    business = models.ForeignKey('Business', models.PROTECT)
    connection = models.ForeignKey('IntegrationConnection', models.PROTECT, null=True, blank=True)
    entity_type = models.CharField(max_length=100, blank=True, default='')
    delayed_seconds = models.PositiveIntegerField(default=900)
    stale_seconds = models.PositiveIntegerField(default=1800)
    observation_ttl_seconds = models.PositiveIntegerField(default=3600)
    window_seconds = models.PositiveIntegerField(default=900)
    min_samples = models.PositiveIntegerField(default=3)
    min_connections = models.PositiveIntegerField(default=2)
    error_ratio = models.FloatField(default=0.25)
    latency_ms = models.PositiveIntegerField(default=2000)
    max_retries = models.PositiveIntegerField(default=3)
    sync_timeout_seconds = models.PositiveIntegerField(default=3600)
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        super().clean()
        if self.connection_id and self.connection.business_id != self.business_id:
            raise ValidationError('Policy connection belongs to another business.')
        if not 0 < self.delayed_seconds <= self.stale_seconds:
            raise ValidationError('Thresholds must satisfy 0 < delayed <= stale.')
        if not 0 < self.error_ratio <= 1:
            raise ValidationError('Error ratio must be in (0, 1].')
        for field in ('observation_ttl_seconds', 'window_seconds', 'min_samples', 'min_connections',
                      'max_retries', 'sync_timeout_seconds', 'latency_ms'):
            if getattr(self, field) <= 0:
                raise ValidationError({field: 'Must be positive.'})

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['business', 'connection', 'entity_type'], name='obs_policy_connection_unique'),
            models.UniqueConstraint(fields=['business', 'entity_type'], condition=models.Q(connection__isnull=True),
                                    name='obs_policy_business_unique'),
            models.CheckConstraint(check=models.Q(delayed_seconds__gt=0, stale_seconds__gte=models.F('delayed_seconds')),
                                   name='obs_policy_thresholds'),
            models.CheckConstraint(check=models.Q(error_ratio__gt=0, error_ratio__lte=1), name='obs_policy_ratio'),
            models.CheckConstraint(check=models.Q(window_seconds__gt=0, min_samples__gt=0, min_connections__gt=0,
                observation_ttl_seconds__gt=0, max_retries__gt=0, sync_timeout_seconds__gt=0, latency_ms__gt=0),
                                   name='obs_policy_positive'),
        ]


class ScopedRecord(models.Model):
    business = models.ForeignKey('Business', models.PROTECT)
    connection = models.ForeignKey('IntegrationConnection', models.PROTECT)

    class Meta:
        abstract = True


class ObservationReceipt(ScopedRecord):
    key = models.CharField(max_length=200)
    kind = models.CharField(max_length=50)
    digest = models.CharField(max_length=64)
    observed_at = models.DateTimeField()
    received_at = models.DateTimeField()
    object_id = models.PositiveBigIntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'key'], name='obs_receipt_unique')]
        indexes = [models.Index(fields=['business', 'kind', 'observed_at'])]


class ConnectionCheck(ScopedRecord):
    observation = models.OneToOneField(ObservationReceipt, models.PROTECT)
    outcome = models.CharField(max_length=30, choices=options('SUCCESS DEGRADED ERROR AUTH_ERROR EXPIRED'))
    authentication = models.CharField(max_length=20, choices=options('USABLE INVALID EXPIRED UNKNOWN'), default='UNKNOWN')
    credential_status = models.CharField(max_length=20, choices=options('USABLE INVALID EXPIRED UNKNOWN'), default='UNKNOWN')
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    code = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    observed_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=['connection', '-observed_at', '-id'])]


class ProviderRequest(ScopedRecord):
    observation = models.OneToOneField(ObservationReceipt, models.PROTECT)
    capability = models.CharField(max_length=100, default='default')
    target = models.CharField(max_length=200, default='GLOBAL')
    outcome = models.CharField(max_length=30, choices=options(
        'SUCCESS AUTH_ERROR RATE_LIMIT TIMEOUT PROVIDER_ERROR CONNECTIVITY_ERROR'))
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    rate_limit_remaining = models.PositiveIntegerField(null=True, blank=True)
    retry_after_seconds = models.PositiveIntegerField(null=True, blank=True)
    quota_scope = models.CharField(max_length=20, choices=options('CONNECTION PROVIDER'), default='CONNECTION')
    observed_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=['connection', 'observed_at']),
                   models.Index(fields=['capability', 'target', 'observed_at'])]
        constraints = [models.CheckConstraint(check=models.Q(http_status__isnull=True) |
            models.Q(http_status__gte=100, http_status__lte=599), name='obs_http_status_valid')]


class IntegrationError(ScopedRecord):
    fingerprint = models.CharField(max_length=64)
    code = models.CharField(max_length=100)
    category = models.CharField(max_length=30, choices=options(
        'AUTHENTICATION CONNECTIVITY PROVIDER_API RATE_LIMIT WEBHOOK SYNC MAPPING NORMALIZATION VALIDATION INTERNAL'))
    severity = models.CharField(max_length=10, choices=options('LOW MEDIUM HIGH CRITICAL'), default='MEDIUM')
    entity_type = models.CharField(max_length=100, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    stage = models.CharField(max_length=30, blank=True)
    message = models.TextField()
    details = models.JSONField(default=dict)
    sync = models.ForeignKey('IntegrationSyncLog', models.PROTECT, null=True, blank=True)
    webhook = models.ForeignKey('WebhookObservation', models.PROTECT, null=True, blank=True, related_name='linked_errors')
    status = models.CharField(max_length=15, choices=options('ACTIVE ACKNOWLEDGED RESOLVED IGNORED'), default='ACTIVE')
    occurrences = models.PositiveIntegerField(default=1)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'fingerprint'], name='obs_error_unique'),
                       models.CheckConstraint(check=models.Q(occurrences__gt=0), name='obs_error_occurrences_positive')]
        indexes = [models.Index(fields=['business', 'status', '-last_seen_at'])]


class WebhookObservation(ScopedRecord):
    event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100, blank=True)
    validation = models.CharField(max_length=10, choices=options('UNKNOWN VALID INVALID'), default='UNKNOWN')
    status = models.CharField(max_length=15, choices=options('RECEIVED ROUTING PROCESSED FAILED REJECTED'), default='RECEIVED')
    payload = models.ForeignKey('IntegrationPayload', models.PROTECT, null=True, blank=True)
    provider_event_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
    last_observed_at = models.DateTimeField()
    delivery_count = models.PositiveIntegerField(default=1)
    error = models.ForeignKey(IntegrationError, models.PROTECT, null=True, blank=True, related_name='failed_webhooks')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'event_id'], name='obs_webhook_event_unique')]
        indexes = [models.Index(fields=['business', 'status', '-received_at'])]


class WebhookDelivery(models.Model):
    webhook = models.ForeignKey(WebhookObservation, models.PROTECT, related_name='deliveries')
    observation = models.OneToOneField(ObservationReceipt, models.PROTECT)
    received_at = models.DateTimeField()
    validation = models.CharField(max_length=10)
    duplicate = models.BooleanField(default=False)


class FailedRecord(ScopedRecord):
    fingerprint = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=100)
    external_id = models.CharField(max_length=255)
    stage = models.CharField(max_length=30, choices=options(
        'RETRIEVAL MAPPING NORMALIZATION VALIDATION IDENTITY_INPUT PERSISTENCE ROUTING'))
    code = models.CharField(max_length=100)
    message = models.TextField()
    payload = models.ForeignKey('IntegrationPayload', models.PROTECT, null=True, blank=True)
    sync = models.ForeignKey('IntegrationSyncLog', models.PROTECT, null=True, blank=True)
    webhook = models.ForeignKey(WebhookObservation, models.PROTECT, null=True, blank=True)
    error = models.ForeignKey(IntegrationError, models.PROTECT)
    status = models.CharField(max_length=15, choices=options('OPEN REVIEWING RETRYING RESOLVED IGNORED'), default='OPEN')
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True)
    resolution_method = models.CharField(max_length=20, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'fingerprint'], name='obs_failed_record_unique')]
        indexes = [models.Index(fields=['business', 'status', '-last_seen_at'])]


class SourceFreshness(ScopedRecord):
    entity_type = models.CharField(max_length=100)
    coverage_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    complete = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'entity_type'], name='obs_freshness_unique')]


class OperationAttempt(ScopedRecord):
    key = models.CharField(max_length=200)
    action = models.CharField(max_length=30)
    target_id = models.PositiveBigIntegerField()
    status = models.CharField(max_length=15, choices=options('RUNNING SUCCEEDED FAILED UNSUPPORTED'))
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, models.SET_NULL, null=True)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'key'], name='obs_operation_unique')]
        indexes = [models.Index(fields=['connection', 'action', 'target_id'])]


class ObservabilityAudit(ScopedRecord):
    target_type = models.CharField(max_length=30)
    target_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=30)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, models.SET_NULL, null=True)
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=['business', 'target_type', 'target_id'])]
