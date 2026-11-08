"""Typed configuration contracts. No expressions, executable imports, or raw secrets."""
import json
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from rest_framework import serializers

from app.models import Campaign, Customer, Product
from app.observability.policies import SECRET_TEXT, SENSITIVE
from app.overview.configuration import StrictSerializer


PERIODS = ['DAY', 'WEEK', 'MONTH', 'ROLLING_7D', 'ROLLING_30D']
TASKS = ['business_assistant', 'customer_support', 'marketing', 'summarization', 'recommendations']
CONTEXTS = ['profile', 'facts', 'metrics', 'issues', 'relationships', 'graph', 'approved_policies', 'knowledge', 'goals']
ACTIONS = ['CREATE_SUPPORT_DRAFT', 'PROPOSE_COURIER_CHANGE', 'PROPOSE_CAMPAIGN_CHANGE', 'CREATE_TASK']
KNOWLEDGE_TYPES = ['PROFILE', 'POLICY', 'PRODUCT', 'SUPPORT', 'BRAND', 'INTERNAL', 'GOALS', 'DECISIONS']
SOURCE_TYPES = ['MANUAL', 'UPLOAD', 'WEBSITE', 'INTEGRATION']
PLATFORM_GUARDRAILS = {'external_execution_requires_approval': True, 'ai_may_create_verified_facts': False,
                       'ai_may_create_authoritative_relationships': False, 'automatic_external_execution': False,
                       'evidence_required': True}


def ai_providers():
    return getattr(settings, 'BIZORA_AI_PROVIDERS', {'mock': {'models': ['mock-business', 'mock-support', 'mock-marketing', 'mock-summary', 'mock-recommendation']}})


def embedding_models():
    return getattr(settings, 'BIZORA_EMBEDDING_MODELS', ['mock-embedding'])


def bounded_json(value, depth=0):
    if depth > 5:
        raise serializers.ValidationError('Configuration nesting exceeds five levels.')
    if isinstance(value, dict):
        if len(value) > 50 or any(not isinstance(k, str) or len(k) > 100 or SENSITIVE.search(k) for k in value):
            raise serializers.ValidationError('Metadata contains invalid keys or credential fields.')
        for item in value.values():
            bounded_json(item, depth+1)
    elif isinstance(value, list):
        if len(value) > 50:
            raise serializers.ValidationError('Configuration lists are limited to 50 items.')
        for item in value:
            bounded_json(item, depth+1)
    elif isinstance(value, str):
        if len(value) > 2000 or SECRET_TEXT.search(value):
            raise serializers.ValidationError('Text is too long or contains a credential representation.')
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise serializers.ValidationError('Unsupported configuration value.')
    try:
        if len(json.dumps(value, allow_nan=False)) > 32000:
            raise serializers.ValidationError('Configuration data exceeds its size limit.')
    except (TypeError, ValueError):
        raise serializers.ValidationError('Configuration must be finite JSON data.')
    return value


class JsonObject(serializers.JSONField):
    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if not isinstance(data, dict):
            raise serializers.ValidationError('Expected an object.')
        return bounded_json(data)


def strings(maximum=50, allow_empty=True, required=False):
    return serializers.ListField(child=serializers.CharField(max_length=255), max_length=maximum, allow_empty=allow_empty, required=required)


class Contact(StrictSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)


class Location(StrictSerializer):
    country = serializers.RegexField(r'^[A-Z]{2}$', required=False)
    city = serializers.CharField(max_length=150, required=False, allow_blank=True)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)


def validate_timezone(value):
    try:
        ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError):
        raise serializers.ValidationError('Use a valid IANA timezone.')
    return value


class ProfileSchema(StrictSerializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=2000, allow_blank=True, required=False)
    industry = serializers.CharField(max_length=100, allow_blank=True, required=False)
    contact = Contact(required=False)
    location = Location(required=False)
    operating_regions = strings()
    channels = serializers.ListField(child=serializers.ChoiceField(choices=['WEBSITE', 'SOCIAL_COMMERCE', 'MARKETPLACE', 'PHYSICAL', 'DIRECT']), max_length=5, required=False)
    currency = serializers.RegexField(r'^[A-Z]{3}$')
    timezone = serializers.CharField(max_length=100, validators=[validate_timezone])
    metadata = JsonObject(required=False)


class OperationalDefaults(StrictSerializer):
    order_status = serializers.ChoiceField(choices=['PENDING', 'CONFIRMED'], required=False)
    conversation_priority = serializers.ChoiceField(choices=['LOW', 'NORMAL', 'HIGH'], required=False)
    delivery_region = serializers.CharField(max_length=100, required=False)


