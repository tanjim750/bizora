"""Regression tests for knowledge and AI production boundaries."""

import os
import subprocess
import sys
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.db.models.query import QuerySet
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone

from app.exceptions import (
    DomainBoundaryViolationError,
    EmbeddingDimensionMismatchError,
    StaleVersionError,
    TenantIsolationError,
)
from app.models import (
    AiAction,
    AiRecommendation,
    AiRecommendationEvidence,
    Business,
    BusinessFact,
    BusinessIssue,
    BusinessMembership,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeEmbedding,
    KnowledgeSource,
)
from app.services.actions import approve_action, execute_action, reject_action
from app.services.ai import generate_grounded_recommendation, promote_recommendation_to_memory
from app.services.authorization import require_business_access
from app.services.hybrid_retrieval import generate_or_store_embedding, keyword_search, vector_search
from app.services.knowledge_pipeline import (
    IngestionRequest,
    bump_document_version,
    chunk_document,
    ingest_document,
    process_document,
    resolve_active_version,
    validate_domain_boundaries,
)


class ProductionSettingsGuardrailTests(SimpleTestCase):
    def test_production_requires_a_private_secret_key(self):
        script = """
from pathlib import Path
exists = Path.exists
Path.exists = lambda path: False if path.name == '.env' else exists(path)
import bizora.settings
"""
        for secret in (None, "bizora-production-hardened-cryptographic-secret-key-vault-2026"):
            with self.subTest(secret_present=secret is not None):
                env = os.environ.copy()
                env.pop("SECRET_KEY", None)
                env["DEBUG"] = "False"
                if secret is not None:
                    env["SECRET_KEY"] = secret
                result = subprocess.run(
                    [sys.executable, "-c", script], env=env, capture_output=True, text=True, check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ImproperlyConfigured", result.stderr)


class KnowledgeRetrievalGuardrailTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="First", slug="first")
        self.other = Business.objects.create(name="Second", slug="second")

    def make_chunk(self, *, document_business, chunk_business, status="READY", metadata=None):
        source = KnowledgeSource.objects.create(
            business=document_business,
            name="Private policy",
            source_type="POLICY_FILE",
        )
        document = KnowledgeDocument.objects.create(
            business=document_business,
            knowledge_source=source,
            title="Private policy",
            content="Private refund instructions",
            status=status,
        )
        chunk = KnowledgeChunk.objects.create(
            business=chunk_business,
            knowledge_document=document,
            chunk_index=0,
            content="Private refund instructions",
            metadata=metadata,
        )
        KnowledgeEmbedding.objects.create(
            business=chunk_business,
            knowledge_chunk=chunk,
            model="test-model-4d",
            dimensions=4,
            embedding=[1.0, 0.0, 0.0, 0.0],
        )
        return chunk

    def test_inconsistent_tenant_lineage_is_never_retrieved(self):
        self.make_chunk(
            document_business=self.other,
            chunk_business=self.business,
            metadata={"is_current": True},
        )

        self.assertEqual(keyword_search(self.business, "private refund"), [])
        self.assertEqual(
            vector_search(self.business, [1.0, 0.0, 0.0, 0.0], model_name="test-model-4d"),
            [],
        )

    def test_unfinished_document_is_not_retrieved(self):
        self.make_chunk(
            document_business=self.business,
            chunk_business=self.business,
            status="PENDING",
            metadata={"is_current": True},
        )

        self.assertEqual(keyword_search(self.business, "private refund"), [])
        self.assertEqual(
            vector_search(self.business, [1.0, 0.0, 0.0, 0.0], model_name="test-model-4d"),
            [],
        )

    def test_empty_keyword_query_returns_no_documents(self):
        self.make_chunk(
            document_business=self.business,
            chunk_business=self.business,
            metadata={"is_current": True},
        )

        self.assertEqual(keyword_search(self.business, "  "), [])

    def test_null_chunk_metadata_does_not_crash_retrieval(self):
        chunk = self.make_chunk(
            document_business=self.business,
            chunk_business=self.business,
        )

        self.assertEqual(keyword_search(self.business, "private refund")[0].chunk_id, chunk.id)
        self.assertEqual(
            vector_search(self.business, [1.0, 0.0, 0.0, 0.0], model_name="test-model-4d")[0].chunk_id,
            chunk.id,
        )

    def test_embedding_write_checks_lineage_and_known_model_dimension(self):
        chunk = self.make_chunk(document_business=self.other, chunk_business=self.business)
        with self.assertRaises(TenantIsolationError):
            generate_or_store_embedding(chunk, [1.0, 0.0, 0.0, 0.0], model_name="test-model-4d")

        good_chunk = self.make_chunk(document_business=self.business, chunk_business=self.business)
        with self.assertRaises(EmbeddingDimensionMismatchError):
            generate_or_store_embedding(
                good_chunk,
                [1.0, 0.0, 0.0, 0.0],
                model_name="text-embedding-3-small",
                expected_dimensions=4,
            )

    def test_embedding_write_rejects_nonfinite_and_zero_vectors(self):
        chunk = self.make_chunk(document_business=self.business, chunk_business=self.business)
        for vector in ([float("nan"), 0, 0, 0], [float("inf"), 0, 0, 0], [0, 0, 0, 0]):
            with self.subTest(vector=vector), self.assertRaises(ValidationError):
                generate_or_store_embedding(chunk, vector, model_name="test-model-4d")

    def test_invalid_query_vector_does_not_return_unrelated_chunks(self):
        self.make_chunk(document_business=self.business, chunk_business=self.business)

        for vector in ([0.0, 0.0, 0.0, 0.0], [float("nan"), 0.0, 0.0, 0.0]):
            with self.subTest(vector=vector):
                self.assertEqual(
                    vector_search(self.business, vector, model_name="test-model-4d"),
                    [],
                )

    def test_postgres_vector_query_ranks_and_limits_in_sql(self):
        queries = []

        def capture_query(queryset):
            queries.append(str(queryset.query))
            return iter([])

        with patch.object(connection, "vendor", "postgresql"), patch.object(QuerySet, "__iter__", capture_query):
            vector_search(self.business, [1.0, 0.0, 0.0, 0.0], top_k=2, model_name="test-model-4d")

        self.assertEqual(len(queries), 1)
        self.assertIn("<=>", queries[0])
        self.assertIn("LIMIT 2", queries[0])

    @skipUnless(connection.vendor == "postgresql", "requires PostgreSQL pgvector")
    def test_postgres_metadata_filter_precedes_vector_limit(self):
        ignored = self.make_chunk(
            document_business=self.business, chunk_business=self.business,
            metadata={"is_current": True, "category": "OTHER"},
        )
        target = self.make_chunk(
            document_business=self.business, chunk_business=self.business,
            metadata={"is_current": True, "category": "DELIVERY"},
        )
        generate_or_store_embedding(ignored, [1.0, 0.0, 0.0, 0.0], model_name="test-model-4d")
        generate_or_store_embedding(target, [0.8, 0.6, 0.0, 0.0], model_name="test-model-4d")

        results = vector_search(
            self.business, [1.0, 0.0, 0.0, 0.0], top_k=1,
            model_name="test-model-4d", filter_metadata={"category": "DELIVERY"},
        )
        self.assertEqual([item.chunk_id for item in results], [target.id])


