from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from app import models as m
from app.domains.common import DomainError, require, authorize
from app.domains.registry import scoped, resource
from app.domains import data, identity, operations, projections
from app.serializers.domains import EventInputSerializer, TransitionSerializer, AssignmentSerializer, HandoverSerializer, IdentityCommandSerializer


class DomainPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class DomainAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def business(self, request, business_id, write=False, manager=False):
        # Lookup through membership first so inaccessible businesses are indistinguishable.
        membership = m.BusinessMembership.objects.select_related('business').filter(
            user=request.user, user__is_active=True, business_id=business_id, is_active=True).first()
        require(membership is not None, 'NOT_FOUND', 'Business not found.')
        authorize(request.user, membership.business, write=write, manager=manager)
        return membership.business

    def handle_exception(self, exc):
        if isinstance(exc, DomainError):
            status = 403 if exc.code == 'FORBIDDEN' else 404 if exc.code == 'NOT_FOUND' else 409 if exc.code in ('STALE_EVENT', 'STALE_STATE', 'IDEMPOTENCY_CONFLICT', 'HANDOVER_CONFLICT') else 400
            return Response({'code': exc.code, 'detail': exc.message}, status=status)
        if isinstance(exc, ObjectDoesNotExist):
            return Response({'code': 'NOT_FOUND', 'detail': 'Record not found.'}, status=404)
        if isinstance(exc, (DjangoValidationError, ValueError, TypeError)):
            return Response({'code': 'INVALID_DATA', 'detail': 'Invalid field value.'}, status=400)
        if isinstance(exc, IntegrityError):
            return Response({'code': 'CONSTRAINT_CONFLICT', 'detail': 'The operation conflicts with existing domain state.'}, status=409)
        return super().handle_exception(exc)

    def page(self, queryset, request):
        pager = DomainPagination()
        rows = pager.paginate_queryset(queryset, request, view=self)
        return pager.get_paginated_response([projections.serialize(x) for x in rows])

    @staticmethod
    def validated(serializer_class, request):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class ResourceList(DomainAPIView):
    def get(self, request, business_id, name):
        business = self.business(request, business_id)
        qs = scoped(name, business)
        fields = {f.name for f in qs.model._meta.fields}
        allowed = {'status', 'priority', 'channel', 'customer', 'order', 'product', 'campaign',
                   'conversation', 'direction', 'provider', 'platform', 'payment_method', 'category', 'sku', 'tag',
                   'visitor', 'session', 'payment', 'contact_type', 'assignee_type', 'traffic_source', 'traffic_medium', 'utm_campaign', 'device_type', 'browser', 'operating_system', 'event_type', 'is_anonymous'} & fields
        controls = {'page', 'page_size', 'q', 'since', 'until', 'contact', 'external_id', 'connection_id', 'ordering'}
        if name == 'customers':
            allowed |= {'tag', 'contact_type'}
        from app.domains.queries import lookup, conversation_search
        qs = lookup(name, business, qs, request.query_params)
        require(not (set(request.query_params) - allowed - controls), 'INVALID_FILTER', 'Unsupported filter.')
        for key in (allowed & set(request.query_params)) - ({'tag', 'contact_type'} if name == 'customers' else set()):
            qs = qs.filter(**{key: request.query_params[key]})
        if request.query_params.get('q'):
            search = Q()
            for field in ('name', 'display_name', 'sku', 'order_number', 'subject', 'tracking_code'):
                if field in fields:
                    search |= Q(**{field + '__icontains': request.query_params['q']})
            if name == 'conversations':
                qs = conversation_search(qs, business, request.query_params['q'])
            else:
                if 'content' in fields:
                    search |= Q(content__icontains=request.query_params['q'])
                require(bool(search), 'INVALID_FILTER', 'Search is unsupported for this resource.')
                qs = qs.filter(search)
        date_field = next((x for x in ('occurred_at', 'started_at', 'ordered_at', 'created_at') if x in fields), None)
        for param, op in [('since', 'gte'), ('until', 'lte')]:
            if param in request.query_params:
                value = parse_datetime(request.query_params[param])
                require(value is not None and timezone.is_aware(value) and date_field, 'INVALID_FILTER', 'Date filters require an ISO timestamp with offset.')
                qs = qs.filter(**{date_field + '__' + op: value})
        ordering = request.query_params.get('ordering', 'newest')
        require(ordering in ('newest', 'oldest'), 'INVALID_FILTER', 'Use newest or oldest ordering.')
        order_field = date_field or 'pk'
        return self.page(qs.order_by(('-' if ordering == 'newest' else '') + order_field, ('-' if ordering == 'newest' else '') + 'pk'), request)

    def post(self, request, business_id, name):
        business = self.business(request, business_id, write=True)
        values = self.validated(EventInputSerializer, request)
        obj, created = data.ingest(business, request.user, name, values.pop('data'),
             key=request.headers.get('Idempotency-Key'), **values)
        return Response(projections.serialize(obj), status=201 if created else 200)