class FeaturePreferences(StrictSerializer):
    calling = serializers.BooleanField(required=False)
    marketing = serializers.BooleanField(required=False)
    website = serializers.BooleanField(required=False)
    support = serializers.BooleanField(required=False)
    delivery = serializers.BooleanField(required=False)
    graph = serializers.BooleanField(required=False)
    ai_recommendations = serializers.BooleanField(required=False)


class GeneralSchema(StrictSerializer):
    locale = serializers.RegexField(r'^[a-z]{2,3}(?:-[A-Z]{2})?$', required=False)
    language = serializers.RegexField(r'^[a-z]{2,3}(?:-[A-Z]{2})?$', required=False)
    timezone = serializers.CharField(max_length=100, validators=[validate_timezone])
    currency = serializers.RegexField(r'^[A-Z]{3}$')
    date_format = serializers.ChoiceField(choices=['YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY'], required=False)
    time_format = serializers.ChoiceField(choices=['12H', '24H'], required=False)
    decimal_places = serializers.IntegerField(min_value=0, max_value=6, required=False)
    decimal_separator = serializers.ChoiceField(choices=['.', ','], required=False)
    thousands_separator = serializers.ChoiceField(choices=['.', ',', ' ', ''], required=False)
    currency_display = serializers.ChoiceField(choices=['CODE', 'SYMBOL'], required=False)
    reporting_period = serializers.ChoiceField(choices=PERIODS, required=False)
    week_start = serializers.IntegerField(min_value=0, max_value=6, required=False)
    operational_defaults = OperationalDefaults(required=False)
    features = FeaturePreferences(required=False)
    metadata = JsonObject(required=False)

    def validate(self, data):
        if data.get('decimal_separator') == data.get('thousands_separator'):
            raise serializers.ValidationError('Decimal and thousands separators must differ.')
        return data


class Scope(StrictSerializer):
    product_id = serializers.IntegerField(min_value=1, required=False)
    campaign_id = serializers.IntegerField(min_value=1, required=False)
    customer_id = serializers.IntegerField(min_value=1, required=False)
    region = serializers.CharField(max_length=150, required=False)
    courier = serializers.CharField(max_length=100, required=False)
    channel = serializers.CharField(max_length=100, required=False)
    customer_type = serializers.CharField(max_length=50, required=False)
    category = serializers.CharField(max_length=100, required=False)

    def validate(self, data):
        for field, model in [('product_id', Product), ('campaign_id', Campaign), ('customer_id', Customer)]:
            if field in data and not model.objects.filter(pk=data[field], business_id=self.context['business_id']).exists():
                raise serializers.ValidationError({field: 'Entity does not belong to this business.'})
        return data


def decimal_scalar(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise serializers.ValidationError('Numeric conditions require a finite decimal value.')
    try:
        result = Decimal(str(value))
        if not result.is_finite() or abs(result) >= Decimal('1e18') or result.as_tuple().exponent < -6:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise serializers.ValidationError('Numeric value exceeds the supported decimal range.')
    return str(result)


class Condition(StrictSerializer):
    field = serializers.RegexField(r'^[a-zA-Z][a-zA-Z0-9_]{0,99}$')
    operator = serializers.ChoiceField(choices=['gt', 'gte', 'lt', 'lte', 'eq', 'ne', 'in', 'not_in'])
    value = serializers.JSONField()

    def validate(self, data):
        if data['operator'] in {'gt', 'gte', 'lt', 'lte'}:
            data['value'] = decimal_scalar(data['value'])
        elif data['operator'] in {'in', 'not_in'}:
            if not isinstance(data['value'], list) or not 0 < len(data['value']) <= 50 or any(isinstance(v, (dict, list)) for v in data['value']):
                raise serializers.ValidationError('Membership conditions require 1 to 50 scalar values.')
            bounded_json(data['value'])
        else:
            if isinstance(data['value'], (dict, list)):
                raise serializers.ValidationError('Equality conditions require scalar values.')
            bounded_json(data['value'])
        return data


class Conditions(StrictSerializer):
    all = Condition(many=True, max_length=30, allow_empty=False, required=False)
    any = Condition(many=True, max_length=30, allow_empty=False, required=False)

    def validate(self, data):
        if len(data) != 1:
            raise serializers.ValidationError('Supply exactly one all or any condition list.')
        return data


class Outcome(StrictSerializer):
    type = serializers.ChoiceField(choices=['CLASSIFY', 'ALERT', 'REQUIRE_APPROVAL'])
    code = serializers.RegexField(r'^[A-Z][A-Z0-9_]{0,99}$')
    severity = serializers.ChoiceField(choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])


