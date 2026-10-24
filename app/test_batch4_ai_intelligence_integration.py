"""
Batch 4 Test Suite: AI Intelligence Audit, Grounding & Integration.
Validates Grounded AI Context Builder, Goal-Aligned Recommendations,
Repeat-Decision Prevention, Brand-Tone Output Enforcement,
and Safe Approval Promotion Pipeline.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from app.exceptions import TenantIsolationError, UnapprovedMemoryPromotionError
from app.models import (
    AiRecommendation,
    Business,
    BusinessFact,
    BusinessGoal,
    BusinessIssue,
    BusinessMembership,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
)
from app.services.ai import (
    assemble_grounded_memory_context,
    enforce_brand_tone_on_output,
    generate_goal_aligned_recommendation,
    promote_recommendation_to_memory,
)
from app.services.domain_memory import (
    BrandToneData,
    BusinessProfileData,
    record_historical_decision,
    set_brand_tone,
    set_business_goal,
    set_business_profile,
)

User = get_user_model()


class Batch4AiIntelligenceIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lead_ops", password="password123")
        self.business_a = Business.objects.create(
            name="Apex Retail Dhaka",
            slug="apex-retail-dhaka",
            currency="BDT",
            timezone="Asia/Dhaka",
        )
        BusinessMembership.objects.create(business=self.business_a, user=self.user, role="OPERATOR")
        self.business_b = Business.objects.create(
            name="Barisal Gadgets",
            slug="barisal-gadgets",
            currency="BDT",
            timezone="Asia/Dhaka",
        )

        # Ingest knowledge documents and chunks for hybrid retrieval
        self.source = KnowledgeSource.objects.create(
            business=self.business_a,
            name="Operations Manual",
            source_type="DOCUMENT_UPLOAD",
            source_reference="docs/ops.md",
        )
        self.doc = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=self.source,
            title="Courier Operational Guide",
            document_type="POLICY",
            content="Steadfast courier is authorized for Gazipur. Pathao handles Dhaka metro.",
            status="READY",
            version=1,
            metadata={"category": "DELIVERY_POLICY"},
        )
        self.chunk = KnowledgeChunk.objects.create(
            business=self.business_a,
            knowledge_document=self.doc,
            chunk_index=0,
            content="Steadfast courier is authorized for Gazipur. Pathao handles Dhaka metro.",
            token_count=12,
            metadata={"is_current": True, "category": "DELIVERY_POLICY"},
        )

        # Set up Business Profile
        set_business_profile(
            self.business_a,
            BusinessProfileData(
                name="Apex Retail Dhaka",
                description="Apex is a leading activewear brand.",
                industry="Retail",
                operating_regions=["Dhaka", "Gazipur"],
                target_customers="Sports enthusiasts",
                operating_model={"sales": "ONLINE"},
                ai_context_summary="Fast delivery across Bangladesh.",
            ),
        )

        # Set up Brand Tone
        set_brand_tone(
            self.business_a,
            BrandToneData(
                primary_tone="Professional & Courteous",
                style_guidelines=["Active voice"],
                preferred_terms=["Valued Customer"],
                restricted_words=["cheap", "guarantee 100%"],
                channel_overrides={
                    "SUPPORT": {"primary_tone": "Empathetic & Solution-oriented"}
                },
            ),
        )

        # Set up Business Goal
        set_business_goal(
            business=self.business_a,
            name="Reduce Delivery Failure Below 5%",
            category="LOGISTICS",
            priority="HIGH",
            target_value="< 5%",
            timeframe="Q3 2026",
        )

        # Set up verified Business Issue & Fact for grounding
        self.issue = BusinessIssue.objects.create(
            business=self.business_a,
            issue_type="HIGH_DELIVERY_FAILURE",
            title="Gazipur Delivery Failure Rate Spiked to 18%",
            severity="HIGH",
            status="OPEN",
            subject_entity_type="COURIER",
            subject_entity_id=101,  # RedX courier
            detected_at=timezone.now(),
        )
        self.fact = BusinessFact.objects.create(
            business=self.business_a,
            fact_type="METRIC_ANOMALY",
            statement="RedX courier failure rate in Gazipur is 18%, above baseline 5%.",
            confidence=Decimal("0.9500"),
            valid_from=timezone.now(),
            detected_at=timezone.now(),
        )

    # ─────────────────────────────────────────────────────────────
    # 1. Grounded AI Context Builder
    # ─────────────────────────────────────────────────────────────

    def test_assemble_grounded_memory_context_synthesizes_all_domains(self):
        ctx = assemble_grounded_memory_context(
            business=self.business_a,
            query="Gazipur delivery courier",
            intent="delivery_inquiry",
            top_k=3,
        )
        self.assertIn("profile", ctx)
        self.assertEqual(ctx["profile"]["name"], "Apex Retail Dhaka")
        self.assertIn("active_goals", ctx)
        self.assertGreaterEqual(len(ctx["active_goals"]), 1)
        self.assertIn("brand_tone", ctx)
        self.assertIn("retrieved_knowledge", ctx)
        self.assertGreaterEqual(len(ctx["retrieved_knowledge"]), 1)
        self.assertIn("Steadfast", ctx["retrieved_knowledge"][0]["content"])

    def test_assemble_grounded_memory_context_tenant_isolation(self):
        with self.assertRaises(TenantIsolationError):
            assemble_grounded_memory_context(business=None, query="delivery")  # type: ignore

    # ─────────────────────────────────────────────────────────────
    # 2. Goal-Aligned Recommendations
    # ─────────────────────────────────────────────────────────────

    def test_generate_goal_aligned_recommendation_prioritizes_matching_goals(self):
        rec, _action = generate_goal_aligned_recommendation(
            business=self.business_a,
            issue_type="HIGH_DELIVERY_FAILURE",
            candidate_action_type="CHANGE_COURIER",
            candidate_entity_type="COURIER",
            candidate_entity_id=202,  # Steadfast courier
        )
        self.assertEqual(rec.priority, "HIGH")
        self.assertGreater(rec.confidence, Decimal("0.85"))
        self.assertIn("Reduce Delivery Failure", rec.metadata.get("aligned_goal", ""))

    # ─────────────────────────────────────────────────────────────
    # 3. Repeat-Decision Prevention
    # ─────────────────────────────────────────────────────────────

    def test_repeat_decision_prevention_suppresses_rejected_actions(self):
        now = timezone.now()
        # Record that Courier 999 was tried and REJECTED in Gazipur
        record_historical_decision(
            business=self.business_a,
            decision_type="CHANGE_COURIER",
            title="Attempted Courier 999 in Gazipur",
            rationale="Courier 999 lost packages and had severe SLA breaches.",
            outcome="REJECTED",
            target_entity_type="COURIER",
            target_entity_id=999,
            decided_by=self.user,
            decided_at=now,
        )

        # AI attempts to recommend Courier 999
        rec, _action = generate_goal_aligned_recommendation(
            business=self.business_a,
            issue_type="HIGH_DELIVERY_FAILURE",
            candidate_action_type="CHANGE_COURIER",
            candidate_entity_type="COURIER",
            candidate_entity_id=999,
        )
        # Must suppress or flag conflict rather than blindly suggesting Courier 999
        self.assertTrue(rec.metadata.get("repeat_decision_conflict", False))
        self.assertIn("previously rejected", rec.rationale.lower())

    # ─────────────────────────────────────────────────────────────
    # 4. Brand Tone Output Enforcement
    # ─────────────────────────────────────────────────────────────

    def test_enforce_brand_tone_on_output_sanitizes_restricted_terms(self):
        raw_text = "We offer cheap shoes and we guarantee 100% satisfaction on delivery."
        sanitized = enforce_brand_tone_on_output(
            business=self.business_a,
            text=raw_text,
            channel="SUPPORT",
        )
        self.assertNotIn("cheap", sanitized.lower())
        self.assertNotIn("guarantee 100%", sanitized.lower())

    # ─────────────────────────────────────────────────────────────
    # 5. Safe Approval Promotion Pipeline
    # ─────────────────────────────────────────────────────────────

    def test_promote_recommendation_to_memory_governance_gate(self):
        now = timezone.now()
        unapproved_rec = AiRecommendation.objects.create(
            business=self.business_a,
            recommendation_type="CHANGE_COURIER",
            title="Route Gazipur to Steadfast",
            description="Shift volume to Steadfast.",
            status="SUGGESTED",
            generated_at=now,
        )
        # Unapproved cannot be promoted
        with self.assertRaises(UnapprovedMemoryPromotionError):
            promote_recommendation_to_memory(
                business=self.business_a,
                recommendation=unapproved_rec,
                user=self.user,
            )

        # Once approved, succeeds
        unapproved_rec.status = "APPROVED"
        unapproved_rec.save()

        suggestion = promote_recommendation_to_memory(
            business=self.business_a,
            recommendation=unapproved_rec,
            user=self.user,
        )
        self.assertIsNotNone(suggestion.id)
        self.assertEqual(suggestion.approved_by, self.user)
        self.assertEqual(suggestion.status, "APPROVED")

    # ─────────────────────────────────────────────────────────────
    # Adversarial & Edge Case Tests (Phase 4)
    # ─────────────────────────────────────────────────────────────

    def test_promote_recommendation_cross_tenant_isolation_rejected(self):
        now = timezone.now()
        rec_b = AiRecommendation.objects.create(
            business=self.business_b,
            recommendation_type="CHANGE_COURIER",
            title="Barisal Route Expansion",
            status="APPROVED",
            generated_at=now,
        )
        # Attempting to promote business B's recommendation within business A must fail
        with self.assertRaises(TenantIsolationError):
            promote_recommendation_to_memory(
                business=self.business_a,
                recommendation=rec_b,
                user=self.user,
            )

    def test_promote_recommendation_requires_authoritative_user(self):
        now = timezone.now()
        approved_rec = AiRecommendation.objects.create(
            business=self.business_a,
            recommendation_type="RESTOCK",
            title="Restock shoes",
            status="APPROVED",
            generated_at=now,
        )
        with self.assertRaises(UnapprovedMemoryPromotionError):
            promote_recommendation_to_memory(
                business=self.business_a,
                recommendation=approved_rec,
                user=None,  # Human approver missing
            )

    def test_enforce_brand_tone_edge_cases_and_casing(self):
        # Mixed casing and exclamation marks
        raw = "These are CHEAP products, but we guarantee 100% excellence!"
        sanitized = enforce_brand_tone_on_output(
            business=self.business_a,
            text=raw,
            channel="SUPPORT",
        )
        self.assertNotIn("cheap", sanitized.lower())
        self.assertNotIn("guarantee 100%", sanitized.lower())

        # Empty string
        self.assertEqual(
            enforce_brand_tone_on_output(business=self.business_a, text=""),
            "",
        )

        # Cross-tenant check
        with self.assertRaises(TenantIsolationError):
            enforce_brand_tone_on_output(business=None, text="test")  # type: ignore

    def test_assemble_grounded_memory_context_empty_query_and_no_match(self):
        # Empty query returns empty retrieved knowledge safely
        ctx_empty = assemble_grounded_memory_context(
            business=self.business_a,
            query="",
        )
        self.assertEqual(ctx_empty["retrieved_knowledge"], [])

        # Non-matching query returns empty retrieved knowledge safely
        ctx_nomatch = assemble_grounded_memory_context(
            business=self.business_a,
            query="unobtainium superconducting widgets",
        )
        self.assertEqual(ctx_nomatch["retrieved_knowledge"], [])

    def test_generate_goal_aligned_recommendation_with_no_matching_goal(self):
        # Deactivate all active goals to test fallback
        BusinessGoal.objects.filter(business=self.business_a).update(status="ARCHIVED")

        rec, _action = generate_goal_aligned_recommendation(
            business=self.business_a,
            issue_type="IRRELEVANT_ISSUE",
            candidate_action_type="UNKNOWN_ACTION",
            candidate_entity_type="NONE",
            candidate_entity_id=None,
        )
        self.assertEqual(rec.priority, "MEDIUM")
        self.assertIsNone(rec.metadata.get("aligned_goal"))
        self.assertAlmostEqual(float(rec.confidence), 0.75, places=2)

    def test_generate_goal_aligned_recommendation_tenant_isolation(self):
        with self.assertRaises(TenantIsolationError):
            generate_goal_aligned_recommendation(
                business=None,  # type: ignore
                candidate_action_type="TEST",
            )

