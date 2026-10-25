from rest_framework import serializers

from app.models import FailedRecord, IntegrationError, IntegrationSyncLog, OperationAttempt, WebhookObservation
from .policies import safe_details


class SafeSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        return safe_details(super().to_representation(instance))


class SyncSerializer(SafeSerializer):
    connection_id = serializers.IntegerField(source='integration_connection_id')
    duration_seconds = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    stalled = serializers.SerializerMethodField()
    metadata = serializers.SerializerMethodField()
    records_succeeded = serializers.SerializerMethodField()
    records_skipped = serializers.SerializerMethodField()

    def get_records_succeeded(self, row):
        return row.records_succeeded if row.counter_schema == 'V1' else None

    def get_records_skipped(self, row):
        return row.records_skipped if row.counter_schema == 'V1' else None

    def get_duration_seconds(self, row):
        if row.started_at is None:
            return None
        return max(0, ((row.completed_at or self.context['now']) - row.started_at).total_seconds())

    def get_progress_percent(self, row):
        return round(100 * row.records_processed / row.discovered, 2) if row.discovered else None

    def get_stalled(self, row):
        policy = self.context['policies'].get(row.integration_connection_id, row.entity_type)
        return row.status in {'PENDING', 'RUNNING'} and (
            self.context['now'] - row.last_observed_at).total_seconds() > policy.sync_timeout_seconds

    def get_metadata(self, row):
        metadata = row.metadata if isinstance(row.metadata, dict) else {}
        return {key: value for key, value in metadata.items()
                if key in {'correlation_id', 'reason', 'is_mock'}}

    class Meta:
        model = IntegrationSyncLog
        fields = ['id', 'connection_id', 'entity_type', 'sync_type', 'trigger', 'status', 'discovered',
                  'counter_schema',
                  'records_received', 'records_processed', 'records_succeeded', 'records_skipped',
                  'records_failed', 'started_at', 'completed_at', 'duration_seconds', 'progress_percent',
                  'stalled', 'cursor', 'parent_id', 'initiated_by_id', 'error_message', 'metadata', 'created_at']


class FailedRecordSerializer(SafeSerializer):
    class Meta:
        model = FailedRecord
        fields = ['id', 'connection_id', 'entity_type', 'external_id', 'stage', 'code', 'message',
                  'payload_id', 'sync_id', 'webhook_id', 'error_id', 'status', 'first_seen_at',
                  'last_seen_at', 'resolved_at', 'resolution', 'resolution_method']


class WebhookSerializer(SafeSerializer):
    transport_latency_seconds = serializers.SerializerMethodField()
    processing_latency_seconds = serializers.SerializerMethodField()
    latency_reason = serializers.SerializerMethodField()
    replay_eligible = serializers.SerializerMethodField()

    def get_transport_latency_seconds(self, row):
        if row.provider_event_at is None or row.provider_event_at > row.received_at:
            return None
        return (row.received_at - row.provider_event_at).total_seconds()

    def get_processing_latency_seconds(self, row):
        if row.processed_at is None or row.processed_at < row.received_at:
            return None
        return (row.processed_at - row.received_at).total_seconds()

    def get_latency_reason(self, row):
        if row.provider_event_at is None:
            return 'NO_PROVIDER_TIME'
        if row.provider_event_at > row.received_at or (row.processed_at and row.processed_at < row.received_at):
            return 'CLOCK_SKEW'
        return 'AVAILABLE'

    def get_replay_eligible(self, row):
        return row.validation == 'VALID' and row.status == 'FAILED' and bool(
            row.payload_id and row.payload.signature_verified)

    class Meta:
        model = WebhookObservation
        fields = ['id', 'connection_id', 'event_id', 'event_type', 'entity_type', 'validation', 'status',
                  'payload_id', 'provider_event_at', 'received_at', 'processed_at', 'delivery_count',
                  'transport_latency_seconds', 'processing_latency_seconds', 'latency_reason',
                  'error_id', 'replay_eligible']


class ErrorSerializer(SafeSerializer):
    class Meta:
        model = IntegrationError
        fields = ['id', 'connection_id', 'code', 'category', 'severity', 'entity_type', 'external_id',
                  'stage', 'message', 'details', 'sync_id', 'webhook_id', 'status', 'occurrences',
                  'first_seen_at', 'last_seen_at', 'resolved_at']


class AttemptSerializer(SafeSerializer):
    class Meta:
        model = OperationAttempt
        fields = ['id', 'action', 'target_id', 'status', 'actor_id', 'result', 'created_at',
                  'completed_at', 'next_retry_at']


class QuerySerializer(serializers.Serializer):
    connection = serializers.IntegerField(min_value=1, required=False)
    provider = serializers.IntegerField(min_value=1, required=False)
    entity_type = serializers.CharField(max_length=100, required=False)
    status = serializers.CharField(max_length=30, required=False)
    category = serializers.CharField(max_length=30, required=False)
    severity = serializers.ChoiceField(choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'], required=False)
    stage = serializers.CharField(max_length=30, required=False)
    sync_type = serializers.ChoiceField(choices=['FULL', 'INCREMENTAL'], required=False)
    trigger = serializers.ChoiceField(choices=['MANUAL', 'SCHEDULED', 'REPLAY', 'RETRY'], required=False)
    active = serializers.ChoiceField(choices=['true', 'false'], required=False)
    ordering = serializers.CharField(max_length=50, required=False)
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)
    scope = serializers.ChoiceField(choices=['business', 'global'], required=False)
    group_by = serializers.ChoiceField(choices=['code', 'stage', 'entity_type'], required=False)


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({'non_field_errors': ['Unknown request fields.']})
        return super().to_internal_value(data)


class LifecycleSerializer(StrictSerializer):
    status = serializers.CharField(max_length=20)
    note = serializers.CharField(max_length=2000, allow_blank=True, default='')


class OperationSerializer(StrictSerializer):
    idempotency_key = serializers.CharField(max_length=200)
