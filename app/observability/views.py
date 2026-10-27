from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import FieldDoesNotExist, ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDay
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import (Business, FailedRecord, IntegrationConnection, IntegrationError,
                        IntegrationPayload, IntegrationSource, IntegrationSyncLog, MonitoringPolicy,
                        ObservabilityAudit, OperationAttempt, WebhookObservation)
from .access import require_access
from .lifecycle import transition_record
from .policies import safe_details
from .selectors import Policies, connection_snapshots, provider_snapshots, reliability_summary
from .serializers import (AttemptSerializer, ErrorSerializer, FailedRecordSerializer, LifecycleSerializer,
                          OperationSerializer, QuerySerializer, SyncSerializer, WebhookSerializer)
from .services import audit, timestamp


RESOURCES = {
    'syncs': (IntegrationSyncLog, SyncSerializer, 'integration_connection', 'started_at'),
    'failed-records': (FailedRecord, FailedRecordSerializer, 'connection', 'last_seen_at'),
    'webhooks': (WebhookObservation, WebhookSerializer, 'connection', 'received_at'),
    'errors': (IntegrationError, ErrorSerializer, 'connection', 'last_seen_at'),
}


class Pagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class BusinessView(APIView):
    permission_classes = [IsAuthenticated]

    def evaluation_time(self):
        return timezone.now()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_access(request.user, kwargs['business_id'], manage=request.method not in {'GET', 'HEAD', 'OPTIONS'})
        get_object_or_404(Business, pk=kwargs['business_id'])

    def handle_exception(self, exc):
        if isinstance(exc, DjangoValidationError):
            exc = ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return super().handle_exception(exc)

    def params(self, request, business_id):
        known = set(QuerySerializer().fields) | {'from', 'to'}
        unknown = set(request.query_params) - known
        if unknown:
            raise ValidationError({'query': f'Unsupported parameters: {sorted(unknown)}'})
        serializer = QuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for name in ('from', 'to'):
            if name in request.query_params:
                data[name] = timestamp(request.query_params[name], name)
        if 'from' in data and 'to' in data and data['from'] > data['to']:
            raise ValidationError('from must precede to.')
        if 'connection' in data and not IntegrationConnection.objects.filter(
                business_id=business_id, pk=data['connection']).exists():
            raise ValidationError('Connection does not belong to this business.')
        if data.get('scope') == 'global' and not request.user.is_superuser:
            raise PermissionDenied('Provider-wide diagnostics require superuser access.')
        return data

    def connections(self, business_id, params):
        query = IntegrationConnection.objects.filter(business_id=business_id).select_related('business', 'integration_source')
        if 'connection' in params:
            query = query.filter(pk=params['connection'])
        if 'provider' in params:
            query = query.filter(integration_source_id=params['provider'])
        if 'status' in params:
            if params['status'] not in {'CONNECTED', 'DISCONNECTED', 'DISABLED', 'EXPIRED', 'SYNCING', 'ERROR'}:
                raise ValidationError('Invalid connection lifecycle status.')
            query = query.filter(status=params['status'])
        for key, lookup in [('from', 'gte'), ('to', 'lte')]:
            if key in params:
                query = query.filter(**{f'created_at__{lookup}': params[key]})
        ordering = params.get('ordering', 'id')
        if ordering.lstrip('-') not in {'id', 'name', 'status', 'created_at', 'updated_at'}:
            raise ValidationError('Unsupported connection ordering.')
        return query.order_by(ordering, 'pk')

    def supported(self, params, resource):
        paging = {'page', 'page_size'}
        common = {'connection', 'provider', 'entity_type', 'status', 'ordering', 'from', 'to'}
        allowed = {'connections': {'connection', 'provider', 'status', 'ordering', 'from', 'to'},
                   'freshness': {'connection', 'provider', 'entity_type', 'status'},
                   'providers': {'provider', 'scope'},
                   'syncs': common | {'active', 'sync_type', 'trigger'},
                   'failed-records': common | {'stage', 'group_by'},
                   'webhooks': common,
                   'errors': common | {'category', 'severity', 'stage'}}[resource] | paging
        if set(params) - allowed:
            raise ValidationError('One or more filters are not supported for this resource.')

    def record_query(self, resource, business_id, params):
        self.supported(params, resource)
        model, _, connection_field, time_field = RESOURCES[resource]
        query = model.objects.filter(**{f'{connection_field}__business_id': business_id})
        if resource == 'webhooks':
            query = query.select_related('payload').defer('payload__body')
        for name, field in [('connection', f'{connection_field}_id'),
                            ('provider', f'{connection_field}__integration_source_id')]:
            if name in params:
                query = query.filter(**{field: params[name]})
        for name in ('entity_type', 'status', 'category', 'severity', 'stage', 'sync_type', 'trigger'):
            if name not in params:
                continue
            try:
                field = model._meta.get_field(name)
            except FieldDoesNotExist as exc:
                raise ValidationError(f'Filter {name} is not supported for {resource}.') from exc
            if field.choices and params[name] not in dict(field.choices):
                raise ValidationError({name: 'Unsupported value.'})
            if resource == 'syncs' and name == 'status' and params[name] not in {'PENDING', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED'}:
                raise ValidationError('Unsupported sync status.')
            query = query.filter(**{name: params[name]})
        if 'active' in params:
            query = query.filter(status__in=['PENDING', 'RUNNING']) if params['active'] == 'true' else query.exclude(status__in=['PENDING', 'RUNNING'])
        for key, lookup in [('from', 'gte'), ('to', 'lte')]:
            if key in params:
                query = query.filter(**{f'{time_field}__{lookup}': params[key]})
        ordering = params.get('ordering', '-id')
        if ordering.lstrip('-') not in {'id', time_field, 'status'}:
            raise ValidationError('Unsupported ordering.')
        return query.order_by(ordering, 'pk')

    def serialize(self, resource, row, business_id, now):
        serializer = RESOURCES[resource][1]
        return serializer(row, context={'now': now, 'policies': Policies(business_id)}).data


class CollectionView(BusinessView):
    def get(self, request, business_id, resource):
        params = self.params(request, business_id)
        self.supported(params, resource)
        now = timezone.now()
        pager = Pagination()
        if resource in {'connections', 'freshness'}:
            connection_params = {k: v for k, v in params.items() if resource == 'connections' or k in {'connection', 'provider'}}
            page = pager.paginate_queryset(self.connections(business_id, connection_params), request)
            data = connection_snapshots(page, now)
            if resource == 'freshness':
                data = [item for row in data for item in row['freshness']
                        if not params.get('entity_type') or item['entity_type'] == params['entity_type']]
                if 'status' in params:
                    if params['status'] not in {'FRESH', 'DELAYED', 'STALE', 'UNAVAILABLE'}:
                        raise ValidationError('Unsupported freshness status.')
                    data = [item for item in data if item['status'] == params['status']]
        elif resource == 'providers':
            query = IntegrationSource.objects.all() if params.get('scope') == 'global' else (
                IntegrationSource.objects.filter(integrationconnection__business_id=business_id).distinct())
            if 'provider' in params:
                query = query.filter(pk=params['provider'])
            page = pager.paginate_queryset(query.order_by('pk'), request)
            data = provider_snapshots(page, business_id, now, privileged=params.get('scope') == 'global')
        else:
            serializer = RESOURCES[resource][1]
            page = pager.paginate_queryset(self.record_query(resource, business_id, params), request)
            data = serializer(page, many=True, context={'now': now, 'policies': Policies(business_id)}).data
        return pager.get_paginated_response(data)


class DetailView(BusinessView):
    def get(self, request, business_id, resource, pk):
        params = self.params(request, business_id)
        if set(params) - ({'scope'} if resource == 'providers' else set()):
            raise ValidationError('Detail endpoints do not accept collection filters.')
        now = timezone.now()
        if resource == 'connections':
            row = get_object_or_404(self.connections(business_id, {}), pk=pk)
            return Response(connection_snapshots([row], now)[0])
        if resource == 'providers':
            query = IntegrationSource.objects.all() if params.get('scope') == 'global' else IntegrationSource.objects.filter(
                integrationconnection__business_id=business_id).distinct()
            row = get_object_or_404(query, pk=pk)
            return Response(provider_snapshots([row], business_id, now, privileged=params.get('scope') == 'global')[0])
        model, _, connection_field, _ = RESOURCES[resource]
        query = model.objects.filter(**{f'{connection_field}__business_id': business_id})
        if resource == 'webhooks':
            query = query.select_related('payload').defer('payload__body')
        row = get_object_or_404(query, pk=pk)
        data = dict(self.serialize(resource, row, business_id, now))
        connection_id = getattr(row, f'{connection_field}_id')
        action = {'syncs': 'sync_retry', 'failed-records': 'record_retry', 'webhooks': 'webhook_replay'}.get(resource)
        if action:
            attempts = OperationAttempt.objects.filter(connection_id=connection_id, action=action, target_id=pk).order_by('-pk')[:20]
            data['attempts'] = AttemptSerializer(attempts, many=True).data
        if resource == 'webhooks':
            data['deliveries'] = list(row.deliveries.order_by('-pk').values(
                'id', 'observation_id', 'received_at', 'validation', 'duplicate')[:20])
        target_type = {'errors': 'error', 'failed-records': 'failed_record', 'webhooks': 'webhook', 'syncs': 'sync'}[resource]
        data['history'] = list(ObservabilityAudit.objects.filter(business_id=business_id, target_type=target_type,
            target_id=pk).order_by('-pk').values('action', 'actor_id', 'from_status', 'to_status', 'note', 'created_at')[:20])
        return Response(safe_details(data))

    def patch(self, request, business_id, resource, pk):
        if resource not in {'errors', 'failed-records'}:
            return Response({'detail': 'Lifecycle updates are not supported for this resource.'}, status=405)
        serializer = LifecycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = transition_record(business_id, 'error' if resource == 'errors' else 'failed_record', pk,
                                actor=request.user, **serializer.validated_data)
        return Response(self.serialize(resource, row, business_id, timezone.now()))


class OperationView(BusinessView):
    def post(self, request, business_id, resource, pk, action):
        serializer = OperationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from .operations import execute_operation
        row = execute_operation(business_id, resource, pk, action, serializer.validated_data['idempotency_key'], request.user,
                                now=self.evaluation_time())
        return Response(AttemptSerializer(row).data, status=409 if row.status == 'UNSUPPORTED' else 200)


class SummaryView(BusinessView):
    def get(self, request, business_id):
        params = self.params(request, business_id)
        if set(params) - {'connection', 'provider', 'status', 'from', 'to'}:
            raise ValidationError('Unsupported summary filters.')
        return Response(reliability_summary(self.connections(business_id, params), timezone.now()))


class PolicyView(BusinessView):
    fields = ['connection_id', 'entity_type', 'delayed_seconds', 'stale_seconds', 'observation_ttl_seconds',
              'window_seconds', 'min_samples', 'min_connections', 'error_ratio', 'latency_ms',
              'max_retries', 'sync_timeout_seconds', 'enabled']

    def get(self, request, business_id):
        params = self.params(request, business_id)
        if set(params) - {'connection', 'entity_type', 'page', 'page_size'}:
            raise ValidationError('Unsupported policy filters.')
        query = MonitoringPolicy.objects.filter(business_id=business_id)
        for name, field in [('connection', 'connection_id'), ('entity_type', 'entity_type')]:
            if name in params:
                query = query.filter(**{field: params[name]})
        pager = Pagination()
        return pager.get_paginated_response(pager.paginate_queryset(query.order_by('pk').values(
            'id', 'updated_at', *self.fields), request))

    @transaction.atomic
    def put(self, request, business_id):
        if request.query_params:
            raise ValidationError('Policy writes do not accept query parameters.')
        if not isinstance(request.data, dict) or set(request.data) - set(self.fields):
            raise ValidationError('Unknown policy fields.')
        numeric = set(self.fields) - {'connection_id', 'entity_type', 'enabled', 'error_ratio'}
        if any(isinstance(request.data[name], bool) or not isinstance(request.data[name], int)
               for name in numeric & set(request.data)):
            raise ValidationError('Policy intervals and counts must be integers.')
        if 'enabled' in request.data and not isinstance(request.data['enabled'], bool):
            raise ValidationError('enabled must be boolean.')
        Business.objects.select_for_update(no_key=True).get(pk=business_id)
        connection_id = request.data.get('connection_id')
        if connection_id is not None and (isinstance(connection_id, bool) or not isinstance(connection_id, int) or
                not IntegrationConnection.objects.filter(pk=connection_id, business_id=business_id).exists()):
            raise ValidationError('Policy connection does not belong to this business.')
        entity_type = request.data.get('entity_type', '')
        if not isinstance(entity_type, str) or len(entity_type) > 100:
            raise ValidationError('Invalid entity type.')
        row = MonitoringPolicy.objects.filter(business_id=business_id, connection_id=connection_id,
                                              entity_type=entity_type).first()
        row = row or MonitoringPolicy(business_id=business_id, connection_id=connection_id, entity_type=entity_type)
        for name, value in request.data.items():
            setattr(row, name, value)
        row.updated_at = self.evaluation_time()
        row.full_clean()
        row.save()
        from app.configuration.services import record_native_change
        record_native_change(business_id, 'FRESHNESS', str(row.pk),
            MonitoringPolicy.objects.filter(pk=row.pk).values(*self.fields).get(), request.user, row.updated_at)
        return Response(dict(MonitoringPolicy.objects.filter(pk=row.pk).values('id', *self.fields).get()))


class PayloadDiagnosticView(BusinessView):
    def get(self, request, business_id, pk):
        require_access(request.user, business_id, manage=True)
        if request.query_params:
            raise ValidationError('Payload diagnostics do not accept query parameters.')
        row = get_object_or_404(IntegrationPayload.objects.select_related('connection'), pk=pk,
                                connection__business_id=business_id)
        audit(row.connection, 'payload', row.pk, 'DIAGNOSTIC_READ', actor=request.user)
        return Response({'id': row.pk, 'connection_id': row.connection_id, 'digest': row.digest,
            'received_at': row.received_at, 'source_at': row.source_at, 'signature_verified': row.signature_verified,
            'diagnostic_payload': safe_details(row.body)})


class GroupsView(BusinessView):
    def get(self, request, business_id):
        params = self.params(request, business_id)
        query = self.record_query('failed-records', business_id, params)
        group_by = params.get('group_by', 'code')
        groups = query.order_by().values(group_by).annotate(count=Count('id')).order_by('-count', group_by)
        pager = Pagination()
        return pager.get_paginated_response(pager.paginate_queryset(groups, request))


class StatisticsView(BusinessView):
    def get(self, request, business_id):
        params = self.params(request, business_id)
        query = self.record_query('syncs', business_id, params).order_by()
        zone_name = Business.objects.get(pk=business_id).timezone
        try:
            zone = ZoneInfo(zone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValidationError('The configured business timezone is invalid.') from exc
        duration = ExpressionWrapper(F('completed_at') - F('started_at'), output_field=DurationField())
        totals = query.aggregate(runs=Count('id'), failures=Count('id', filter=Q(status='FAILED')),
            partial=Count('id', filter=Q(status='PARTIAL')), average=Avg(duration))
        average = totals.pop('average')
        totals['average_duration_seconds'] = average.total_seconds() if average is not None else None
        daily = query.annotate(day=TruncDay('started_at', tzinfo=zone)).values('day').annotate(
            runs=Count('id'), failures=Count('id', filter=Q(status='FAILED')), average=Avg(duration)).order_by('-day')[:100]
        totals.update(timezone=zone_name, as_of=timezone.now(), daily=[{
            'day': item['day'], 'runs': item['runs'], 'failures': item['failures'],
            'average_duration_seconds': item['average'].total_seconds() if item['average'] is not None else None} for item in daily])
        return Response(totals)