class RuleSchema(StrictSerializer):
    category = serializers.ChoiceField(choices=['ORDERS', 'CUSTOMERS', 'DELIVERY', 'MARKETING', 'SUPPORT', 'PAYMENTS', 'INTELLIGENCE', 'WEBSITE'])
    conditions = Conditions()
    scope = Scope(required=False)
    sample_metric = serializers.RegexField(r'^[a-zA-Z][a-zA-Z0-9_]{0,99}$', required=False)
    min_samples = serializers.IntegerField(min_value=1, max_value=1000000000, required=False)
    window_days = serializers.IntegerField(min_value=1, max_value=366, required=False)
    outcome = Outcome()
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    def validate(self, data):
        if 'min_samples' in data and not data.get('sample_metric'):
            raise serializers.ValidationError('A minimum sample requires sample_metric.')
        return data


class AiFeatures(StrictSerializer):
    business_assistant = serializers.BooleanField(required=False)
    customer_support = serializers.BooleanField(required=False)
    marketing = serializers.BooleanField(required=False)
    summarization = serializers.BooleanField(required=False)
    recommendations = serializers.BooleanField(required=False)
    suggested_replies = serializers.BooleanField(required=False)


class ResponsePreferences(StrictSerializer):
    language = serializers.CharField(max_length=30, required=False)
    detail = serializers.ChoiceField(choices=['BRIEF', 'NORMAL', 'DETAILED'], required=False)
    tone = serializers.ChoiceField(choices=['PROFESSIONAL', 'FRIENDLY', 'FORMAL'], required=False)


class Escalation(StrictSerializer):
    on_low_confidence = serializers.BooleanField(required=False)
    topics = strings()


class Execution(StrictSerializer):
    approval_required = serializers.BooleanField(required=False)
    disabled_actions = serializers.ListField(child=serializers.ChoiceField(choices=ACTIONS), max_length=4, required=False)

    def validate_approval_required(self, value):
        if value is not True:
            raise serializers.ValidationError('Platform approval requirements cannot be disabled.')
        return value


class Parameters(StrictSerializer):
    temperature = serializers.DecimalField(3, 2, min_value=Decimal('0'), max_value=Decimal('2'), required=False)
    max_output_tokens = serializers.IntegerField(min_value=1, max_value=8192, required=False)


class AiWorkflow(StrictSerializer):
    enabled = serializers.BooleanField(required=False)
    context_categories = serializers.ListField(child=serializers.ChoiceField(choices=CONTEXTS), max_length=10, required=False)
    confidence_threshold = serializers.DecimalField(5, 4, min_value=Decimal('0'), max_value=Decimal('1'), required=False)
    allowed_actions = serializers.ListField(child=serializers.ChoiceField(choices=ACTIONS), max_length=4, required=False)
    response = ResponsePreferences(required=False)


class AiSchema(StrictSerializer):
    enabled = serializers.BooleanField()
    provider = serializers.CharField(max_length=50)
    models = serializers.DictField(child=serializers.CharField(max_length=150), required=False)
    features = AiFeatures(required=False)
    context_categories = serializers.ListField(child=serializers.ChoiceField(choices=CONTEXTS), max_length=10, required=False)
    response = ResponsePreferences(required=False)
    confidence_threshold = serializers.DecimalField(5, 4, min_value=Decimal('0'), max_value=Decimal('1'))
    escalation = Escalation(required=False)
    allowed_actions = serializers.ListField(child=serializers.ChoiceField(choices=ACTIONS), max_length=4, required=False)
    execution = Execution(required=False)
    parameters = Parameters(required=False)
    workflows = serializers.DictField(child=AiWorkflow(), required=False)

    def validate(self, data):
        providers = ai_providers()
        if data['provider'] not in providers:
            raise serializers.ValidationError('Provider is not enabled by this installation.')
        models = data.get('models', {})
        if set(models)-set(TASKS) or any(v not in providers[data['provider']]['models'] for v in models.values()):
            raise serializers.ValidationError('Task or model is not registered for this provider.')
        minimum = Decimal(str(getattr(settings, 'BIZORA_AI_MIN_CONFIDENCE', '0.6')))
        if data['confidence_threshold'] < minimum:
            raise serializers.ValidationError('Confidence threshold is below the platform minimum.')
        if data.get('escalation', {}).get('on_low_confidence') is False:
            raise serializers.ValidationError('Low-confidence escalation is mandatory.')
        workflows = data.get('workflows', {})
        if set(workflows)-set(TASKS):
            raise serializers.ValidationError('Unknown AI workflow.')
        for workflow in workflows.values():
            if set(workflow.get('context_categories', []))-set(data.get('context_categories', [])):
                raise serializers.ValidationError('Workflow context must be a subset of approved business context.')
            if set(workflow.get('allowed_actions', []))-set(data.get('allowed_actions', [])):
                raise serializers.ValidationError('Workflow actions must be a subset of business permissions.')
            if workflow.get('confidence_threshold', data['confidence_threshold']) < data['confidence_threshold']:
                raise serializers.ValidationError('Workflow confidence may only strengthen the business threshold.')
        return data


