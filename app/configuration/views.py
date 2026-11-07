from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import Business, ConfigurationEvent, ConfigurationRecord
from app.observability.access import require_access
from app.observability.views import Pagination
from .presentation import public
from .schemas import PLATFORM_GUARDRAILS, Scope, TASKS
from .services import record_data, revision_data, save_record, section_data


SECTIONS = {'profile': 'PROFILE', 'general': 'GENERAL', 'ai': 'AI', 'knowledge': 'KNOWLEDGE',
            'rules': 'RULE', 'policies': 'POLICY', 'connections': 'INTEGRATION', 'sources': 'SOURCE', 'freshness': 'FRESHNESS'}


class BusinessView(APIView):
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_access(request.user, kwargs['business_id'], manage=request.method not in {'GET', 'HEAD', 'OPTIONS'})
        self.business = get_object_or_404(Business, pk=kwargs['business_id'])
        self.now = self.evaluation_time()

    def evaluation_time(self):
        return timezone.now()

    def params(self, request, allowed=()):
        if set(request.query_params)-set(allowed) or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params):
            raise ValidationError('Unsupported or repeated query parameters.')
        params = request.query_params.dict()
        for key in ('page', 'page_size'):
            if key in params:
                try:
                    params[key] = int(params[key])
                except (ValueError, TypeError):
                    raise ValidationError('Invalid page value.')
                if params[key] < 1 or (key == 'page_size' and params[key] > 100):
                    raise ValidationError('Page value is out of range.')
        return params

    def page(self, request, query, transform, record_kind=None):
        pager = Pagination()
        rows = pager.paginate_queryset(query, request)
        if record_kind:
            records = {r.key: r for r in ConfigurationRecord.objects.filter(business=self.business,
                kind=record_kind, key__in=[str(row.pk) for row in rows])}
            data = [transform(row, records.get(str(row.pk))) for row in rows]
        else:
            data = [transform(row) for row in rows]
        response = pager.get_paginated_response(data)
        response.data = public(response.data)
        return response


class SectionView(BusinessView):
    def get(self, request, business_id, section):
        self.params(request)
        return Response(public(section_data(self.business, SECTIONS[section])))

    def put(self, request, business_id, section):
        self.params(request)
        record = save_record(business_id, SECTIONS[section], 'default', request.data, request.user, now=self.now)
        return Response(public(record_data(record)))


class ResourceView(BusinessView):
    def get(self, request, business_id, section, key=None):
        kind = SECTIONS[section]
        if key is not None:
            self.params(request)
            return Response(public(record_data(get_object_or_404(ConfigurationRecord, business_id=business_id, kind=kind, key=key))))
        params = self.params(request, ('status', 'page', 'page_size'))
        query = ConfigurationRecord.objects.filter(business_id=business_id, kind=kind)
        if 'status' in params:
            from .models import STATES
            if params['status'] not in STATES:
                raise ValidationError('Unsupported state.')
            query = query.filter(status=params['status'])
        return self.page(request, query.order_by('-priority', 'key'), record_data)

    def post(self, request, business_id, section):
        self.params(request)
        import re
        key = request.data.get('key') if isinstance(request.data, dict) else None
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,99}', key):
            raise ValidationError('A stable lowercase configuration key is required.')
        record = save_record(business_id, SECTIONS[section], key, request.data, request.user, now=self.now, create=True)
        return Response(public(record_data(record)), status=201)

    def patch(self, request, business_id, section, key):
        self.params(request)
        record = save_record(business_id, SECTIONS[section], key, request.data, request.user, now=self.now)
        return Response(public(record_data(record)))


class HistoryView(BusinessView):
    def get(self, request, business_id, section, key='default', pk=None):
        self.params(request, ('page', 'page_size'))
        record = get_object_or_404(ConfigurationRecord, business_id=business_id, kind=SECTIONS[section], key=str(pk) if pk else key)
        return self.page(request, record.revisions.select_related('record').order_by('-version'), revision_data)


class ChangesView(BusinessView):
    def get(self, request, business_id):
        self.params(request, ('page', 'page_size'))
        query = ConfigurationEvent.objects.filter(business_id=business_id).order_by('-created_at', '-pk')
        return self.page(request, query, lambda r: {'id': r.pk, 'section': r.section, 'key': r.key,
            'version': r.version, 'actor_id': r.actor_id, 'created_at': r.created_at, 'delivery_state': 'AVAILABLE_FOR_CONSUMERS'})


