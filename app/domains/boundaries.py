"""Versioned, process-local seams for external domain owners; no transport is supplied."""
import json
from copy import deepcopy
from typing import Protocol
from django.conf import settings
from django.utils.module_loading import import_string
from app.domains.common import authorize, require, related
VERSION = 'bizora.domain.v1'
CAPABILITIES = {'Integrations': {'prepare_operation': ('operation', 'entity_type', 'entity_id')}, 'Business Intelligence': {'entity_context': ('entity_type', 'entity_id')}, 'Business Graph': {'entity_context': ('entity_type', 'entity_id')}, 'AI Intelligence': {'entity_context': ('entity_type', 'entity_id')}, 'Business Memory': {'policy_context': ('query',)}, 'Configuration': {'policy': ('policy_key',)}, 'Monitoring': {'freshness': ('resource',)}}
MERGE_OWNERS = tuple(CAPABILITIES)
OUTPUTS = {'Integrations': {'request': dict, 'execution': str}, 'Business Intelligence': {'facts': list, 'metrics': list, 'issues': list, 'evidence': list}, 'Business Graph': {'nodes': list, 'edges': list}, 'AI Intelligence': {'recommendations': list, 'answers': list, 'evidence': list}, 'Business Memory': {'policies': list}, 'Configuration': {'policy': dict}, 'Monitoring': {'freshness': dict}}

def validate_scope(value, business, depth=0):
    require(depth <= 20, 'INVALID_CONTRACT', 'Contract nesting exceeds 20 levels.')
    if isinstance(value, dict):
        if 'business_id' in value:
            require(type(value['business_id']) is int and value['business_id'] == business.pk, 'CONTRACT_MISMATCH', 'Nested business scope differs.')
        if 'entity_type' in value and 'entity_id' in value:
            from .identity import ENTITY_MODELS
            from app import models as m
            reference_models={**ENTITY_MODELS,'MESSAGE':m.Message}
            require(value['entity_type'] in reference_models, 'INVALID_ENTITY', 'Unsupported typed entity reference.')
            related(reference_models[value['entity_type']], value['entity_id'], business)
        for child in value.values():
            validate_scope(child, business, depth + 1)
    elif isinstance(value, list):
        require(len(value) <= 1000, 'INVALID_CONTRACT', 'Contract lists are bounded to 1000 entries.')
        for child in value:
            validate_scope(child, business, depth + 1)

class Adapter(Protocol):

    def exchange(self, envelope: dict) -> dict:
        ...

def configured_adapter(owner):
    path = getattr(settings, 'BIZORA_DOMAIN_ADAPTERS', {}).get(owner)
    if not path:
        return None
    adapter = import_string(path)()
    require(callable(getattr(adapter, 'exchange', None)), 'INVALID_ADAPTER', 'Configured adapter must implement exchange.')
    require(not getattr(adapter, 'simulated', False) or getattr(settings, 'BIZORA_ALLOW_FIXTURE_ADAPTERS', False), 'INVALID_ADAPTER', 'Fixture adapters require explicit local/test configuration.')
    return adapter

class FixtureAdapter:
    """Explicit fixture-only adapter, injected by tests/local demonstrations, never registered live."""
    simulated = True

    def __init__(self, result=None, status='AVAILABLE'):
        self.result, self.status = (result or {}, status)

    def exchange(self, envelope):
        return {key: deepcopy(envelope[key]) for key in ('version', 'business_id', 'owner', 'capability', 'request_id')} | {'status': self.status, 'result': deepcopy(self.result), 'simulated': True}