class Ingestion(StrictSerializer):
    allowed_types = serializers.ListField(child=serializers.ChoiceField(choices=SOURCE_TYPES), max_length=4)
    max_document_bytes = serializers.IntegerField(min_value=1024, max_value=52428800)


class Vector(StrictSerializer):
    enabled = serializers.BooleanField()
    limit = serializers.IntegerField(min_value=1, max_value=100)
    minimum_similarity = serializers.DecimalField(5, 4, min_value=Decimal('0'), max_value=Decimal('1'))


class Keyword(StrictSerializer):
    enabled = serializers.BooleanField()
    limit = serializers.IntegerField(min_value=1, max_value=100)


class Hybrid(StrictSerializer):
    enabled = serializers.BooleanField()
    vector_weight = serializers.DecimalField(5, 4, min_value=Decimal('0'), max_value=Decimal('1'))
    keyword_weight = serializers.DecimalField(5, 4, min_value=Decimal('0'), max_value=Decimal('1'))

    def validate(self, data):
        if data['vector_weight']+data['keyword_weight'] != 1:
            raise serializers.ValidationError('Hybrid weights must sum to one.')
        return data


class KnowledgeSchema(StrictSerializer):
    knowledge_types = serializers.ListField(child=serializers.ChoiceField(choices=KNOWLEDGE_TYPES), max_length=8)
    ingestion = Ingestion()
    chunk_size = serializers.IntegerField(min_value=100, max_value=8000)
    chunk_overlap = serializers.IntegerField(min_value=0, max_value=2000)
    embedding_model = serializers.CharField(max_length=150)
    vector = Vector()
    keyword = Keyword()
    hybrid = Hybrid()
    retrieval_limit = serializers.IntegerField(min_value=1, max_value=100)
    workflow_scopes = serializers.DictField(child=serializers.ListField(child=serializers.ChoiceField(choices=KNOWLEDGE_TYPES), max_length=8))
    include_archived_for_history = serializers.BooleanField()

    def validate(self, data):
        if data['chunk_overlap'] >= data['chunk_size']:
            raise serializers.ValidationError('Chunk overlap must be smaller than chunk size.')
        if data['embedding_model'] not in embedding_models():
            raise serializers.ValidationError('Embedding model is not registered by this installation.')
        if set(data['workflow_scopes'])-set(TASKS):
            raise serializers.ValidationError('Unknown retrieval workflow.')
        if any(set(v)-set(data['knowledge_types']) for v in data['workflow_scopes'].values()):
            raise serializers.ValidationError('Workflow scopes must use enabled knowledge categories.')
        if data['hybrid']['enabled'] and not (data['vector']['enabled'] and data['keyword']['enabled']):
            raise serializers.ValidationError('Hybrid retrieval requires vector and keyword retrieval.')
        return data


class PolicySchema(StrictSerializer):
    category = serializers.ChoiceField(choices=['DELIVERY', 'RETURN', 'REFUND', 'CANCELLATION', 'SUPPORT', 'PRODUCT'])
    title = serializers.CharField(max_length=255)
    terms = serializers.CharField(max_length=8000, allow_blank=True)
    scope = Scope(required=False)
    ai_available = serializers.BooleanField(required=False)
    parameters = serializers.DictField()

    def validate(self, data):
        schema = policy_parameters(data['category'])
        parsed = schema(data=data['parameters'], context=self.context, partial=self.context.get('status') != 'ACTIVE')
        parsed.is_valid(raise_exception=True)
        data['parameters'] = parsed.validated_data
        if self.context.get('status') == 'ACTIVE' and (not data['terms'].strip() or not data['parameters']):
            raise serializers.ValidationError('Active policies require terms and complete parameters.')
        return data


