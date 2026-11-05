"""
Bug Reproduction Test Suite for Business Memory & Knowledge and AI Intelligence.
Reproduces:
1. BUG-001: Archived knowledge sources/documents leaking into vector and keyword search.
2. BUG-002: resolve_active_version allowing ARCHIVED documents without StaleVersionError.
3. BUG-003: cosine_similarity unhandled exception on NaN/Inf float vectors.
4. BUG-004: Brand tone channel overrides case-sensitivity failure.
5. BUG-005: Recommendation false goal alignment on completely unrelated domains.
"""

from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from app.exceptions import StaleVersionError
from app.models import (
    AiRecommendationEvidence,
    Business,
    BusinessFact,
    BusinessIssue,
    BusinessIssueEvidence,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeEmbedding,
    KnowledgeSource,
)
from app.services.ai import (
    generate_goal_aligned_recommendation,
    generate_grounded_recommendation,
)
from app.services.ai_context import assemble_memory_context
from app.services.domain_memory import (
    BrandToneData,
    get_brand_tone,
    set_brand_tone,
    set_business_goal,
)
from app.services.hybrid_retrieval import (
    cosine_similarity,
    keyword_search,
    vector_search,
)
from app.services.knowledge_pipeline import (
    bump_document_version,
    resolve_active_version,
)


class BugReproductionTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(
            name="Test Business",
            slug="test-business",
            currency="BDT",
            timezone="Asia/Dhaka",
        )

    # ─────────────────────────────────────────────────────────────
    # BUG-001: Archived sources/documents leaking into active retrieval
    # ─────────────────────────────────────────────────────────────

    def test_bug_001_archived_knowledge_source_leaks_into_search(self):
        archived_source = KnowledgeSource.objects.create(
            business=self.business,
            name="Decommissioned Supplier SOP",
            source_type="DOCUMENT_UPLOAD",
            status="ARCHIVED",
        )
        doc = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=archived_source,
            title="Old Supplier Contacts",
            content="Contact supplier Alpha at supplier@alpha.test for Gazipur orders.",
            status="READY",
            version=1,
        )
        chunk = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=doc,
            chunk_index=0,
            content="Contact supplier Alpha at supplier@alpha.test for Gazipur orders.",
            token_count=10,
            metadata={"is_current": True},
        )
        KnowledgeEmbedding.objects.create(
            business=self.business,
            knowledge_chunk=chunk,
            model="test-model-4d",
            dimensions=4,
            embedding=[1.0, 0.0, 0.0, 0.0],
        )

        # Keyword search should NOT return chunks from an ARCHIVED source
        kw_results = keyword_search(
            business=self.business,
            query="supplier Alpha",
        )
        self.assertEqual(len(kw_results), 0, "BUG-001: Keyword search returned chunks from ARCHIVED source!")

        # Vector search should NOT return chunks from an ARCHIVED source
        vec_results = vector_search(
            business=self.business,
            query_vector=[1.0, 0.0, 0.0, 0.0],
            model_name="test-model-4d",
            min_score=0.5,
        )
        self.assertEqual(len(vec_results), 0, "BUG-001: Vector search returned chunks from ARCHIVED source!")

    # ─────────────────────────────────────────────────────────────
    # BUG-002: resolve_active_version allows ARCHIVED documents
    # ─────────────────────────────────────────────────────────────

    def test_bug_002_resolve_active_version_allows_archived_documents(self):
        source = KnowledgeSource.objects.create(
            business=self.business,
            name="Policy Source",
            source_type="POLICY_FILE",
        )
        KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=source,
            title="Archived SLA",
            content="Delivery SLA 5 days.",
            status="ARCHIVED",
            version=1,
        )
        # Requesting an ARCHIVED version must raise StaleVersionError just like SUPERSEDED
        with self.assertRaises(StaleVersionError, msg="BUG-002: resolve_active_version allowed ARCHIVED document!"):
            resolve_active_version(self.business, source.id, target_version=1)

    def test_archived_source_documents_are_excluded_from_ai_memory_context(self):
        archived_source = KnowledgeSource.objects.create(
            business=self.business,
            name="Retired Refund Rules",
            source_type="POLICY_FILE",
            status="ARCHIVED",
            source_reference="retired-policy.pdf",
        )
        KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=archived_source,
            title="Refund policy",
            document_type="POLICY",
            content="Old policy: refunds are never allowed.",
            status="READY",
            version=1,
        )

        intent_context = assemble_memory_context(self.business, intent="refund")
        general_context = assemble_memory_context(self.business)

        self.assertEqual(intent_context, [])
        self.assertEqual(general_context, [])

    def test_policy_intent_matches_human_readable_document_title(self):
        source = KnowledgeSource.objects.create(
            business=self.business,
            name="Current Policies",
            source_type="POLICY_FILE",
        )
        document = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=source,
            title="Refund policy",
            document_type="POLICY",
            content="Refund requests are accepted within seven days.",
            status="READY",
        )

        context = assemble_memory_context(self.business, intent="refund_inquiry")

        self.assertIn(document.id, [item["id"] for item in context if item["document_type"] == "POLICY"])

    def test_stale_document_cannot_be_bumped_twice(self):
        source = KnowledgeSource.objects.create(
            business=self.business,
            name="Delivery Rules",
            source_type="POLICY_FILE",
        )
        original = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=source,
            title="Delivery policy",
            document_type="POLICY",
            content="Delivery within five days.",
            status="READY",
            version=1,
        )
        bump_document_version(original, "Delivery within three days.")

        with self.assertRaises(StaleVersionError):
            bump_document_version(original, "Delivery within two days.")
        self.assertEqual(
            KnowledgeDocument.objects.filter(knowledge_source=source, version=2, status="READY").count(),
            1,
        )

    def test_goal_context_includes_text_target(self):
        set_business_goal(
            business=self.business,
            name="Reduce returns",
            category="OPERATIONS",
            priority="HIGH",
            target_value="Below 5%",
            timeframe="Q4",
        )

        context = assemble_memory_context(self.business)

        goal = next(item for item in context if item["document_type"] == "BUSINESS_GOAL")
        self.assertIn("Below 5%", goal["content"])

    def test_recommendation_does_not_attach_unrelated_open_issue(self):
        BusinessIssue.objects.create(
            business=self.business,
            issue_type="MARKETING_ROAS_DEGRADATION",
            title="Campaign ROAS fell",
            status="OPEN",
            detected_at=timezone.now(),
        )
        BusinessFact.objects.create(
            business=self.business,
            fact_type="MARKETING_ROAS",
            statement="Campaign ROAS is 1.1.",
            detected_at=timezone.now(),
        )
        recommendation, _ = generate_goal_aligned_recommendation(
            business=self.business,
            issue_type="HIGH_DELIVERY_FAILURE",
            candidate_action_type="CHANGE_COURIER",
        )

        self.assertIsNone(recommendation.business_issue_id)
        self.assertFalse(
            AiRecommendationEvidence.objects.filter(ai_recommendation=recommendation).exists()
        )

    def test_grounded_recommendation_does_not_attach_unrelated_fact(self):
        issue = BusinessIssue.objects.create(
            business=self.business,
            issue_type="HIGH_DELIVERY_FAILURE",
            title="Delivery failure rose",
            status="OPEN",
            detected_at=timezone.now(),
        )
        BusinessFact.objects.create(
            business=self.business,
            fact_type="MARKETING_ROAS",
            statement="Campaign ROAS is 1.1.",
            detected_at=timezone.now(),
        )
        invalidated_fact = BusinessFact.all_objects.create(
            business=self.business,
            fact_type="DELIVERY_FAILURE",
            statement="Old delivery failure finding was invalidated.",
            status="INVALIDATED",
            detected_at=timezone.now(),
        )
        BusinessIssueEvidence.objects.create(
            business_issue=issue,
            business_fact=invalidated_fact,
            evidence_type="FACT",
        )

        with patch.object(Business, "execute_llm_with_timeout", return_value={
            "content": "Review the issue", "confidence": "0.85", "provider_status": "ok",
        }):
            recommendation, _ = generate_grounded_recommendation(self.business, issue=issue)
        evidence = AiRecommendationEvidence.objects.get(ai_recommendation=recommendation)

        self.assertEqual(evidence.business_issue_id, issue.id)
        self.assertIsNone(evidence.business_fact_id)
        self.assertEqual(evidence.evidence_type, "ISSUE_GROUNDING")

    # ─────────────────────────────────────────────────────────────
    # BUG-003: cosine_similarity unhandled exception on NaN / Inf
    # ─────────────────────────────────────────────────────────────

    def test_bug_003_cosine_similarity_handles_nan_gracefully(self):
        nan_vec = [float("nan"), 1.0, 0.0, 0.0]
        normal_vec = [1.0, 0.0, 0.0, 0.0]
        # Should return 0.0 rather than raising ValueError or returning NaN
        sim = cosine_similarity(nan_vec, normal_vec)
        self.assertEqual(sim, 0.0, "BUG-003: cosine_similarity did not handle NaN gracefully!")

    # ─────────────────────────────────────────────────────────────
    # BUG-004: Brand tone channel overrides case-sensitivity
    # ─────────────────────────────────────────────────────────────

    def test_bug_004_brand_tone_channel_override_case_insensitivity(self):
        # User stores channel override with lowercase key 'support'
        set_brand_tone(
            self.business,
            BrandToneData(
                primary_tone="Professional",
                style_guidelines=[],
                preferred_terms=[],
                restricted_words=["cheap"],
                channel_overrides={
                    "support": {"primary_tone": "Empathetic & Caring"}
                },
            ),
        )
        # Calling get_brand_tone with channel="SUPPORT" or "support" must retrieve the override
        tone = get_brand_tone(self.business, channel="SUPPORT")
        self.assertEqual(tone["primary_tone"], "Empathetic & Caring", "BUG-004: Channel override failed case-insensitive match!")

    # ─────────────────────────────────────────────────────────────
    # BUG-005: Recommendation false goal alignment on unrelated domains
    # ─────────────────────────────────────────────────────────────

    def test_bug_005_recommendation_does_not_hallucinate_unrelated_goal_alignment(self):
        # Business has a logistics goal
        set_business_goal(
            business=self.business,
            name="Reduce Courier RTO Rate to 3%",
            category="LOGISTICS",
            priority="HIGH",
            target_value="< 3%",
            timeframe="Q4",
        )
        now = timezone.now()
        BusinessIssue.objects.create(
            business=self.business,
            issue_type="MARKETING_ROAS_DEGRADATION",
            title="Facebook Ads ROAS Dropped to 1.1x",
            severity="HIGH",
            status="OPEN",
            subject_entity_type="CAMPAIGN",
            subject_entity_id=505,
            detected_at=now,
        )

        # AI recommends pausing advertising campaign
        rec, _action = generate_goal_aligned_recommendation(
            business=self.business,
            issue_type="MARKETING_ROAS_DEGRADATION",
            candidate_action_type="PAUSE_CAMPAIGN",
            candidate_entity_type="CAMPAIGN",
            candidate_entity_id=505,
        )
        # The marketing recommendation MUST NOT claim to advance the courier RTO goal
        self.assertIsNone(
            rec.metadata.get("aligned_goal"),
            "BUG-005: Marketing recommendation falsely claimed alignment with Logistics Courier goal!",
        )
        self.assertEqual(rec.priority, "MEDIUM")
