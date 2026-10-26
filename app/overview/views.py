from datetime import datetime, timedelta
from decimal import Decimal

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import AiRecommendation, Business, BusinessIssue, BusinessMetric
from app.observability.access import require_access
from app.observability.policies import safe_details
from app.observability.views import Pagination
from .activity import activity_data, activity_query
from .catalog import (CATALOG, DOMAINS, ISSUE_STATUSES, RECOMMENDATION_STATUSES, SEVERITIES, domain_for)
from .configuration import ConfigurationSerializer, configuration, save_configuration
from .cross_domain import cross_domain
from .evidence import ENTITIES, EvidenceProjection
from .findings import (issue_data, issues_query, recommendation_data, recommendations_query,
                       with_issue_evidence, with_recommendation_context)
from .health import health
from .metrics import MetricProjection
from .windows import aware_timestamp, window


def public(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        # Redaction also covers arbitrary nested action-preview keys.
        from app.observability.policies import SENSITIVE
        return {str(k): '[REDACTED]' if SENSITIVE.search(str(k)) else public(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [public(v) for v in value]
    return safe_details(value)


ALLOWED = {
    'summary': {'metric', 'period', 'dimension_type', 'dimension_value', 'from', 'to'},
    'kpis': {'metric', 'domain', 'period', 'dimension_type', 'dimension_value', 'from', 'to'},
    'trends': {'metric', 'domain', 'period', 'dimension_type', 'dimension_value', 'from', 'to'},
    'health': {'period', 'from', 'to'},
    'issues': {'status', 'severity', 'entity_type', 'entity_id', 'from', 'to', 'page', 'page_size'},
    'recommendations': {'status', 'priority', 'issue', 'from', 'to', 'page', 'page_size'},
    'activity': {'domain', 'entity_type', 'entity_id', 'severity', 'from', 'to', 'page', 'page_size'},
    'cross-domain': set(), 'configuration': set(), 'catalog': set(),
}


class BusinessView(APIView):
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_access(request.user, kwargs['business_id'], manage=request.method not in {'GET', 'HEAD', 'OPTIONS'})
        self.business = get_object_or_404(Business, pk=kwargs['business_id'])
        self.now = self.evaluation_time()
        self.config = configuration(self.business.pk)
        self.evidence = EvidenceProjection(self.business.pk, self.now)

    def evaluation_time(self):
        return timezone.now()

    def params(self, request, resource):
        unknown = set(request.query_params)-ALLOWED[resource]
        if unknown or any(len(request.query_params.getlist(k)) > 1 for k in request.query_params):
            raise ValidationError({'query': 'Unsupported or repeated query parameters.'})
        data = request.query_params.dict()
        if len(str(data)) > 5000:
            raise ValidationError('Query is too large.')
        for field in ('page', 'page_size', 'entity_id', 'issue'):
            if field in data:
                try:
                    data[field] = int(data[field])
                except (ValueError, TypeError):
                    raise ValidationError({field: 'Expected a positive integer.'})
                if data[field] < 1 or (field == 'page_size' and data[field] > 100):
                    raise ValidationError({field: 'Out of range.'})
        if ('dimension_type' in data) != ('dimension_value' in data):
            raise ValidationError('dimension_type and dimension_value must be supplied together.')
        if 'dimension_type' in data and (not data['dimension_type'] or len(data['dimension_type']) > 50 or not data['dimension_value'] or len(data['dimension_value']) > 255):
            raise ValidationError('Dimension fields are invalid.')
        if 'entity_id' in data and 'entity_type' not in data:
            raise ValidationError('entity_id requires entity_type.')
        choices = {'period': ['DAY', 'WEEK', 'MONTH'], 'priority': SEVERITIES, 'severity': SEVERITIES,
                   'domain': list(DOMAINS)+(['calling', 'issues', 'ai'] if resource == 'activity' else []),
                   'entity_type': list(ENTITIES)+['issue', 'recommendation']}
        if resource in {'issues', 'recommendations'}:
            choices['status'] = ISSUE_STATUSES if resource == 'issues' else RECOMMENDATION_STATUSES
        for field, options in choices.items():
            if field in data and data[field] not in options:
                raise ValidationError({field: 'Unsupported value.'})
        if ('from' in data) != ('to' in data):
            raise ValidationError('from and to must be supplied together.')
        for field in ('from', 'to'):
            if field in data:
                data[field] = aware_timestamp(data[field])
        if 'from' in data and (data['from'] >= data['to'] or data['to'] > self.now or data['to']-data['from'] > timedelta(days=366)):
            raise ValidationError('Window must be positive, at most 366 days, and not in the future.')
        if 'metric' in data:
            keys = data['metric'].split(',')
            known = set(CATALOG) | set(BusinessMetric.objects.filter(business=self.business, is_active=True).values_list('key', flat=True))
            if len(keys) > 50 or len(keys) != len(set(keys)) or set(keys)-known:
                raise ValidationError('Unknown, duplicate, or excessive metric keys.')
            data['metric'] = keys
        return data

    def paginated(self, query, request, transform):
        pager = Pagination()
        page = pager.paginate_queryset(query, request)
        self.evidence.prime_findings(page)
        response = pager.get_paginated_response([transform(row) for row in page])
        response.data['as_of'] = self.now
        response.data = public(response.data)
        return response


class CollectionView(BusinessView):
    def get(self, request, business_id, resource):
        params = self.params(request, resource)
        if resource == 'configuration':
            return Response(public(self.config))
        if resource == 'catalog':
            definitions = {m.key: m for m in BusinessMetric.objects.filter(business=self.business, is_active=True)}
            return Response(public({'results': [{'key': key, 'domain': domain_for(definitions[key]) if key in definitions else CATALOG[key],
                'name': definitions[key].name if key in definitions else key.replace('_', ' ').title(),
                'registered': key in definitions, 'selected': key in {r['key'] for r in self.config['kpis']}}
                for key in sorted(set(CATALOG) | set(definitions))]}))
        if resource == 'issues':
            query = with_issue_evidence(issues_query(business_id, params, self.now, self.config))
            return self.paginated(query, request, lambda r: issue_data(r, self.evidence, self.now))
        if resource == 'recommendations':
            query = with_recommendation_context(recommendations_query(business_id, params, self.now, self.config), business_id)
            return self.paginated(query, request, lambda r: recommendation_data(r, self.evidence, self.now))
        if resource == 'activity':
            return self.paginated(activity_query(business_id, params, self.now), request, lambda r: activity_data(r, business_id))
        if resource == 'cross-domain':
            return Response(public(cross_domain(self.business, self.config, self.evidence, self.now)))
        bounds = window(self.business, self.config, params, self.now)
        projection = MetricProjection(self.business, self.config, params, bounds, self.now)
        if resource == 'trends':
            return Response(public({**projection.trends(), 'window': bounds, 'as_of': self.now}))
        cards = projection.kpis()
        if resource == 'kpis':
            return Response(public({'results': cards, 'window': bounds, 'as_of': self.now}))
        # Summary display filters must never narrow the inputs used for business health.
        health_cards = cards if resource == 'health' or not any(k in params for k in ('metric', 'dimension_type')) else (
            MetricProjection(self.business, self.config, {k: v for k, v in params.items() if k in {'period', 'from', 'to'}}, bounds, self.now).kpis())
        state = health(self.business, self.config, health_cards, self.evidence, self.now)
        if resource == 'health':
            return Response(public({**state, 'window': bounds}))
        issue_rows = list(with_issue_evidence(issues_query(business_id, {}, self.now, self.config))[:10])
        rec_rows = list(with_recommendation_context(recommendations_query(business_id, {}, self.now, self.config), business_id)[:10])
        self.evidence.prime_findings(issue_rows + rec_rows)
        issues = [issue_data(r, self.evidence, self.now) for r in issue_rows]
        recommendations = [recommendation_data(r, self.evidence, self.now) for r in rec_rows]
        attention = [{'kind': 'ISSUE', 'id': r['id'], 'priority': 1 if r['severity'] == 'CRITICAL' else 2,
                      'title': r['title'], 'drilldown': r['drilldown']} for r in issues]
        attention += [{'kind': 'HEALTH_CHANGE', 'priority': 2, 'status': state['status'], 'trend': state['trend']}] if state['trend'] in {'DECLINING', 'MIXED'} else []
        attention += [{'kind': 'KPI_DEVIATION', 'priority': 3, 'key': r['key'], 'drilldown': r['drilldown']}
                      for r in cards if r['status'] == 'AVAILABLE' and r['comparison']['assessment'] == 'DECLINING']
        attention += [{'kind': 'RECOMMENDATION', 'id': r['id'], 'priority': 4, 'title': r['title'], 'drilldown': r['drilldown']}
                      for r in recommendations if r['priority'] in {'CRITICAL', 'HIGH'}]
        recent = [activity_data(r, business_id) for r in activity_query(business_id, {}, self.now)[:5]]
        attention += [{'kind': 'ACTIVITY', 'priority': 5, 'id': r['id'], 'drilldown': r['drilldown']}
                      for r in recent if r['severity'] in {'CRITICAL', 'HIGH'}]
        business_status = 'REQUIRES_ATTENTION' if state['status'] in {'CRITICAL', 'WARNING'} else (
            state['trend'] if state['trend'] in {'DECLINING', 'IMPROVING'} else state['status'])
        return Response(public({'business_id': business_id, 'as_of': self.now, 'window': bounds, 'business_status': business_status,
            'health': state, 'kpis': cards, 'issues': issues, 'recommendations': recommendations, 'recent_activity': recent,
            'attention': sorted(attention, key=lambda r: r['priority']),
            'summary': f"Business health is {state['status'].lower()}; {len(issues)} prominent active issues and {len(recommendations)} current recommendations shown.",
            'limits': {'issues': 10, 'recommendations': 10, 'recent_activity': 5},
            'links': {key: f'/api/businesses/{business_id}/overview/{key}/' for key in ALLOWED}}))


class ConfigurationView(CollectionView):
    def put(self, request, business_id, resource='configuration'):
        self.params(request, 'configuration')
        serializer = ConfigurationSerializer(data=request.data, context={'business_id': business_id})
        serializer.is_valid(raise_exception=True)
        return Response(public(save_configuration(business_id, request.user, serializer.validated_data, self.now)))


class DetailView(BusinessView):
    def get(self, request, business_id, resource, pk):
        if request.query_params:
            raise ValidationError('Detail endpoints do not accept query parameters.')
        if resource == 'issues':
            row = get_object_or_404(BusinessIssue, business_id=business_id, pk=pk,
                                    detected_at__lte=self.now, created_at__lte=self.now)
            data = issue_data(row, self.evidence, self.now, detail=True)
        elif resource == 'recommendations':
            row = get_object_or_404(AiRecommendation.objects.select_related('business_issue'), business_id=business_id,
                                    pk=pk, generated_at__lte=self.now, created_at__lte=self.now)
            data = recommendation_data(row, self.evidence, self.now, detail=True)
        else:
            data = self.evidence.detail(resource, pk)
        return Response(public({**data, 'as_of': self.now}))


class EntityView(BusinessView):
    def get(self, request, business_id, entity_type, pk):
        if request.query_params:
            raise ValidationError('Entity endpoints do not accept query parameters.')
        data = self.evidence.entity(entity_type, pk)
        if not data or not data['available']:
            raise Http404
        data = {**data, 'graph': self.evidence.graph_context(entity_type, pk), 'as_of': self.now}
        return Response(public(data))
