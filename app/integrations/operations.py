"""Provider-operation boundary. Live adapters can be registered by integration owners."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from django.core.exceptions import ValidationError

from app.business_data.products import confirm_product, persist_product


class UnsupportedOperation(Exception):
    pass


class ProcessingFailure(Exception):
    def __init__(self, code, stage, message, recoverable=True):
        self.code, self.stage, self.message, self.recoverable = code, stage, message, recoverable
        super().__init__(message)


@dataclass(frozen=True)
class CheckResult:
    outcome: str
    latency_ms: int | None = None
    code: str = ''
    message: str = ''


@dataclass(frozen=True)
class ProcessingResult:
    entity_type: str
    external_id: str
    canonical_id: int
    source_at: datetime
    original_received_at: datetime
    skipped: bool = False


class IntegrationOperations(Protocol):
    def test_connection(self) -> CheckResult: ...
    def process(self, payload, entity_type, now) -> ProcessingResult: ...
    def confirm_processing(self, result: ProcessingResult) -> bool: ...


class MockIntegrationOperations:
    def __init__(self, connection):
        self.connection = connection
        config = connection.config or {}
        self.config = config.get('mock', {}) if isinstance(config, dict) else {}
        if not isinstance(self.config, dict):
            raise ValidationError('Mock provider settings must be an object.')

    def test_connection(self):
        return CheckResult(self.config.get('connection_outcome', 'SUCCESS'), 5)

    def confirm_processing(self, result):
        return confirm_product(self.connection, result)

    def process(self, payload, entity_type, now):
        if entity_type != 'PRODUCT':
            raise UnsupportedOperation('The deterministic prototype processor supports PRODUCT payloads.')
        if self.config.get('processing_outcome') == 'TIMEOUT':
            raise ProcessingFailure('PROVIDER_TIMEOUT', 'RETRIEVAL', 'The simulated provider timed out.')
        name_field = self.config.get('product_name_field', 'name')
        if not isinstance(name_field, str) or len(name_field) > 100:
            raise ValidationError('Invalid provider product mapping.')
        raw_id = payload.body.get('id')
        if not isinstance(raw_id, (int, str)) or isinstance(raw_id, bool):
            raise ProcessingFailure('MISSING_EXTERNAL_ID', 'MAPPING', 'The provider product has no stable identifier.', False)
        external_id = str(raw_id)
        attributes = {'name': payload.body.get(name_field), 'sku': payload.body.get('sku'),
                      'price': payload.body.get('price')}
        source_at = payload.source_at or payload.received_at
        if source_at > payload.received_at or payload.received_at > now:
            raise ProcessingFailure('FUTURE_SOURCE_TIME', 'VALIDATION', 'Source timestamps are in the future.', False)
        try:
            product, changed = persist_product(self.connection, external_id, attributes, source_at, now)
        except ValidationError as exc:
            raise ProcessingFailure('INVALID_PRODUCT', 'VALIDATION', 'The product failed canonical validation.', False) from exc
        return ProcessingResult('PRODUCT', external_id, product.pk, source_at, payload.received_at, skipped=not changed)


_adapters = {}


def register_adapter(provider_key, factory):
    """Called by trusted integration code, never from an HTTP request or config string."""
    _adapters[provider_key] = factory


def operations_for(connection):
    if connection.is_mock:
        return MockIntegrationOperations(connection)
    factory = _adapters.get(connection.integration_source.key)
    if factory is None:
        raise UnsupportedOperation('No live integration operation adapter is registered for this provider.')
    return factory(connection)
