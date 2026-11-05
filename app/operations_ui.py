"""Replaceable server-rendered UI. Canonical writes always use existing domain services."""
from decimal import Decimal
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from app import models as m, domain_views as api
from app.domains import data, identity, operations, projections
from app.domains.common import DomainError, authorize, related, require
from app.domains.registry import RESOURCES, scoped
from app.domains.states import TRANSITIONS
SECTIONS = {'overview': ('Business overview', None), 'customers': ('Customer 360', 'customers'), 'products': ('Product catalog', 'products'), 'orders': ('Order operations', 'orders'), 'payments': ('Payments & refunds', 'payments'), 'inbox': ('Unified inbox', 'conversations'), 'queue': ('Support queue', 'queue'), 'assignment': ('Conversation assignment', 'conversations'), 'handover': ('AI / human handover', 'conversations'), 'marketing': ('Marketing operations', 'campaigns'), 'website': ('Website observed data', 'visitors'), 'delivery': ('Delivery operations', 'shipments'), 'calls': ('Call operations', 'calls'), 'identity': ('Identity review', 'identity')}

def membership(request, business_id):
    member = get_object_or_404(m.BusinessMembership.objects.select_related('business'), business_id=business_id, user=request.user, is_active=True, user__is_active=True)
    authorize(request.user, member.business)
    return member

def filters_for(request, resource):
    names = {'conversations': ['channel', 'priority'], 'queue': ['channel', 'priority', 'assigned'], 'products': ['sku', 'category'], 'customers': ['contact', 'contact_type', 'tag'], 'orders': ['customer'], 'payments': ['customer', 'order', 'payment_method'], 'shipments': ['customer', 'order', 'provider'], 'calls': ['customer', 'order', 'direction'], 'campaigns': ['provider'], 'sessions': ['visitor', 'traffic_source', 'device_type'], 'website-events': ['visitor', 'session', 'event_type']}.get(resource, [])
    return [{'name': name, 'label': name.replace('_', ' ').title(), 'value': request.GET.get(name, '')} for name in names]

def context(member, **values):
    return {'business': member.business, 'member': member, 'can_write': member.role != 'VIEWER', 'can_manage': member.role in ('MANAGER', 'OWNER'), 'navigation': [(key, title) for key, (title, _) in SECTIONS.items() if key != 'identity' or member.role in ('MANAGER', 'OWNER')], **values}

def result_sections(payload):
    """Preserve projection truncation/fallback metadata while keeping record tables readable."""
    sections = []
    for key, value in payload.items():
        if isinstance(value, dict) and 'results' in value and isinstance(value['results'], list):
            sections.append({'title': key.replace('_', ' ').replace('-', ' ').title(), 'resource': key, 'rows': value['results'], 'count': value.get('count', len(value['results'])), 'truncated': value.get('truncated', False)})
        elif isinstance(value, dict):
            sections.append({'title': key.replace('_', ' ').title(), 'fields': value})
        else:
            sections.append({'title': key.replace('_', ' ').title(), 'value': value})
    return sections

def form_for(fields, identity):
    form = forms.Form(auto_id='id_'+identity+'_%s')
    form.fields = fields
    return form