class ResourceDetail(DomainAPIView):
    def get(self, request, business_id, name, pk):
        business = self.business(request, business_id)
        return Response(projections.detail(business, name, pk))


class TransitionView(DomainAPIView):
    def post(self, request, business_id, name, pk):
        business = self.business(request, business_id, write=True)
        obj = data.transition(business, request.user, name, pk, **self.validated(TransitionSerializer, request))
        return Response(projections.serialize(obj))


class OverviewView(DomainAPIView):
    def get(self, request, business_id):
        return Response(projections.overview(self.business(request, business_id)))


class Customer360View(DomainAPIView):
    def get(self, request, business_id, pk):
        return Response(projections.customer360(self.business(request, business_id), pk))


class SupportQueueView(DomainAPIView):
    def get(self, request, business_id):
        business = self.business(request, business_id)
        qs = scoped('conversations', business).filter(status__in=['OPEN', 'PENDING'])
        require(set(request.query_params) <= {'page', 'page_size', 'assigned', 'priority', 'status', 'channel'}, 'INVALID_FILTER', 'Unsupported queue filter.')
        for key in ('priority', 'status', 'channel'):
            if key in request.query_params:
                qs = qs.filter(**{key: request.query_params[key]})
        assigned = request.query_params.get('assigned')
        active = m.ConversationAssignment.objects.filter(status='ACTIVE', conversation__business=business)
        if assigned == 'me':
            qs = qs.filter(pk__in=active.filter(assignee_type='AGENT', assignee_id=request.user.pk).values('conversation_id'))
        elif assigned == 'unassigned':
            qs = qs.exclude(pk__in=active.values('conversation_id'))
        elif assigned == 'team':
            teams = m.SupportTeam.objects.filter(business=business, members=request.user)
            qs = qs.filter(pk__in=active.filter(assignee_type='TEAM', assignee_id__in=teams.values('pk')).values('conversation_id'))
        else:
            require(assigned is None, 'INVALID_FILTER', 'Invalid assignment filter.')
        # Stable priority order. No fabricated SLA or BI escalation thresholds.
        from django.db.models import Case, When, Value, IntegerField
        qs = qs.annotate(rank=Case(When(priority='URGENT', then=Value(0)), When(priority='HIGH', then=Value(1)), When(priority='NORMAL', then=Value(2)), default=Value(3), output_field=IntegerField()))
        response = self.page(qs.order_by('rank', 'started_at', 'pk'), request)
        response.data['capabilities'] = {'overdue_detection': operations.unavailable('Business Configuration: response/resolution policy'), 'ai_escalation': operations.unavailable('AI Intelligence'), 'analytical_queue_metrics': operations.unavailable('Business Intelligence')}
        return response


class AssignmentView(DomainAPIView):
    def post(self, request, business_id, pk):
        business = self.business(request, business_id, write=True)
        obj = operations.assign(business, request.user, pk, **self.validated(AssignmentSerializer, request))
        return Response(projections.serialize(obj) if obj else {'status': 'UNASSIGNED'})


class HandoverView(DomainAPIView):
    def post(self, request, business_id, pk):
        business = self.business(request, business_id, write=True)
        obj = operations.handover(business, request.user, pk, **self.validated(HandoverSerializer, request))
        return Response(projections.serialize(obj))


