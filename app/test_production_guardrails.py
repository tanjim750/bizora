"""Regression tests for knowledge and AI production boundaries."""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from app.models import (
    AiAction,
    AiRecommendation,
    Business,
    BusinessMembership,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeEmbedding,
    KnowledgeSource,
)
from app.services.actions import approve_action, reject_action
from app.services.authorization import require_business_access
from app.services.hybrid_retrieval import keyword_search, vector_search


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