def command_forms(member, name, record):
    if member.role == 'VIEWER':
        return []
    result = []

    def add(command, title, fields):
        result.append({'command': command, 'title': title, 'form': form_for(fields, command)})
    reason = lambda: forms.CharField(max_length=2000, widget=forms.Textarea(attrs={'rows': 2}))
    status = record.get('delivery_status') if name == 'messages' else record.get('status')
    choices = sorted(TRANSITIONS.get(name, {}).get(status, []))
    if choices:
        add('transition', 'Change recorded state (does not execute provider transport)', {'status': forms.ChoiceField(choices=[(x, x) for x in choices]), 'reason': reason()})
    if name == 'conversations':
        agents = m.BusinessMembership.objects.filter(business=member.business, is_active=True, user__is_active=True).exclude(role='VIEWER').select_related('user')
        add('assign', 'Assign or release', {'assignee_type': forms.ChoiceField(choices=[(x, x) for x in ['AGENT', 'TEAM', 'AI', 'UNASSIGNED']]), 'assignee_id': forms.IntegerField(required=False, min_value=1, help_text='Agent user ID or team ID; leave blank for AI/unassigned.'), 'reason': reason()})
        add('handover', 'Handover', {'target': forms.ChoiceField(choices=[('HUMAN', 'Human'), ('AI', 'AI handling state; engine unavailable')]), 'assignee_id': forms.IntegerField(required=False, min_value=1), 'reason': reason(), 'summary': forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))})
        add('priority', 'Set priority', {'priority': forms.ChoiceField(choices=[(x, x) for x in ['LOW', 'NORMAL', 'HIGH', 'URGENT']]), 'reason': reason()})
        add('note', 'Private internal note', {'content': forms.CharField(max_length=10000, widget=forms.Textarea(attrs={'rows': 3}))})
        add('reply', 'Save pending outgoing message (not sent)', {'content': forms.CharField(max_length=10000, widget=forms.Textarea(attrs={'rows': 3}))})
        add('media-reply', 'Save pending media reference (not sent)', {'attachment_type': forms.ChoiceField(choices=[(x,x) for x in ['IMAGE','VIDEO','AUDIO','FILE','OTHER']]), 'url': forms.URLField(), 'file_name': forms.CharField(required=False,max_length=255), 'mime_type': forms.CharField(required=False,max_length=100), 'size_bytes': forms.IntegerField(required=False,min_value=0)})
        result.append({'help': 'Available agents: ' + ', '.join((f'{x.user_id}: {x.user.get_username()}' for x in agents)) + '. Teams: ' + ', '.join((f'{x.pk}: {x.name}' for x in m.SupportTeam.objects.filter(business=member.business)))})
    if name == 'messages':
        add('read', 'Mark read', {})
    if name == 'products':
        add('add-variant', 'Add product variant', {'name': forms.CharField(max_length=255), 'sku': forms.CharField(max_length=100), 'price': forms.DecimalField(max_digits=18, decimal_places=2, min_value=0), 'inventory_quantity': forms.IntegerField(min_value=0)})
        add('map-product', 'Map reviewed external product source', {'connection_id': forms.IntegerField(min_value=1), 'external_product_id': forms.CharField(max_length=255)})
    if name == 'variants':
        add('variant', 'Edit variant', {'name': forms.CharField(required=False), 'price': forms.DecimalField(max_digits=18, decimal_places=2, min_value=0), 'inventory_quantity': forms.IntegerField(min_value=0)})
    if name == 'payments':
        add('refund', 'Record refund request', {'amount': forms.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal('0.01')), 'reason': reason()})
    if name == 'calls' and record.get('customer'):
        add('callback', 'Request callback', {'reason': reason(), 'scheduled_at': forms.DateTimeField(required=False, help_text='Future ISO timestamp with UTC offset, or blank for an unscheduled request.')})
    if name == 'callbacks':
        add('schedule', 'Schedule pending callback', {'scheduled_at': forms.DateTimeField(help_text='Future ISO timestamp with UTC offset.')})
    if name == 'actions' and member.role in ('MANAGER', 'OWNER'):
        add('review-action', 'Review proposed action (execution unavailable)', {'decision': forms.ChoiceField(choices=[('APPROVED', 'Approve proposal'), ('REJECTED', 'Reject proposal')]), 'reason': reason()})
    if name == 'conflicts':
        add('review-conflict', 'Review identity conflict', {'decision': forms.ChoiceField(choices=[(x, x) for x in ['REVIEWING', 'RESOLVED', 'IGNORED']]), 'reason': reason()})
    if name == 'merge-candidates':
        add('review-merge', 'Review candidate (does not merge)', {'decision': forms.ChoiceField(choices=[('APPROVED', 'Approve candidate'), ('REJECTED', 'Reject candidate')]), 'reason': reason()})
        add('merge-plan', 'Non-destructive merge dry-run', {})
    return result

@login_required(login_url='/ops/login/')
def index(request):
    members = m.BusinessMembership.objects.filter(user=request.user, is_active=True, user__is_active=True).select_related('business')
    return render(request, 'operations/index.html', {'members': members})

@login_required(login_url='/ops/login/')
def section(request, business_id, section):
    member = membership(request, business_id)
    request.GET = request.GET.copy()
    for key in list(request.GET):
        if request.GET[key] == '':
            del request.GET[key]
    if section not in SECTIONS:
        raise Http404
    title, name = SECTIONS[section]
    payload, error, rows, status = ({}, None, None, 200)
    if section == 'overview':
        payload = projections.overview(member.business)
    else:
        if name == 'identity':
            if member.role not in ('OWNER', 'MANAGER'):
                raise Http404
            response = api.IdentityView.as_view()(request, business_id=business_id, command='conflicts')
            payload = {'merge_candidates': projections.section(m.IdentityMergeCandidate.objects.filter(business=member.business)), 'identity_history': projections.section(m.IdentityHistory.objects.filter(business=member.business), ordering='-pk')}
        elif name == 'queue':
            response = api.SupportQueueView.as_view()(request, business_id=business_id)
        else:
            response = api.ResourceList.as_view()(request, business_id=business_id, name=name)
        if response.status_code >= 400:
            error, status = (response.data, response.status_code)
        else:
            rows = response.data
            if section == 'website':
                payload = {'sessions': projections.section(scoped('sessions', member.business)), 'events': projections.section(scoped('website-events', member.business))}
            if section == 'calls':
                payload = {'callback_requests': projections.section(scoped('callbacks', member.business))}
            if section == 'marketing':
                if member.role in ('OWNER', 'MANAGER'):
                    from app.domains.contracts import safe_records
                    payload['actions'] = projections.section(safe_records(m.AiAction.objects.filter(business=member.business), member.business))
                payload.update({'reported_metrics': projections.section(scoped('campaign-metrics', member.business)), 'reported_conversions': projections.section(scoped('conversions', member.business))})
    return render(request, 'operations/page.html', context(member, title=title, section=section, resource='conflicts' if name == 'identity' else 'conversations' if name == 'queue' else name, page=rows, sections=result_sections(payload), error=error, filters=filters_for(request, name), show_search=name in ('customers', 'products', 'orders', 'payments', 'conversations', 'campaigns', 'shipments', 'calls'), show_status=name not in (None, 'visitors')), status=status)