class DeliveryPolicy(StrictSerializer):
    coverage_regions = strings(allow_empty=False, required=True)
    estimated_days = serializers.IntegerField(min_value=0, max_value=366)
    charge = serializers.DecimalField(18, 2, min_value=Decimal('0'), required=False)
    preferred_couriers = strings()
    cod_enabled = serializers.BooleanField(required=False)
    cod_limit = serializers.DecimalField(18, 2, min_value=Decimal('0'), required=False)
    failure_instructions = serializers.CharField(max_length=2000, required=False)


class ReturnPolicy(StrictSerializer):
    window_days = serializers.IntegerField(min_value=0, max_value=366)
    eligibility = strings(allow_empty=False, required=True)
    exclusions = strings()
    procedure = serializers.CharField(max_length=2000)


class RefundPolicy(StrictSerializer):
    window_days = serializers.IntegerField(min_value=0, max_value=366)
    methods = strings(allow_empty=False, required=True)
    approval_required = serializers.BooleanField()
    eligibility = strings(allow_empty=False, required=True)
    procedure = serializers.CharField(max_length=2000)


class CancellationPolicy(StrictSerializer):
    allowed_statuses = strings(allow_empty=False, required=True)
    cutoff_hours = serializers.IntegerField(min_value=0, max_value=8760)
    procedure = serializers.CharField(max_length=2000)


class SupportPolicy(StrictSerializer):
    response_time_seconds = serializers.IntegerField(min_value=1, max_value=2592000)
    escalation_conditions = strings(allow_empty=False, required=True)
    instructions = serializers.CharField(max_length=2000)


class ProductPolicy(StrictSerializer):
    constraints = strings(allow_empty=False, required=True)
    instructions = serializers.CharField(max_length=2000)


def policy_parameters(category):
    return {'DELIVERY': DeliveryPolicy, 'RETURN': ReturnPolicy, 'REFUND': RefundPolicy,
            'CANCELLATION': CancellationPolicy, 'SUPPORT': SupportPolicy, 'PRODUCT': ProductPolicy}[category]


SCHEMAS = {'PROFILE': ProfileSchema, 'GENERAL': GeneralSchema, 'AI': AiSchema, 'KNOWLEDGE': KnowledgeSchema,
           'RULE': RuleSchema, 'POLICY': PolicySchema}
DEFAULTS = {
    'PROFILE': {'description': '', 'industry': '', 'contact': {}, 'location': {}, 'operating_regions': [], 'channels': [], 'metadata': {}},
    'GENERAL': {'locale': 'en', 'language': 'en', 'date_format': 'YYYY-MM-DD', 'time_format': '24H', 'decimal_places': 2,
        'decimal_separator': '.', 'thousands_separator': ',', 'currency_display': 'CODE', 'reporting_period': 'DAY',
        'week_start': 0, 'operational_defaults': {}, 'features': {}, 'metadata': {}},
    'AI': {'enabled': False, 'provider': 'mock', 'models': {}, 'features': {k: False for k in TASKS},
        'context_categories': ['profile', 'facts', 'approved_policies'], 'response': {'language': 'en', 'detail': 'NORMAL', 'tone': 'PROFESSIONAL'},
        'confidence_threshold': '0.7', 'escalation': {'on_low_confidence': True, 'topics': []}, 'allowed_actions': [],
        'execution': {'approval_required': True, 'disabled_actions': []}, 'parameters': {'temperature': '0.2', 'max_output_tokens': 1000}, 'workflows': {}},
    'KNOWLEDGE': {'knowledge_types': list(KNOWLEDGE_TYPES), 'ingestion': {'allowed_types': ['MANUAL', 'UPLOAD'], 'max_document_bytes': 10485760},
        'chunk_size': 500, 'chunk_overlap': 50, 'embedding_model': 'mock-embedding',
        'vector': {'enabled': True, 'limit': 10, 'minimum_similarity': '0.7'}, 'keyword': {'enabled': True, 'limit': 10},
        'hybrid': {'enabled': True, 'vector_weight': '0.6', 'keyword_weight': '0.4'}, 'retrieval_limit': 10,
        'workflow_scopes': {}, 'include_archived_for_history': False},
    'RULE': {'scope': {}}, 'POLICY': {'scope': {}, 'ai_available': False},
}


def defaults(kind, business):
    data = deepcopy(DEFAULTS.get(kind, {}))
    if kind in {'PROFILE', 'GENERAL'}:
        data.update(currency=business.currency, timezone=business.timezone)
        if kind == 'PROFILE':
            data['name'] = business.name
    return data