class EvidenceTenantGuardrailTests(TestCase):
    def test_recommendation_evidence_cannot_reference_other_business_fact(self):
        business = Business.objects.create(name="Evidence", slug="evidence")
        other = Business.objects.create(name="Outside", slug="outside")
        recommendation = AiRecommendation.objects.create(
            business=business,
            recommendation_type="REVIEW",
            title="Review",
            description="Review evidence",
            generated_at=timezone.now(),
        )
        fact = BusinessFact.objects.create(
            business=other,
            fact_type="POLICY",
            statement="Other tenant only",
            detected_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            AiRecommendationEvidence.objects.create(
                ai_recommendation=recommendation,
                business_fact=fact,
                evidence_type="FACT",
            )


class AiActionAuthorizationGuardrailTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="Protected", slug="protected")
        self.user = get_user_model().objects.create_user(username="member", password="password123")
        self.recommendation = AiRecommendation.objects.create(
            business=self.business,
            recommendation_type="REVIEW",
            title="Review",
            description="Review evidence",
            generated_at=timezone.now(),
        )
        self.action = AiAction.objects.create(
            business=self.business,
            ai_recommendation=self.recommendation,
            action_type="REVIEW",
            status="SUGGESTED",
        )

    def test_dynamic_business_id_does_not_bypass_required_role(self):
        BusinessMembership.objects.create(business=self.business, user=self.user, role="MEMBER")
        self.user.business_id = self.business.id

        with self.assertRaises(PermissionDenied):
            require_business_access(self.user, self.business, roles={"OWNER", "ADMIN", "OPERATOR"})

    def test_action_services_require_operator_membership(self):
        with self.assertRaises(PermissionDenied):
            approve_action(self.action, self.user, "approve")
        with self.assertRaises(PermissionDenied):
            reject_action(self.action, self.user, "reject")

        BusinessMembership.objects.create(business=self.business, user=self.user, role="MEMBER")
        with self.assertRaises(PermissionDenied):
            approve_action(self.action, self.user, "approve")

    def test_approved_memory_promotion_requires_operator_membership(self):
        self.recommendation.status = "APPROVED"
        self.recommendation.save(update_fields=["status"])

        with self.assertRaises(PermissionDenied):
            promote_recommendation_to_memory(self.business, self.recommendation, self.user)

        membership = BusinessMembership.objects.create(
            business=self.business, user=self.user, role="MEMBER"
        )
        with self.assertRaises(PermissionDenied):
            promote_recommendation_to_memory(self.business, self.recommendation, self.user)

        membership.role = "OPERATOR"
        membership.save(update_fields=["role"])
        suggestion = promote_recommendation_to_memory(self.business, self.recommendation, self.user)
        self.assertEqual(suggestion.approved_by_id, self.user.id)

    def test_unavailable_ai_provider_cannot_create_a_recommendation(self):
        issue = BusinessIssue.objects.create(
            business=self.business, issue_type="INVENTORY", title="Stock low", detected_at=timezone.now(),
        )
        with patch.dict(os.environ, {"BIZORA_LLM_URL": ""}), self.assertRaises(ValidationError):
            generate_grounded_recommendation(self.business, issue)
        self.assertFalse(AiRecommendation.objects.filter(business=self.business).exclude(pk=self.recommendation.pk).exists())