class IdentityView(DomainAPIView):
    TABLES = {'canonical': m.CanonicalIdentity, 'external': m.ExternalIdentity,
              'conflicts': m.IdentityConflict, 'merge-candidates': m.IdentityMergeCandidate, 'history': m.IdentityHistory}

    def get(self, request, business_id, command):
        business = self.business(request, business_id, manager=True)
        require(command in self.TABLES or command == 'links', 'NOT_FOUND', 'Unknown identity query.')
        qs = self.TABLES[command].objects.filter(business=business) if command in self.TABLES else m.IdentityLink.objects.filter(canonical_identity__business=business, external_identity__business=business)
        allowed = {'page', 'page_size', 'status', 'entity_type', 'canonical_identity', 'external_identity', 'rule_key'}
        require(set(request.query_params) <= allowed, 'INVALID_FILTER', 'Unsupported identity filter.')
        names = {f.name for f in qs.model._meta.fields}
        for key in (set(request.query_params) - {'page', 'page_size'}):
            require(key in names, 'INVALID_FILTER', 'Filter not supported for this identity query.')
            qs = qs.filter(**{key: request.query_params[key]})
        return self.page(qs.order_by('-pk'), request)

    def post(self, request, business_id, command):
        business = self.business(request, business_id, manager=True)
        v = self.validated(IdentityCommandSerializer, request)
        specs = {
            'set-status': (identity.set_status, ['canonical_identity_id', 'status', 'reason']),
            'enrich-external': (identity.enrich_external, ['external_identity_id', 'metadata', 'observed_at', 'reason']),
            'resolve-many': (identity.resolve_many, ['external_identity_ids']),
            'validate-links': (identity.validate_links, []),
            'identified-link': (identity.link_anonymous, ['visitor_id', 'identification_event_id', 'external_identity_id']),
            'canonical': (identity.canonical, ['entity_type', 'entity_id']),
            'register': (identity.register, ['connection_id', 'entity_type', 'identity_type', 'value', 'external_id']),
            'resolve': (identity.resolve, ['external_identity_id']),
            'link': (identity.link, ['external_identity_id', 'canonical_identity_id', 'reason']),
            'unlink': (identity.unlink, ['link_id', 'reason']),
            'verify-contact': (identity.verify_contact, ['contact_id', 'reason']),
            'anonymous-link': (identity.link_anonymous, ['visitor_id', 'purchase_event_id']),
            'detect-merges': (identity.detect_merges, []),
            'review-merge': (identity.review_merge, ['candidate_id', 'decision', 'reason']),
            'execute-merge': (identity.execute_merge, ['candidate_id']),
            'review-conflict': (identity.review_conflict, ['conflict_id', 'decision', 'reason']),
        }
        require(command in specs, 'NOT_FOUND', 'Unknown identity command.')
        fn, keys = specs[command]
        require(all(k in v for k in keys), 'INVALID_DATA', 'Required fields: ' + ', '.join(keys))
        args = [v[k] for k in keys]
        if command == 'register':
            result = fn(business, request.user, *args[:4], external_id=args[4], verified=v['verified'])
        elif command == 'enrich-external':
            result = fn(business, request.user, *args, verified=v.get('verification'))
        else:
            result = fn(business, request.user, *args)
        if isinstance(result, tuple):
            obj, conflict = result
            return Response({'result': projections.serialize(obj) if obj else None,
                             'conflict': projections.serialize(conflict) if conflict else None,
                             'status': 'CONFLICT' if conflict else 'RESOLVED' if obj else 'NO_MATCH'})
        if isinstance(result, list):
            return Response([projections.serialize(x) for x in result])
        return Response(result if isinstance(result, dict) else projections.serialize(result))


class ActionReviewView(DomainAPIView):
    def post(self, request, business_id, pk):
        business = self.business(request, business_id, manager=True)
        v = self.validated(IdentityCommandSerializer, request)
        require('decision' in v and 'reason' in v, 'INVALID_REVIEW', 'Decision and reason are required.')
        obj = operations.review_action(business, request.user, pk, v['decision'], v['reason'])
        return Response({'action': projections.serialize(obj), 'execution': operations.unavailable('AI / Integration execution contract')})


class MessageReadView(DomainAPIView):
    def post(self, request, business_id, pk):
        business = self.business(request, business_id, write=True)
        return Response(projections.serialize(operations.mark_read(business, request.user, pk)))


class WebsitePerformanceView(DomainAPIView):
    def get(self, request, business_id):
        business = self.business(request, business_id)
        return Response({
            'visitors': projections.section(scoped('visitors', business)),
            'sessions': projections.section(scoped('sessions', business)),
            'events': projections.section(scoped('website-events', business)),
            'intelligence': projections.authority_context(business),
            **{name: operations.unavailable('Business Intelligence') for name in
               ('traffic_source_performance', 'conversion_funnel', 'cart_abandonment', 'checkout_dropoff',
                'landing_page_performance', 'device_performance', 'experience_analysis')},
        })


class VariantUpdateView(DomainAPIView):
    def post(self, request, business_id, pk):
        from app.serializers.domains import VariantUpdateSerializer
        business = self.business(request, business_id, write=True)
        v = self.validated(VariantUpdateSerializer, request)
        return Response(projections.serialize(data.update_variant(business, request.user, pk, v['data'], v.get('expected_updated_at'))))