def exchange(business, actor, owner, capability, payload, request_id, adapter=None):
    authorize(actor, business)
    require(owner in CAPABILITIES and (capability in CAPABILITIES[owner] or capability == 'prepare_merge'), 'UNSUPPORTED_CONTRACT', 'Unknown domain capability.')
    required = ('plan_id', 'fingerprint', 'source_identity_id', 'target_identity_id') if capability == 'prepare_merge' else CAPABILITIES[owner][capability]
    if capability == 'prepare_merge':
        authorize(actor, business, manager=True)
    require(isinstance(payload, dict) and all((k in payload and payload[k] is not None for k in required)), 'INVALID_CONTRACT', 'Required input fields: ' + ', '.join(required))
    for key in required:
        if key.endswith('_id') and key != 'plan_id':
            require(type(payload[key]) is int and payload[key] > 0, 'INVALID_CONTRACT', key + ' must be a positive integer.')
        else:
            require(isinstance(payload[key], str) and 0 < len(payload[key].strip()) <= 2000, 'INVALID_CONTRACT', key + ' must be nonempty text, max 2000 characters.')
    require(isinstance(request_id, str) and 0 < len(request_id) <= 180, 'INVALID_KEY', 'Stable request ID required.')
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError):
        require(False, 'INVALID_CONTRACT', 'Payload must be finite JSON.')
    if 'entity_type' in payload and capability != 'prepare_merge':
        from .identity import ENTITY_MODELS
        from app import models as m
        reference_models={**ENTITY_MODELS, 'MESSAGE': m.Message}
        require(payload['entity_type'] in reference_models and 'entity_id' in payload, 'INVALID_ENTITY', 'A supported entity type and ID are required.')
        related(reference_models[payload['entity_type']], payload['entity_id'], business)
    if owner=='Integrations' and capability=='prepare_operation':
        from .contracts import prepare_operation
        expected={'MESSAGE_SEND':'MESSAGE','CALL_INITIATE':'CALL','SHIPMENT_SUBMIT':'SHIPMENT','SHIPMENT_CANCEL':'SHIPMENT'}
        require(set(payload)=={'operation','entity_type','entity_id'} and expected.get(payload['operation'])==payload['entity_type'],
            'INVALID_CONTRACT','Operation must match its canonical entity type; payload overrides are prohibited.')
        payload=prepare_operation(business,actor,payload['operation'],payload['entity_id'])['request']
    if capability == 'prepare_merge':
        from app import models as m
        for key in ('source_identity_id', 'target_identity_id'):
            related(m.CanonicalIdentity, payload[key], business)
    envelope = {'version': VERSION, 'business_id': business.pk, 'owner': owner, 'capability': capability, 'request_id': request_id, 'payload': deepcopy(payload)}
    if adapter is None:
        adapter = configured_adapter(owner)
    if adapter is None:
        return {key: envelope[key] for key in ('version', 'business_id', 'owner', 'capability', 'request_id')} | {'status': 'UNAVAILABLE', 'result': None, 'simulated': False, 'reason': 'No owner adapter is configured.'}
    try:
        response = adapter.exchange(deepcopy(envelope))
    except (TimeoutError, ConnectionError, OSError):
        return {key: envelope[key] for key in ('version', 'business_id', 'owner', 'capability', 'request_id')} | {'status': 'UNAVAILABLE', 'result': None, 'simulated': bool(getattr(adapter, 'simulated', False)), 'reason': 'Owner adapter is temporarily unavailable.'}
    require(isinstance(response, dict) and type(response.get('business_id')) is int and all((response.get(k) == envelope[k] for k in ('version', 'business_id', 'owner', 'capability', 'request_id'))), 'CONTRACT_MISMATCH', 'Adapter response scope/version/request identity differs.')
    require(response.get('status') in ('AVAILABLE', 'REJECTED', 'UNAVAILABLE') and isinstance(response.get('simulated'), bool), 'INVALID_CONTRACT', 'Response requires explicit status and simulation provenance.')
    require(response['status'] != 'AVAILABLE' or isinstance(response.get('result'), dict), 'INVALID_CONTRACT', 'Available results must be objects.')
    if response['status'] == 'AVAILABLE' and capability != 'prepare_merge':
        require(all((isinstance(response['result'].get(key), kind) for key, kind in OUTPUTS[owner].items())), 'INVALID_CONTRACT', 'Available result does not satisfy the owner output schema.')
        if owner == 'Integrations':
            require(response['result']['execution'] == 'NOT_EXECUTED', 'INVALID_CONTRACT', 'Preparation must not claim provider execution.')
    validate_scope(response.get('result'), business)
    require(not getattr(adapter, 'simulated', False) or response['simulated'], 'INVALID_CONTRACT', 'Fixture results must remain labelled simulated.')
    try:
        json.dumps(response, allow_nan=False)
    except (TypeError, ValueError):
        require(False, 'INVALID_CONTRACT', 'Response must be finite JSON.')
    return deepcopy(response)