@login_required(login_url='/ops/login/')
def resources(request, business_id, name):
    member = membership(request, business_id)
    if name not in RESOURCES:
        raise Http404
    request.GET = request.GET.copy()
    for key in list(request.GET):
        if request.GET[key] == '':
            del request.GET[key]
    response = api.ResourceList.as_view()(request, business_id=business_id, name=name)
    return render(request, 'operations/page.html', context(member, title=name.replace('-', ' ').title(), resource=name, page=response.data if response.status_code < 400 else None, error=response.data if response.status_code >= 400 else None, filters=filters_for(request, name), show_search=any((f.name in ('name', 'display_name', 'subject', 'content', 'sku', 'order_number', 'tracking_code') for f in RESOURCES[name][0]._meta.fields)), show_status=any((f.name == 'status' for f in RESOURCES[name][0]._meta.fields))), status=response.status_code)

def owner_context(member, name, pk):
    from app.domains.boundaries import exchange
    kinds = {'customers': 'CUSTOMER', 'products': 'PRODUCT', 'orders': 'ORDER', 'payments': 'PAYMENT', 'conversations': 'CONVERSATION', 'campaigns': 'CAMPAIGN', 'visitors': 'VISITOR', 'sessions': 'SESSION', 'calls': 'CALL', 'shipments': 'SHIPMENT'}
    if name not in kinds:
        return {}
    outputs = {}
    for owner in getattr(settings, 'BIZORA_DOMAIN_ADAPTERS', {}):
        if owner in ('Business Intelligence', 'Business Graph', 'AI Intelligence'):
            capability, payload = ('entity_context', {'entity_type': kinds[name], 'entity_id': pk})
        elif owner == 'Business Memory':
            capability, payload = ('policy_context', {'query': 'Operational policies', 'entity_type': kinds[name], 'entity_id': pk})
        elif owner == 'Configuration':
            capability, payload = ('policy', {'policy_key': 'support-response'})
        elif owner == 'Monitoring':
            capability, payload = ('freshness', {'resource': name})
        else:
            continue
        outputs[owner] = exchange(member.business, member.user, owner, capability, payload, f'ui-{name}-{pk}-{capability}')
    return outputs

def load_detail(member, name, pk):
    if name in ('conflicts', 'merge-candidates', 'actions'):
        authorize(member.user, member.business, manager=True)
        model = {'conflicts': m.IdentityConflict, 'merge-candidates': m.IdentityMergeCandidate, 'actions': m.AiAction}[name]
        return {'record': projections.serialize(related(model, pk, member.business))}
    require(name in RESOURCES, 'NOT_FOUND', 'Unknown canonical resource.')
    if name == 'customers':
        result = projections.customer360(member.business, pk)
        result['record'] = result.pop('customer')
        result['external_owner_context'] = owner_context(member, name, pk)
        result['graph_context'] = projections.graph_context(member.business, 'CUSTOMER', pk)
        return result
    result = projections.detail(member.business, name, pk)
    result['external_owner_context'] = owner_context(member, name, pk)
    if name == 'conversations':
        result['support_context'] = projections.support_context(member.business, pk)
    if name in ('customers', 'products', 'orders'):
        result['graph_context'] = projections.graph_context(member.business, {'customers': 'CUSTOMER', 'products': 'PRODUCT', 'orders': 'ORDER'}[name], pk)
    return result