class FinancialTimelineView(DomainAPIView):
    def get(self, request, business_id):
        business = self.business(request, business_id)
        require(set(request.query_params) <= {'page', 'page_size', 'customer', 'order'}, 'INVALID_FILTER', 'Unsupported financial timeline filter.')
        filters = {key + '_id': int(request.query_params[key]) for key in ('customer', 'order') if key in request.query_params}
        pager = DomainPagination()
        rows = pager.paginate_queryset(projections.financial_timeline(business, **filters), request, view=self)
        return pager.get_paginated_response(list(rows))


class PriorityView(DomainAPIView):
    def post(self, request, business_id, pk):
        from app.serializers.domains import PrioritySerializer
        business = self.business(request, business_id, write=True)
        return Response(projections.serialize(operations.set_priority(business, request.user, pk,
                        **self.validated(PrioritySerializer, request))))


class SupportContextView(DomainAPIView):
    def get(self, request, business_id, pk):
        business = self.business(request, business_id)
        require(set(request.query_params) <= {'order'}, 'INVALID_FILTER', 'Only an optional order is supported.')
        order_id = int(request.query_params['order']) if 'order' in request.query_params else None
        return Response(projections.support_context(business, pk, order_id))


class JourneyView(DomainAPIView):
    def get(self, request, business_id, pk):
        from app.domains.common import related
        business = self.business(request, business_id)
        visitor = related(m.WebsiteVisitor, pk, business)
        return self.page(scoped('website-events', business).filter(visitor=visitor).order_by('occurred_at', 'pk'), request)


class RetargetingContextView(DomainAPIView):
    def get(self, request, business_id, pk):
        return Response(projections.retargeting_context(self.business(request, business_id), pk))


class OutboundPreparationView(DomainAPIView):
    def post(self, request, business_id, operation, pk):
        from app.domains.contracts import prepare_operation
        business = self.business(request, business_id, write=True)
        require(not request.data, 'INVALID_DATA', 'Outbound requests use canonical state; arbitrary overrides are prohibited.')
        return Response(prepare_operation(business, request.user, operation.upper(), pk))


class GraphContextView(DomainAPIView):
    def get(self, request, business_id, kind, pk):
        return Response(projections.graph_context(self.business(request, business_id), kind.upper(), pk))


class CallbackScheduleView(DomainAPIView):
    def post(self, request, business_id, pk):
        from rest_framework import serializers
        class ScheduleSerializer(serializers.Serializer):
            scheduled_at = serializers.DateTimeField()
        business = self.business(request, business_id, write=True)
        return Response(projections.serialize(operations.schedule_callback(business, request.user, pk,
                    **self.validated(ScheduleSerializer, request))))


class MergeDryRunView(DomainAPIView):
    def post(self,request,business_id,pk):
        from app.domains.merge import dry_run
        business=self.business(request,business_id,manager=True)
        require(isinstance(request.data,dict) and set(request.data)<={'expected_fingerprint'},'INVALID_CONTRACT','Only an optional expected_fingerprint is accepted; adapters cannot be supplied by clients.')
        return Response(dry_run(business,request.user,pk,expected_fingerprint=request.data.get('expected_fingerprint')))


class ProductAssessmentView(DomainAPIView):
    def post(self,request,business_id):
        from app.domains.catalog import assess_product
        from app.domains.common import related
        business=self.business(request,business_id,write=True)
        values=self.validated(EventInputSerializer,request)
        connection=related(m.IntegrationConnection,values['connection_id'],business) if values.get('connection_id') else None
        return Response(assess_product(business,request.user,values['data'],connection))


class DomainContractView(DomainAPIView):
    OWNERS={'integrations':'Integrations','bi':'Business Intelligence','graph':'Business Graph','ai':'AI Intelligence',
        'memory':'Business Memory','configuration':'Configuration','monitoring':'Monitoring'}

    def post(self,request,business_id,owner,capability):
        from app.domains.boundaries import exchange
        business=self.business(request,business_id,write=owner=='integrations')
        require(owner in self.OWNERS and capability!='prepare_merge','UNSUPPORTED_CONTRACT','Use the scoped merge dry-run for merge reconciliation.')
        require(isinstance(request.data,dict) and set(request.data)=={'request_id','payload'},'INVALID_CONTRACT','Provide request_id and payload only.')
        return Response(exchange(business,request.user,self.OWNERS[owner],capability,request.data['payload'],request.data['request_id']))
