"""Business configuration contract; monitoring results remain read projections."""
from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone


class MonitoringConfiguration(models.Model):
    business = models.OneToOneField('app.Business', models.CASCADE, related_name='monitoring_configuration')
    settings = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, models.SET_NULL, null=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'monitoring_configurations'


class MonitoringConfigurationRevision(models.Model):
    business = models.ForeignKey('app.Business', models.CASCADE)
    version = models.PositiveIntegerField()
    settings = models.JSONField()
    actor = models.ForeignKey(django_settings.AUTH_USER_MODEL, models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'monitoring_configuration_revisions'
        constraints = [models.UniqueConstraint(fields=['business', 'version'], name='unique_monitoring_revision')]
