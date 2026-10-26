from copy import deepcopy
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException

from app.models import (Business, BusinessMetric, IntegrationConnection, MonitoringConfiguration,
                        MonitoringConfigurationRevision)
from app.observability.access import require_access
from .catalog import CATALOG, CROSS_DOMAIN, DEFAULT_KPIS, DOMAINS, SEVERITIES


DEFAULTS = {'period': 'DAY', 'snapshot_ttl_seconds': 172800, 'domains': list(DOMAINS),
            'kpis': [{'key': key, 'direction': 'NEUTRAL'} for key in DEFAULT_KPIS],
            'issue_severities': list(SEVERITIES), 'recommendation_priorities': list(SEVERITIES),
            'cross_domain': list(CROSS_DOMAIN)}


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError('Expected an object.')
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({'unknown': sorted(unknown)})
        return super().to_internal_value(data)


class SourceSerializer(StrictSerializer):
    connection_id = serializers.IntegerField(min_value=1)
    entity_type = serializers.RegexField(r'^[A-Z][A-Z0-9_]{0,99}$')


class KpiRuleSerializer(StrictSerializer):
    key = serializers.RegexField(r'^[a-zA-Z][a-zA-Z0-9_]{0,99}$')
    direction = serializers.ChoiceField(choices=['HIGHER', 'LOWER', 'NEUTRAL'], default='NEUTRAL')
    target_min = serializers.DecimalField(24, 6, required=False)
    target_max = serializers.DecimalField(24, 6, required=False)
    warning = serializers.DecimalField(24, 6, required=False)
    critical = serializers.DecimalField(24, 6, required=False)
    goal = serializers.CharField(max_length=255, required=False)
    sources = SourceSerializer(many=True, required=False, max_length=20)

    def validate(self, data):
        if 'target_min' in data and 'target_max' in data and data['target_min'] > data['target_max']:
            raise serializers.ValidationError('target_min must not exceed target_max.')
        if {'warning', 'critical'} & set(data) and data['direction'] == 'NEUTRAL':
            raise serializers.ValidationError('Thresholds require HIGHER or LOWER direction.')
        if 'warning' in data and 'critical' in data:
            valid = data['critical'] <= data['warning'] if data['direction'] == 'HIGHER' else data['critical'] >= data['warning']
            if not valid:
                raise serializers.ValidationError('Critical threshold must be at least as adverse as warning.')
        return data


class ConfigurationSerializer(StrictSerializer):
    version = serializers.IntegerField(min_value=0, required=False)
    period = serializers.ChoiceField(choices=['DAY', 'WEEK', 'MONTH'], required=False)
    snapshot_ttl_seconds = serializers.IntegerField(min_value=60, max_value=31536000, required=False)
    domains = serializers.ListField(child=serializers.ChoiceField(choices=DOMAINS), allow_empty=False, max_length=7, required=False)
    kpis = KpiRuleSerializer(many=True, max_length=50, required=False)
    issue_severities = serializers.ListField(child=serializers.ChoiceField(choices=SEVERITIES), max_length=5, required=False)
    recommendation_priorities = serializers.ListField(child=serializers.ChoiceField(choices=SEVERITIES), max_length=5, required=False)
    cross_domain = serializers.ListField(child=serializers.ChoiceField(choices=list(CROSS_DOMAIN)), max_length=9, required=False)

    def validate_kpis(self, data):
        business_id = self.context['business_id']
        keys = [row['key'] for row in data]
        if len(keys) != len(set(keys)):
            raise serializers.ValidationError('KPI keys must be unique.')
        known = set(CATALOG) | set(BusinessMetric.objects.filter(business_id=business_id, is_active=True).values_list('key', flat=True))
        if set(keys) - known:
            raise serializers.ValidationError('KPI must be registered in BI or the display catalog.')
        ids = {s['connection_id'] for row in data for s in row.get('sources', [])}
        if ids - set(IntegrationConnection.objects.filter(business_id=business_id, pk__in=ids).values_list('pk', flat=True)):
            raise serializers.ValidationError('Sources must belong to this business.')
        return data


def json_values(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: json_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_values(item) for item in value]
    return value


def configuration(business_id):
    row = MonitoringConfiguration.objects.filter(business_id=business_id).first()
    return {**deepcopy(DEFAULTS), **(row.settings if row else {}), 'version': row.version if row else 0,
            'updated_at': row.updated_at if row else None, 'updated_by_id': row.updated_by_id if row else None}


class ConfigurationConflict(APIException):
    status_code = 409
    default_detail = 'Configuration version changed. Read the current version and retry.'


@transaction.atomic
def save_configuration(business_id, actor, changes, now):
    require_access(actor, business_id, manage=True)
    # Lock the always-existing business, including the first configuration write.
    Business.objects.select_for_update().get(pk=business_id)
    row = MonitoringConfiguration.objects.filter(business_id=business_id).first()
    version = row.version if row else 0
    expected = changes.pop('version', None)
    if expected is not None and expected != version:
        raise ConfigurationConflict()
    settings = json_values({**deepcopy(DEFAULTS), **(row.settings if row else {}), **changes})
    row, _ = MonitoringConfiguration.objects.update_or_create(business_id=business_id,
        defaults={'settings': settings, 'version': version+1, 'updated_by': actor, 'updated_at': now})
    MonitoringConfigurationRevision.objects.create(business_id=business_id, version=row.version,
        settings=settings, actor=actor, created_at=now)
    return configuration(business_id)