@login_required(login_url='/ops/login/')
def detail(request, business_id, name, pk):
    member = membership(request, business_id)
    try:
        payload = load_detail(member, name, pk)
        record = payload.pop('record')
        return render(request, 'operations/detail.html', context(member, title=f'{name.title()} #{pk}', resource=name, record=record, sections=result_sections(payload), commands=command_forms(member, name, record)))
    except (DomainError, ObjectDoesNotExist) as exc:
        return render(request, 'operations/page.html', context(member, title='Record unavailable', error=str(exc)), status=404)

@login_required(login_url='/ops/login/')
@require_POST
def command(request, business_id, name, pk, command):
    member = membership(request, business_id)
    try:
        authorize(request.user, member.business, write=True)
        payload = load_detail(member, name, pk)
        entry = next((x for x in command_forms(member, name, payload['record']) if x.get('command') == command), None)
        require(entry is not None, 'INVALID_COMMAND', 'This command is not available for the current record state.')
        form = entry['form']
        form.is_bound = True
        form.data = request.POST
        require(form.is_valid(), 'INVALID_FORM', form.errors.as_text())
        values = form.cleaned_data
        with transaction.atomic():
            if command == 'transition':
                data.transition(member.business, request.user, name, pk, expected_status=payload['record'].get('status', payload['record'].get('delivery_status')), **values)
            elif command == 'assign':
                operations.assign(member.business, request.user, pk, **values)
            elif command == 'handover':
                operations.handover(member.business, request.user, pk, **values)
            elif command == 'priority':
                operations.set_priority(member.business, request.user, pk, **values)
            elif command == 'variant':
                data.update_variant(member.business, request.user, pk, values)
            elif command == 'schedule':
                operations.schedule_callback(member.business, request.user, pk, **values)
            elif command == 'read':
                operations.mark_read(member.business, request.user, pk)
            elif command == 'review-action':
                operations.review_action(member.business, request.user, pk, **values)
            elif command == 'review-conflict':
                identity.review_conflict(member.business, request.user, pk, **values)
            elif command == 'review-merge':
                identity.review_merge(member.business, request.user, pk, **values)
            elif command == 'merge-plan':
                from app.domains.merge import dry_run
                plan = dry_run(member.business, request.user, pk)
                return render(request, 'operations/page.html', context(member, title='Merge dry-run — no records changed', sections=result_sections(plan)))
            else:
                token = request.POST.get('submission_id', '')
                require(len(token) == 32 and all((x in '0123456789abcdef' for x in token)), 'INVALID_KEY', 'Reload the page to obtain a submission identifier.')
                record = payload['record']
                source = record.get('integration_connection')
                if command == 'add-variant':
                    target, body = ('variants', {'product': pk, **values})
                elif command == 'map-product':
                    source = values.pop('connection_id')
                    target, body = ('product-references', {'product': pk, **values})
                elif command == 'note':
                    target, body = ('notes', {'conversation': pk, **values})
                elif command == 'media-reply':
                    attachment={key:value for key,value in values.items() if value not in (None,'')}
                    target,body='messages',{'conversation':pk,'external_message_id':'pending-ui-'+token,'direction':'OUTGOING','sender_type':'AGENT','message_type':attachment['attachment_type'],'attachments':[attachment]}
                elif command == 'reply':
                    target, body = ('messages', {'conversation': pk, 'external_message_id': 'pending-ui-' + token, 'direction': 'OUTGOING', 'sender_type': 'AGENT', **values})
                elif command == 'refund':
                    target, body = ('refunds', {'payment': pk, 'external_refund_id': 'ui-' + token, **values})
                elif command == 'callback':
                    values = {k: v for k, v in values.items() if v is not None}
                    target, body = ('callbacks', {'customer': record['customer'], 'order': record.get('order'), 'conversation': record.get('conversation'), **values})
                    source = None
                data.ingest(member.business, request.user, target, body, 'ui-' + token, connection_id=source)
        messages.success(request, 'Change saved. No external provider operation was executed.')
        return redirect('ops-detail', business_id=business_id, name=name, pk=pk)
    except (DomainError, ValidationError, ObjectDoesNotExist, ValueError) as exc:
        return render(request, 'operations/page.html', context(member, title='Command validation', error=str(exc)), status=403 if isinstance(exc, DomainError) and exc.code == 'FORBIDDEN' else 400)

@login_required(login_url='/ops/login/')
def financial_timeline(request, business_id):
    member = membership(request, business_id)
    request.GET = request.GET.copy()
    for key in list(request.GET):
        if request.GET[key] == '':
            del request.GET[key]
    response = api.FinancialTimelineView.as_view()(request, business_id=business_id)
    return render(request, 'operations/page.html', context(member, title='Financial timeline', resource='financial-timeline', page=response.data if response.status_code < 400 else None, error=response.data if response.status_code >= 400 else None, filters=filters_for(request, 'payments')[:2]), status=response.status_code)