class AiActionExecutionTransactionTests(TransactionTestCase):
    def setUp(self):
        business = Business.objects.create(name="External action", slug="external-action")
        recommendation = AiRecommendation.objects.create(
            business=business, recommendation_type="REVIEW", title="Review",
            description="Review evidence", generated_at=timezone.now(),
        )
        self.action = AiAction.objects.create(
            business=business, ai_recommendation=recommendation, action_type="REVIEW",
            status="APPROVED", approved_at=timezone.now(), is_simulated=False,
        )

    def test_provider_call_is_not_retried_after_audit_write_fails(self):
        calls = []

        def provider(payload):
            calls.append(payload)
            return {"status": "success"}

        with patch("app.services.actions._record_action_audit", side_effect=RuntimeError("audit failed")), self.assertRaises(RuntimeError):
            execute_action(self.action, executor_fn=provider)

        self.action.refresh_from_db()
        self.assertEqual(self.action.status, "EXECUTED")
        execute_action(self.action, executor_fn=provider)
        self.assertEqual(len(calls), 1)

    def test_external_call_rejects_an_enclosing_transaction(self):
        calls = []
        with transaction.atomic(), self.assertRaises(ValidationError):
            execute_action(self.action, executor_fn=lambda payload: calls.append(payload))
        self.assertEqual(calls, [])

    def test_provider_is_not_retried_if_result_write_fails(self):
        calls = []
        save = AiAction.save
        writes = 0

        def fail_result_write(action, *args, **kwargs):
            nonlocal writes
            writes += 1
            if writes == 2:
                raise RuntimeError("result write failed")
            return save(action, *args, **kwargs)

        with patch.object(AiAction, "save", fail_result_write), self.assertRaises(RuntimeError):
            execute_action(self.action, executor_fn=lambda payload: calls.append(payload) or {"status": "success"})

        self.action.refresh_from_db()
        self.assertEqual(self.action.status, "EXECUTING")
        with self.assertRaises(ValidationError):
            execute_action(self.action, executor_fn=lambda payload: calls.append(payload))
        self.assertEqual(len(calls), 1)


class KnowledgePipelineGuardrailTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="Knowledge", slug="knowledge")
        self.source = KnowledgeSource.objects.create(
            business=self.business,
            name="Rules",
            source_type="POLICY_FILE",
        )

    def make_document(self, *, status="READY", metadata=None):
        return KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.source,
            title="Rules",
            content="Returns accepted within seven days.",
            status=status,
            metadata=metadata,
        )

    def test_retired_document_cannot_be_processed_again(self):
        document = self.make_document(status="SUPERSEDED")

        with self.assertRaises(StaleVersionError):
            process_document(document)
        document.refresh_from_db()
        self.assertEqual(document.status, "SUPERSEDED")

    def test_explicit_pending_version_is_not_active(self):
        document = self.make_document(status="PENDING")
        with self.assertRaises(StaleVersionError):
            resolve_active_version(self.business, self.source.id, target_version=document.version)

    def test_chunking_retry_is_idempotent_and_metadata_is_authoritative(self):
        document = self.make_document(metadata={"is_current": False, "version": 99, "section": "Forged"})

        first = chunk_document(document)
        second = chunk_document(document)

        self.assertEqual([chunk.id for chunk in first], [chunk.id for chunk in second])
        self.assertEqual(KnowledgeChunk.objects.filter(knowledge_document=document).count(), 1)
        self.assertTrue(second[0].metadata["is_current"])
        self.assertEqual(second[0].metadata["version"], document.version)
        self.assertEqual(second[0].metadata["section"], "General")

    def test_chunking_rejects_invalid_window(self):
        document = self.make_document()

        with self.assertRaises(ValidationError):
            chunk_document(document, chunk_size=0)
        with self.assertRaises(ValidationError):
            chunk_document(document, chunk_size=10, chunk_overlap=10)
        self.assertFalse(KnowledgeChunk.objects.filter(knowledge_document=document).exists())

    def test_structured_transaction_payload_cannot_be_ingested(self):
        request = IngestionRequest(
            business_id=self.business.id,
            source_name="Raw event",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Raw event",
            content='{"nested": {"Order_ID": 123}}',
        )

        with self.assertRaises(DomainBoundaryViolationError):
            ingest_document(self.business, request)
        with self.assertRaises(DomainBoundaryViolationError):
            validate_domain_boundaries("raw_webhook", metadata={})

    def test_direct_processing_rechecks_structured_content(self):
        document = self.make_document(status="PENDING")
        document.content = '{"nested": {"transaction_id": "secret"}}'
        document.save(update_fields=["content"])

        with self.assertRaises(DomainBoundaryViolationError):
            process_document(document)
        document.refresh_from_db()
        self.assertEqual(document.status, "PENDING")

    def test_processing_and_versioning_reject_cross_business_source(self):
        other = Business.objects.create(name="Other Knowledge", slug="other-knowledge")
        foreign_source = KnowledgeSource.objects.create(
            business=other, name="Foreign", source_type="POLICY_FILE"
        )
        document = self.make_document(status="PENDING")
        document.knowledge_source = foreign_source
        document.save(update_fields=["knowledge_source"])

        with self.assertRaises(TenantIsolationError):
            process_document(document)

        document.status = "READY"
        document.save(update_fields=["status"])
        with self.assertRaises(TenantIsolationError):
            bump_document_version(document, "New rules")

    def test_version_update_rejects_empty_content(self):
        document = self.make_document()

        with self.assertRaises(ValidationError):
            bump_document_version(document, "  ")
        document.refresh_from_db()
        self.assertEqual(document.status, "READY")

    def test_version_update_rejects_structured_transaction_payload(self):
        document = self.make_document()

        with self.assertRaises(DomainBoundaryViolationError):
            bump_document_version(document, '{"order_id": 123}')
        document.refresh_from_db()
        self.assertEqual(document.status, "READY")

    def test_version_update_uses_requested_document_metadata_with_existing_chunks(self):
        document = self.make_document(metadata={"policy": "old"})
        chunk_document(document)

        updated = bump_document_version(
            document,
            "Returns accepted within ten days.",
            updated_metadata={"policy": "new"},
        )

        self.assertEqual(updated.metadata["policy"], "new")
        self.assertEqual(updated.metadata["supersedes_version"], document.version)
        self.assertNotIn("is_current", updated.metadata)
