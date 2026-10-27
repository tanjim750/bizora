from django.conf import settings
from django.db import models
from django.utils import timezone


KINDS = 'PROFILE GENERAL AI KNOWLEDGE RULE POLICY INTEGRATION SOURCE FRESHNESS'.split()
STATES = 'DRAFT ACTIVE DISABLED SUPERSEDED ARCHIVED'.split()


class ConfigurationRecord(models.Model):
    business = models.ForeignKey('app.Business', models.PROTECT)
    kind = models.CharField(max_length=20, choices=[(v, v) for v in KINDS])
    key = models.CharField(max_length=100)
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=15, choices=[(v, v) for v in STATES], default='ACTIVE')
    priority = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(null=True)
    valid_to = models.DateTimeField(null=True)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'business_configuration_records'
        constraints = [models.UniqueConstraint(fields=['business', 'kind', 'key'], name='configuration_record_key'),
                       models.CheckConstraint(check=models.Q(version__gt=0), name='configuration_version_positive')]
        indexes = [models.Index(fields=['business', 'kind', 'status'])]


class ConfigurationRevision(models.Model):
    record = models.ForeignKey(ConfigurationRecord, models.PROTECT, related_name='revisions')
    version = models.PositiveIntegerField()
    data = models.JSONField()
    status = models.CharField(max_length=15)
    priority = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(null=True)
    valid_to = models.DateTimeField(null=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, models.SET_NULL, null=True)
    reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'business_configuration_revisions'
        constraints = [models.UniqueConstraint(fields=['record', 'version'], name='configuration_revision_version')]


class ConfigurationEvent(models.Model):
    """Durable change notice for owners; never a claim of completed downstream processing."""
    business = models.ForeignKey('app.Business', models.PROTECT)
    section = models.CharField(max_length=20)
    key = models.CharField(max_length=100)
    version = models.PositiveIntegerField()
    dedupe_key = models.CharField(max_length=200, unique=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'business_configuration_events'
        indexes = [models.Index(fields=['business', '-created_at'])]


class KnowledgeReprocessingRequest(models.Model):
    business = models.ForeignKey('app.Business', models.PROTECT)
    key = models.CharField(max_length=100)
    source = models.ForeignKey('app.KnowledgeSource', models.PROTECT, null=True)
    document = models.ForeignKey('app.KnowledgeDocument', models.PROTECT, null=True)
    configuration_revision = models.ForeignKey(ConfigurationRevision, models.PROTECT)
    source_revision = models.ForeignKey(ConfigurationRevision, models.PROTECT, null=True, related_name='source_processing_requests')
    document_version = models.PositiveIntegerField(null=True)
    action = models.CharField(max_length=15, choices=[('REPROCESS', 'REPROCESS'), ('REEMBED', 'REEMBED')])
    status = models.CharField(max_length=15, default='REQUESTED')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'knowledge_reprocessing_requests'
        constraints = [models.UniqueConstraint(fields=['business', 'key'], name='knowledge_reprocessing_key')]
