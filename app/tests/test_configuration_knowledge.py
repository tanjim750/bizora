from unittest.mock import patch

from django.test import TestCase

from app.configuration.selectors import approved_sources, knowledge_configuration
from app.models import KnowledgeDocument, KnowledgeReprocessingRequest, KnowledgeSource
from app.tests.configuration_helpers import setup_configuration
from app.tests.observability_helpers import NOW


@patch('app.configuration.views.timezone.now', return_value=NOW)
class KnowledgeConfigurationTests(TestCase):
    def setUp(self):
        setup_configuration(self)

    def create_source(self, **changes):
        return self.client.post(self.base+'sources/', {'name': 'Support manual', 'source_type': 'MANUAL',
            'knowledge_type': 'SUPPORT', 'source_reference': 'manual:support-v1', 'status': 'ACTIVE', **changes}, format='json')

    def test_source_approval_and_workflow_scope_control_consumer_sources(self, _):
        result = self.create_source()
        self.assertEqual(result.status_code, 201, result.data)
        source = KnowledgeSource.objects.get(pk=result.data['id'])
        self.assertEqual(source.status, 'ACTIVE')
        self.assertEqual(len(approved_sources(self.business.pk, workflow='customer_support', at=NOW)), 1)
        self.client.put(self.base+'knowledge/', {'workflow_scopes': {'customer_support': ['POLICY']}}, format='json')
        self.assertEqual(approved_sources(self.business.pk, workflow='customer_support', at=NOW), [])
        response = self.client.patch(self.base+f'sources/{source.pk}/', {'version': 1, 'status': 'ARCHIVED'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(approved_sources(self.business.pk, at=NOW), [])

    def test_reprocessing_is_idempotent_pins_config_and_never_claims_completion(self, _):
        self.client.put(self.base+'knowledge/', {'chunk_size': 700}, format='json')
        source = self.create_source().data['id']
        doc = KnowledgeDocument.objects.create(business=self.business, knowledge_source_id=source, title='Guide',
            content='Original document', created_at=NOW, updated_at=NOW)
        body = {'idempotency_key': 'reprocess-v1', 'document_id': doc.pk, 'action': 'REEMBED'}
        first = self.client.post(self.base+'reprocessing/', body, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data['status'], 'REQUESTED')
        second = self.client.post(self.base+'reprocessing/', body, format='json')
        self.assertEqual(second.data['id'], first.data['id'])
        self.assertEqual(KnowledgeReprocessingRequest.objects.count(), 1)
        request = KnowledgeReprocessingRequest.objects.get()
        self.assertEqual(request.configuration_revision.data['chunk_size'], 700)
        self.assertEqual(request.source_revision.data['source_id'], source)
        self.assertEqual(request.document_version, 1)
        doc.refresh_from_db()
        self.assertEqual(doc.content, 'Original document')
        self.assertEqual(doc.status, 'READY')
        self.assertEqual(self.client.post(self.base+'reprocessing/', {**body, 'action': 'REPROCESS'}, format='json').status_code, 409)

    def test_foreign_or_inconsistent_source_document_is_rejected(self, _):
        other_source = KnowledgeSource.objects.create(business=self.other_business, name='Private', source_type='MANUAL', created_at=NOW, updated_at=NOW)
        bad_doc = KnowledgeDocument.objects.create(business=self.business, knowledge_source=other_source, title='Private', created_at=NOW, updated_at=NOW)
        for body in ({'source_id': other_source.pk}, {'document_id': bad_doc.pk}):
            response = self.client.post(self.base+'reprocessing/', {'idempotency_key': 'bad', 'action': 'REPROCESS', **body}, format='json')
            self.assertEqual(response.status_code, 400)
        self.assertFalse(KnowledgeReprocessingRequest.objects.exists())

    def test_archived_retrieval_requires_explicit_historical_context(self, _):
        self.client.put(self.base+'knowledge/', {'include_archived_for_history': True}, format='json')
        self.assertFalse(knowledge_configuration(self.business.pk, historical=False)['include_archived'])
        self.assertTrue(knowledge_configuration(self.business.pk, historical=True)['include_archived'])

    def test_archived_sources_are_available_only_for_explicit_enabled_history(self, _):
        source = self.create_source().data['id']
        self.client.patch(self.base+f'sources/{source}/', {'status': 'ARCHIVED'}, format='json')
        self.assertEqual(approved_sources(self.business.pk, historical=True, at=NOW), [])
        self.client.put(self.base+'knowledge/', {'include_archived_for_history': True}, format='json')
        self.assertEqual(approved_sources(self.business.pk, at=NOW), [])
        self.assertEqual(approved_sources(self.business.pk, historical=True, at=NOW)[0]['settings']['source_id'], source)
