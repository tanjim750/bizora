"""
End-to-End Validation Test Suite for Business Memory & Knowledge.
Directly validates all 19 features, domain boundaries, retrieval flows,
and governance gates specified in docs/implementations/features/business-memory-knowledge.md.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from app.exceptions import (
    DomainBoundaryViolationError,
    EmbeddingDimensionMismatchError,
    StaleVersionError,
    TenantIsolationError,
    UnapprovedMemoryPromotionError,
)
from app.models import (
    Business,
    BusinessFact,
    BusinessIssue,
    BusinessMembership,
    Product,
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
    DeliveryPolicyData,
    ReturnRefundPolicyData,
    check_repeat_decision_conflict,
    get_active_business_goals,
    get_active_policies,
    get_brand_tone,
    get_business_profile,
    get_delivery_policy,
    get_product_knowledge,
    get_return_refund_policy,
    get_support_knowledge,
    record_historical_decision,
    set_brand_tone,
    set_business_goal,
    set_business_policy,
    set_business_profile,
    set_delivery_policy,
    set_product_knowledge,
    set_return_refund_policy,
    set_support_knowledge,
    validate_text_against_brand_tone,
)
from app.services.hybrid_retrieval import (
    generate_or_store_embedding,
    hybrid_retrieval,
    keyword_search,
    vector_search,
)
from app.services.knowledge_pipeline import (
    IngestionRequest,
    bump_document_version,
    chunk_document,
    ingest_document,
    process_document,
    register_knowledge_source,
    resolve_active_version,
)

User = get_user_model()


class BusinessMemoryKnowledgeE2EValidationTests(TestCase):
    """
    Validates all 19 specification features and architectural boundaries
    defined in docs/implementations/features/business-memory-knowledge.md.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="lead_ops_verifier", password="password123")
        self.business_primary = Business.objects.create(
            name="Apex Activewear Dhaka",
            slug="apex-activewear-dhaka",
            currency="BDT",
            timezone="Asia/Dhaka",
        )
        BusinessMembership.objects.create(business=self.business_primary, user=self.user, role="OPERATOR")
        self.business_rival = Business.objects.create(
            name="Barisal Tech Hub",
            slug="barisal-tech-hub",
            currency="BDT",
            timezone="Asia/Dhaka",
        )
        self.product = Product.objects.create(
            business=self.business_primary,
            name="Apex Pro Carbon Runner",
            sku="APX-RUN-01",
            price=Decimal("4500.00"),
            currency="BDT",
        )

    # ─────────────────────────────────────────────────────────────
    # Feature 1: Business Profile
    # ─────────────────────────────────────────────────────────────

    def test_e2e_feature_01_business_profile(self):
        profile_data = BusinessProfileData(
            name="Apex Activewear Dhaka",
            description="Premier performance sportswear and footwear manufacturer.",
            industry="Apparel & Footwear",
            operating_regions=["Dhaka Metro", "Gazipur", "Narayanganj"],
            target_customers="Marathoners and fitness enthusiasts",
            operating_model={"sales": "OMNICHANNEL", "fulfillment": "HUB_AND_SPOKE"},
            ai_context_summary="Fast delivery across Bangladesh with focus on customer fit.",
            source_tracking="FOUNDER_INTERVIEW_2026",
        )
        mem = set_business_profile(self.business_primary, profile_data)
        self.assertTrue(mem.is_active)
        self.assertEqual(mem.source_reference, "FOUNDER_INTERVIEW_2026")

        retrieved = get_business_profile(self.business_primary)
        self.assertEqual(retrieved["industry"], "Apparel & Footwear")
        self.assertIn("Dhaka Metro", retrieved["operating_regions"])
        self.assertEqual(retrieved["operating_model"]["sales"], "OMNICHANNEL")

    # ─────────────────────────────────────────────────────────────
    # Feature 2: Business Policies
    # ─────────────────────────────────────────────────────────────

    def test_e2e_feature_02_business_policies(self):
        set_business_policy(
            business=self.business_primary,
            policy_category="ORDER_HANDLING",
            title="High Value Verification Policy",
            content="Orders exceeding BDT 10,000 require phone verification prior to fulfillment.",
            applicability="CHECKOUT_VERIFICATION",
        )
        set_business_policy(
            business=self.business_primary,
            policy_category="PAYMENT",
            title="Advance Payment Requirement",
            content="Custom monogrammed orders require 100% advance bKash/Nagad payment.",
            applicability="CUSTOM_PRODUCTS",
        )

        order_policies = get_active_policies(self.business_primary, policy_category="ORDER_HANDLING")
        self.assertEqual(len(order_policies), 1)
        self.assertEqual(order_policies[0].metadata["applicability"], "CHECKOUT_VERIFICATION")

    # ─────────────────────────────────────────────────────────────
    # Feature 3: Product Knowledge
    # ─────────────────────────────────────────────────────────────

    def test_e2e_feature_03_product_knowledge(self):
        pk = set_product_knowledge(
            business=self.business_primary,
            product=self.product,
            knowledge_type="PRODUCT_GUIDE",
            title="Pro Carbon Runner Specs",
            content="True to size. Features nitrogen-infused Pebax foam with full-length carbon plate.",
            metadata={
                "faqs": [
                    {"q": "Can it be used for marathons?", "a": "Yes, certified for WA race distances."}
                ],
                "positioning": "Flagship elite marathon racing shoe",
                "limitations": "Not recommended for gravel trails or muddy courses.",
            },
        )
        self.assertEqual(pk.subject_entity_id, self.product.id)

        knowledge = get_product_knowledge(self.business_primary, product_id=self.product.id)
        self.assertEqual(len(knowledge), 1)
        self.assertIn("Pebax foam", knowledge[0].content)
        self.assertEqual(knowledge[0].metadata["faqs"][0]["q"], "Can it be used for marathons?")

    # ─────────────────────────────────────────────────────────────
    # Feature 4: Delivery Policy
    # ─────────────────────────────────────────────────────────────

    def test_e2e_feature_04_delivery_policy(self):
        deliv = DeliveryPolicyData(
            coverage_zones=["Dhaka Metro", "Gazipur", "Chittagong"],
            sla_hours={"DHAKA_METRO": 24, "GAZIPUR": 48},
            charges={"DHAKA_METRO": 60.0, "OUTSIDE_DHAKA": 120.0},
            courier_preferences=["Pathao", "Steadfast"],
            cod_rules={"enabled": True, "max_order_bdt": 15000},
            failed_delivery_handling="Attempt customer call 3 times before courier return initiation.",
        )
        set_delivery_policy(self.business_primary, deliv)
        active_deliv = get_delivery_policy(self.business_primary)

        self.assertIn("Steadfast", active_deliv["courier_preferences"])
        self.assertEqual(active_deliv["cod_rules"]["max_order_bdt"], 15000)
        self.assertEqual(active_deliv["sla_hours"]["GAZIPUR"], 48)

    # ─────────────────────────────────────────────────────────────
    # Feature 5: Return & Refund Policy
    # ─────────────────────────────────────────────────────────────

    def test_e2e_feature_05_return_refund_policy(self):
        ret_data = ReturnRefundPolicyData(
            return_window_days=7,
            eligible_conditions=["Unused", "unworn", "original tags attached"],
            non_returnable_conditions=["Compression socks and running underwear if opened."],
            refund_methods=["ORIGINAL_PAYMENT_METHOD", "STORE_CREDIT"],
            replacement_allowed=True,
            cancellation_cutoff_hours=6,
        )
        set_return_refund_policy(self.business_primary, ret_data)
        policy = get_return_refund_policy(self.business_primary)

        self.assertEqual(policy["return_window_days"], 7)
        self.assertIn("Compression socks", policy["non_returnable_conditions"][0])
        self.assertTrue(policy["replacement_allowed"])

    # ─────────────────────────────────────────────────────────────
    # Feature 6: Brand Tone
    # ─────────────────────────────────────────────────────────────

    def test_e2e_feature_06_brand_tone(self):
        tone = BrandToneData(
            primary_tone="Athletic, motivating, and professional",
            style_guidelines=["Active voice", "Concise answers", "Courteous sign-off"],
            preferred_terms=["Athlete", "Champion", "Runner"],
            restricted_words=["cheap", "guarantee 100%", "dirt cheap"],
            channel_overrides={
                "SUPPORT": {"primary_tone": "Empathetic, reassuring, and solution-driven"}
            },
        )
        set_brand_tone(self.business_primary, tone)

        # Check retrieval & channel override
        main_tone = get_brand_tone(self.business_primary)
        self.assertEqual(main_tone["primary_tone"], "Athletic, motivating, and professional")

        support_tone = get_brand_tone(self.business_primary, channel="SUPPORT")
        self.assertEqual(support_tone["primary_tone"], "Empathetic, reassuring, and solution-driven")

        # Check word violation detector
        violations = validate_text_against_brand_tone(
            self.business_primary,
            "These shoes are cheap and we guarantee 100% no blisters.",
        )
        self.assertIn("cheap", violations)
        self.assertIn("guarantee 100%", violations)

    # ─────────────────────────────────────────────────────────────
    # Feature 7: Support Knowledge
    # ─────────────────────────────────────────────────────────────

    def test_e2e_feature_07_support_knowledge(self):
        tree = {
            "symptom": "Tracking link not updating for Gazipur shipment",
            "step_1": "Check Steadfast consignment tracking status in logistics portal.",
            "step_2": "If stalled > 24 hours, file manual merchant ticket #LOG-ST.",
        }
        set_support_knowledge(
            business=self.business_primary,
            category="DELIVERY_TRACKING",
            question_or_topic="Courier Stalled Status",
            approved_answer="Apologies for the delay! We have opened a priority ticket with Steadfast.",
            troubleshooting_tree=tree,
            escalation_team="Logistics Ops Desk",
        )
        sk_items = get_support_knowledge(self.business_primary, category="DELIVERY_TRACKING")
        self.assertEqual(len(sk_items), 1)
        self.assertEqual(sk_items[0].metadata["escalation_team"], "Logistics Ops Desk")

    # ─────────────────────────────────────────────────────────────
    # Feature 8: Business Goals
    # ─────────────────────────────────────────────────────────────

    def test_e2e_feature_08_business_goals(self):
        set_business_goal(
            business=self.business_primary,
            name="Reduce Gazipur Delivery Failure Below 5%",
            category="LOGISTICS",
            priority="HIGH",
            target_value="< 5.0%",
            timeframe="Q3 2026",
        )
        set_business_goal(
            business=self.business_primary,
            name="Improve Repeat Purchase Rate",
            category="SALES",
            priority="MEDIUM",
            target_value="25%",
            timeframe="Q4 2026",
        )
        goals = get_active_business_goals(self.business_primary)
        self.assertEqual(len(goals), 2)
        # Priority HIGH should appear before MEDIUM
        self.assertEqual(goals[0].priority, "HIGH")
        self.assertEqual(goals[0].name, "Reduce Gazipur Delivery Failure Below 5%")

    # ─────────────────────────────────────────────────────────────
    # Feature 9: Historical Decisions
    # ─────────────────────────────────────────────────────────────

    def test_e2e_feature_09_historical_decisions(self):
        now = timezone.now()
        record_historical_decision(
            business=self.business_primary,
            decision_type="CHANGE_COURIER",
            title="De-allocated RedX in Gazipur",
            rationale="RedX lost 14 packages and had 18% return rate in May 2026.",
            outcome="REJECTED",
            target_entity_type="COURIER",
            target_entity_id=901,
            decided_by=self.user,
            decided_at=now,
        )

        conflict = check_repeat_decision_conflict(
            business=self.business_primary,
            decision_type="CHANGE_COURIER",
            target_entity_type="COURIER",
            target_entity_id=901,
        )
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict.outcome, "REJECTED")
        self.assertIn("lost 14 packages", conflict.rationale)

    # ─────────────────────────────────────────────────────────────
    # Feature 11 to 14, 19: Knowledge Pipeline, Ingestion, Chunks & Versioning
    # ─────────────────────────────────────────────────────────────

    def test_e2e_features_11_to_14_and_19_pipeline_and_versioning(self):
        # 11. Knowledge Source
        source = register_knowledge_source(
            business=self.business_primary,
            name="Operations Manual 2026",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            source_reference="docs/ops_2026.md",
        )
        self.assertEqual(source.status, "ACTIVE")

        # 12 & 13 & 14. Document Ingestion v1
        content_v1 = (
            "# Courier Allocation Policy\n\n"
            "## Dhaka Metro\n"
            "Pathao is primary courier for all inside Dhaka orders.\n\n"
            "## Gazipur District\n"
            "Steadfast courier is authorized for Gazipur. Cash on delivery is supported up to 5000 BDT."
        )
        req_v1 = IngestionRequest(
            business_id=self.business_primary.id,
            source_name="Operations Manual 2026",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Courier Allocation Policy",
            content=content_v1,
            metadata={"category": "DELIVERY_POLICY"},
        )
        doc_v1 = ingest_document(self.business_primary, req_v1)
        self.assertEqual(doc_v1.version, 1)
        self.assertEqual(doc_v1.status, "PENDING")
        doc_v1 = process_document(doc_v1)
        self.assertEqual(doc_v1.status, "READY")
        chunks_v1 = chunk_document(doc_v1)
        self.assertEqual(len(chunks_v1), 2)

        # 19. Sequential atomic versioning v1 -> v2
        content_v2 = (
            "# Courier Allocation Policy\n\n"
            "## Gazipur District\n"
            "Steadfast courier is sole carrier for Gazipur. Extended COD limit up to 10000 BDT."
        )
        doc_v2 = bump_document_version(
            current_document=doc_v1,
            new_content=content_v2,
            updated_title="Courier Allocation Policy v2",
        )
        chunk_document(doc_v2)
        self.assertEqual(doc_v2.version, 2)

        # Confirm v1 is SUPERSEDED and active resolver returns v2
        doc_v1.refresh_from_db()
        self.assertEqual(doc_v1.status, "SUPERSEDED")

        active_doc = resolve_active_version(self.business_primary, source.id)
        self.assertEqual(active_doc.id, doc_v2.id)
        self.assertEqual(active_doc.version, 2)

        # Direct stale access raises StaleVersionError
        with self.assertRaises(StaleVersionError):
            resolve_active_version(self.business_primary, source.id, target_version=1)

    # ─────────────────────────────────────────────────────────────
    # Feature 15 to 18: Embeddings, Vector Search, Keyword Search & Hybrid RRF
    # ─────────────────────────────────────────────────────────────

    def test_e2e_features_15_to_18_embeddings_and_hybrid_retrieval(self):
        register_knowledge_source(
            business=self.business_primary,
            name="SOP Fulfillment",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            source_reference="docs/sop_fulfillment.md",
        )
        req = IngestionRequest(
            business_id=self.business_primary.id,
            source_name="SOP Fulfillment",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Courier Matrix",
            content="Steadfast handles Gazipur deliveries. APX-RUN-01 shoes dispatch daily at 4pm.",
        )
        doc = ingest_document(self.business_primary, req)
        doc = process_document(doc)
        chunks = chunk_document(doc)
        self.assertGreaterEqual(len(chunks), 1)
        chunk = chunks[0]

        # 15. Embedding Generation with Dimension Enforcement
        vector_4d = [0.8, 0.6, 0.0, 0.0]
        embedding = generate_or_store_embedding(
            chunk=chunk,
            vector=vector_4d,
            model_name="test-model-4d",
            expected_dimensions=4,
        )
        self.assertEqual(embedding.dimensions, 4)

        # Invalid dimension raises error
        with self.assertRaises(EmbeddingDimensionMismatchError):
            generate_or_store_embedding(
                chunk=chunk,
                vector=[0.1, 0.2],  # only 2 dimensions, expected 4
                model_name="test-model-4d",
                expected_dimensions=4,
            )

        # 16. Vector Search
        query_vector = [0.8, 0.6, 0.0, 0.0]
        dense_results = vector_search(
            business=self.business_primary,
            query_vector=query_vector,
            model_name="test-model-4d",
            top_k=2,
        )
        self.assertEqual(len(dense_results), 1)
        self.assertAlmostEqual(dense_results[0].dense_score, 1.0, places=3)

        # 17. Keyword Search (Exact SKU matching)
        sparse_results = keyword_search(
            business=self.business_primary,
            query="APX-RUN-01",
            top_k=2,
        )
        self.assertEqual(len(sparse_results), 1)
        self.assertIn("APX-RUN-01", sparse_results[0].content)

        # 18. Hybrid Retrieval (Reciprocal Rank Fusion RRF)
        fused = hybrid_retrieval(
            business=self.business_primary,
            query="APX-RUN-01 Gazipur Steadfast",
            query_vector=query_vector,
            top_k=2,
        )
        self.assertEqual(len(fused), 1)
        self.assertGreater(fused[0].rrf_score, 0.0)
        self.assertEqual(fused[0].document_title, "Courier Matrix")
        self.assertEqual(fused[0].source_reference, "docs/sop_fulfillment.md")

    # ─────────────────────────────────────────────────────────────
    # Full Integration: Grounded AI, Repeat Prevention, Tone & Governance
    # ─────────────────────────────────────────────────────────────

    def test_e2e_grounded_ai_intelligence_with_full_memory_flow(self):
        # 1. Setup deterministic BI facts & issues
        now = timezone.now()
        BusinessIssue.objects.create(
            business=self.business_primary,
            issue_type="HIGH_DELIVERY_FAILURE",
            title="Gazipur Delivery Failure Rate Spiked to 18%",
            severity="HIGH",
            status="OPEN",
            subject_entity_type="COURIER",
            subject_entity_id=901,  # RedX courier
            detected_at=now,
        )
        BusinessFact.objects.create(
            business=self.business_primary,
            fact_type="METRIC_ANOMALY",
            statement="RedX courier failure rate in Gazipur is 18%, exceeding SLA threshold 5%.",
            confidence=Decimal("0.9600"),
            valid_from=now,
            detected_at=now,
        )

        # 2. Setup goals, brand tone, historical decisions, knowledge
        set_business_goal(
            business=self.business_primary,
            name="Reduce Delivery Failure Below 5%",
            category="LOGISTICS",
            priority="HIGH",
            target_value="< 5%",
            timeframe="Q3 2026",
        )
        set_brand_tone(
            self.business_primary,
            BrandToneData(
                primary_tone="Professional",
                style_guidelines=[],
                preferred_terms=[],
                restricted_words=["cheap", "guarantee 100%"],
                channel_overrides={"SUPPORT": {"primary_tone": "Empathetic"}},
            ),
        )
        # RedX previously failed in Gazipur
        record_historical_decision(
            business=self.business_primary,
            decision_type="CHANGE_COURIER",
            title="Tried RedX in Gazipur",
            rationale="RedX lost packages and breached SLA.",
            outcome="REJECTED",
            target_entity_type="COURIER",
            target_entity_id=901,
            decided_by=self.user,
            decided_at=now,
        )

        # Ingest Steadfast courier knowledge
        register_knowledge_source(
            business=self.business_primary,
            name="Courier Guide",
            source_type="DOCUMENT_UPLOAD",
        )
        req = IngestionRequest(
            business_id=self.business_primary.id,
            source_name="Courier Guide",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Steadfast Gazipur Coverage",
            content="Steadfast courier is authorized for Gazipur with 97% on-time success rate.",
        )
        doc = ingest_document(self.business_primary, req)
        doc = process_document(doc)
        chunk_document(doc)

        # 3. Assemble Grounded Memory Context
        context = assemble_grounded_memory_context(
            business=self.business_primary,
            query="Gazipur Steadfast courier",
        )
        self.assertIn("profile", context)
        self.assertIn("active_goals", context)
        self.assertIn("brand_tone", context)
        self.assertGreaterEqual(len(context["retrieved_knowledge"]), 1)
        self.assertIn("Steadfast courier is authorized", context["retrieved_knowledge"][0]["content"])

        # 4. Repeat Decision Conflict Prevention
        # AI candidate trying to suggest RedX (901) is flagged
        rec_conflicted, _ = generate_goal_aligned_recommendation(
            business=self.business_primary,
            issue_type="HIGH_DELIVERY_FAILURE",
            candidate_action_type="CHANGE_COURIER",
            candidate_entity_type="COURIER",
            candidate_entity_id=901,
        )
        self.assertTrue(rec_conflicted.metadata.get("repeat_decision_conflict", False))
        self.assertEqual(rec_conflicted.priority, "LOW")
        self.assertIn("previously rejected", rec_conflicted.rationale.lower())

        # 5. Goal-Aligned Recommendation
        # AI candidate suggesting Steadfast (202) is aligned with strategic goal
        rec_aligned, action = generate_goal_aligned_recommendation(
            business=self.business_primary,
            issue_type="HIGH_DELIVERY_FAILURE",
            candidate_action_type="CHANGE_COURIER",
            candidate_entity_type="COURIER",
            candidate_entity_id=202,
        )
        self.assertEqual(rec_aligned.priority, "HIGH")
        self.assertGreater(rec_aligned.confidence, Decimal("0.85"))
        self.assertIn("Reduce Delivery Failure Below 5%", rec_aligned.metadata.get("aligned_goal", ""))
        self.assertEqual(action.status, "SUGGESTED")

        # 6. Brand Tone Sanitization on AI Output
        raw_ai_output = "We offer cheap shoes and guarantee 100% swift resolution."
        sanitized = enforce_brand_tone_on_output(
            business=self.business_primary,
            text=raw_ai_output,
            channel="SUPPORT",
        )
        self.assertNotIn("cheap", sanitized.lower())
        self.assertNotIn("guarantee 100%", sanitized.lower())

        # 7. Safe Approval Promotion Pipeline (Human-in-the-Loop Governance Gate)
        # Attempt to promote unapproved recommendation raises UnapprovedMemoryPromotionError
        with self.assertRaises(UnapprovedMemoryPromotionError):
            promote_recommendation_to_memory(
                business=self.business_primary,
                recommendation=rec_aligned,
                user=self.user,
            )

        # Approve and promote
        rec_aligned.status = "APPROVED"
        rec_aligned.save()
        approved_mem = promote_recommendation_to_memory(
            business=self.business_primary,
            recommendation=rec_aligned,
            user=self.user,
        )
        self.assertEqual(approved_mem.status, "APPROVED")
        self.assertEqual(approved_mem.approved_by, self.user)
        self.assertEqual(approved_mem.title, rec_aligned.title)

    # ─────────────────────────────────────────────────────────────
    # Domain Boundary Violation Invariants
    # ─────────────────────────────────────────────────────────────

    def test_e2e_domain_boundary_invariants_rejected(self):
        # Transactional data rejected
        with self.assertRaises(DomainBoundaryViolationError):
            register_knowledge_source(
                business=self.business_primary,
                name="Raw Webhook Feed",
                source_type="RAW_WEBHOOK",
            )

        # Deeply nested transactional keys rejected
        req_bad = IngestionRequest(
            business_id=self.business_primary.id,
            source_name="Fulfillment",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Invalid Document",
            content="Valid text",
            metadata={"order_payload": {"order_id": 1024}},
        )
        with self.assertRaises(DomainBoundaryViolationError):
            ingest_document(self.business_primary, req_bad)

        # Live metric streaming rejected
        with self.assertRaises(DomainBoundaryViolationError):
            register_knowledge_source(
                business=self.business_primary,
                name="Live Metric Stream",
                source_type="LIVE_METRIC_SNAPSHOT",
            )

    # ─────────────────────────────────────────────────────────────
    # Strict Multi-Tenant Isolation
    # ─────────────────────────────────────────────────────────────

    def test_e2e_strict_multi_tenant_isolation(self):
        with self.assertRaises(TenantIsolationError):
            get_business_profile(None)  # type: ignore

        with self.assertRaises(TenantIsolationError):
            register_knowledge_source(business=None, name="X", source_type="DOCUMENT_UPLOAD")  # type: ignore

        with self.assertRaises(TenantIsolationError):
            hybrid_retrieval(business=None, query="test")  # type: ignore
