from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class IntegrationPayload(models.Model):
    """Protected immutable source material. Never serialized by observability APIs."""
    connection = models.ForeignKey('IntegrationConnection', models.PROTECT)
    key = models.CharField(max_length=200)
    body = models.JSONField()
    digest = models.CharField(max_length=64)
    signature_verified = models.BooleanField(default=False)
    received_at = models.DateTimeField(default=timezone.now)
    source_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Captured integration payloads are immutable.')
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'key'], name='integration_payload_key_unique')]