class EffectiveView(BusinessView):
    def get(self, request, business_id):
        params = self.params(request, set(Scope().fields) | {'workflow', 'historical'})
        workflow = params.pop('workflow', None)
        if workflow is not None and workflow not in TASKS:
            raise ValidationError('Unknown workflow.')
        historical = params.pop('historical', 'false')
        if historical not in {'true', 'false'}:
            raise ValidationError('historical must be true or false.')
        scope = Scope(data=params, context={'business_id': business_id})
        scope.is_valid(raise_exception=True)
        from .selectors import (ai_configuration, approved_sources, effective_policies, effective_rules, knowledge_configuration)
        sections = {name: section_data(self.business, kind) for name, kind in SECTIONS.items()
                    if kind in {'PROFILE', 'GENERAL', 'AI', 'KNOWLEDGE'}}
        sections['ai']['settings'] = ai_configuration(business_id, workflow)
        sections['knowledge']['settings'] = knowledge_configuration(business_id, workflow, historical == 'true')
        return Response(public({'business_id': business_id, 'as_of': self.now,
            'sections': sections, 'rules': effective_rules(business_id, scope=scope.validated_data, at=self.now),
            'policies': effective_policies(business_id, scope=scope.validated_data, at=self.now),
            'approved_sources': approved_sources(business_id, workflow, self.now, historical == 'true'),
            'guardrails': PLATFORM_GUARDRAILS}))


class ProvidersView(BusinessView):
    def get(self, request, business_id):
        self.params(request, ('page', 'page_size'))
        from app.models import IntegrationSource
        from .integrations import capabilities
        return self.page(request, IntegrationSource.objects.filter(is_active=True).order_by('key'),
            lambda r: {'id': r.pk, 'key': r.key, 'name': r.name, 'category': r.category,
                       'capabilities': capabilities(r), 'mock_supported': True})


class ConnectionsView(BusinessView):
    def get(self, request, business_id, pk=None):
        from app.models import IntegrationConnection
        from .integrations import connection_data
        query = IntegrationConnection.objects.filter(business_id=business_id).select_related('integration_source')
        if pk is not None:
            self.params(request)
            return Response(public(connection_data(get_object_or_404(query, pk=pk))))
        self.params(request, ('page', 'page_size'))
        return self.page(request, query.order_by('pk'), connection_data, record_kind='INTEGRATION')

    def post(self, request, business_id):
        self.params(request)
        from .integrations import connection_data, save_connection
        return Response(public(connection_data(save_connection(business_id, request.user, request.data, self.now))), status=201)

    def patch(self, request, business_id, pk):
        self.params(request)
        from .integrations import connection_data, save_connection
        return Response(public(connection_data(save_connection(business_id, request.user, request.data, self.now, pk))))


class SourcesView(BusinessView):
    def get(self, request, business_id, pk=None):
        from app.models import KnowledgeSource
        from .knowledge import source_data
        query = KnowledgeSource.objects.filter(business_id=business_id)
        if pk is not None:
            self.params(request)
            return Response(public(source_data(get_object_or_404(query, pk=pk))))
        self.params(request, ('page', 'page_size'))
        return self.page(request, query.order_by('pk'), source_data, record_kind='SOURCE')

    def post(self, request, business_id):
        self.params(request)
        from .knowledge import save_source, source_data
        return Response(public(source_data(save_source(business_id, request.user, request.data, self.now))), status=201)

    def patch(self, request, business_id, pk):
        self.params(request)
        from .knowledge import save_source, source_data
        return Response(public(source_data(save_source(business_id, request.user, request.data, self.now, pk))))


class ReprocessingView(BusinessView):
    def get(self, request, business_id):
        self.params(request, ('page', 'page_size'))
        from app.models import KnowledgeReprocessingRequest
        from .knowledge import reprocessing_data
        return self.page(request, KnowledgeReprocessingRequest.objects.filter(business_id=business_id).order_by('-pk'), reprocessing_data)

    def post(self, request, business_id):
        self.params(request)
        from .knowledge import request_reprocessing, reprocessing_data
        row, created = request_reprocessing(business_id, request.user, request.data, self.now)
        return Response(public(reprocessing_data(row)), status=201 if created else 200)


class MonitoringHistoryView(BusinessView):
    def get(self, request, business_id):
        self.params(request, ('page', 'page_size'))
        from app.models import MonitoringConfigurationRevision
        query = MonitoringConfigurationRevision.objects.filter(business_id=business_id).order_by('-version')
        return self.page(request, query, lambda r: {'version': r.version, 'settings': r.settings,
            'actor_id': r.actor_id, 'created_at': r.created_at})
