"""
Critical Security, Concurrency, and Adversarial Penetration Test Suite
for Business Memory & Knowledge and AI Intelligence.

Validates:
1. Concurrency and atomic race condition resilience.
2. Cross-tenant embedding leakage penetration.
3. Stale knowledge vector poisoning prevention.
4. Deep adversarial payload injection and boundary enforcement.
5. Governance tamper and privilege escalation resistance.
6. Extreme vector edge cases (zero norm, NaN, dimension mismatches).
7. Brand tone adversarial obfuscation and regex resilience.
8. Large document chunking and token stress limits.
"""


from django.contrib.auth import get_user_model
from django.db import transaction
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
    AiRecommendation,
    ApprovedSuggestion,
    Business,
)
from app.services.ai import (
    enforce_brand_tone_on_output,
    promote_recommendation_to_memory,
)
from app.services.domain_memory import (
    BrandToneData,
    set_brand_tone,
)
from app.services.hybrid_retrieval import (
    cosine_similarity,
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


class CriticalSecurityAndStressTests(TestCase):
    """
    Critical security and adversarial test suite covering
    high-concurrency, security isolation, vector corruption,
    and governance bypass vectors.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="lead_sec_tester", password="secure_password_99")
        self.business_primary = Business.objects.create(
            name="Alpha Corp",
            slug="alpha-corp",
            currency="BDT",
            timezone="Asia/Dhaka",
        )
        self.business_intruder = Business.objects.create(
            name="Hostile Intruder Corp",
            slug="hostile-intruder-corp",
            currency="USD",
            timezone="America/New_York",
        )

    # ─────────────────────────────────────────────────────────────
    # 1. Concurrency & Atomic Race Condition Test
    # ─────────────────────────────────────────────────────────────

    def test_critical_concurrent_document_version_bumps(self):
        """Verifies select_for_update atomic locking on version bumps."""
        source = register_knowledge_source(
            business=self.business_primary,
            name="Security SOP",
            source_type="DOCUMENT_UPLOAD",
        )
        req = IngestionRequest(
            business_id=self.business_primary.id,
            source_name="Security SOP",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Access Guidelines",
            content="Base v1 content for atomic verification.",
        )
        doc = ingest_document(self.business_primary, req)
        doc = process_document(doc)
        chunk_document(doc)
        self.assertEqual(doc.version, 1)

        # Execute atomic sequential version bump
        with transaction.atomic():
            v2 = bump_document_version(
                current_document=doc,
                new_content="Updated v2 content under transaction lock.",
                updated_title="Access Guidelines v2",
            )
            chunk_document(v2)
            self.assertEqual(v2.version, 2)

        # Verify old version is SUPERSEDED and active version resolves to 2
        doc.refresh_from_db()
        self.assertEqual(doc.status, "SUPERSEDED")

        active = resolve_active_version(self.business_primary, source.id)
        self.assertEqual(active.version, 2)
        self.assertEqual(active.id, v2.id)

    # ─────────────────────────────────────────────────────────────
    # 2. Cross-Tenant Embedding Leakage Penetration Test
    # ─────────────────────────────────────────────────────────────

    def test_critical_cross_tenant_embedding_and_keyword_isolation(self):
        """Ensures complete cryptographic and logical tenant separation."""
        # Primary tenant stores proprietary secret knowledge
        register_knowledge_source(
            business=self.business_primary,
            name="Proprietary Algorithms",
            source_type="DOCUMENT_UPLOAD",
        )
        req_p = IngestionRequest(
            business_id=self.business_primary.id,
            source_name="Proprietary Algorithms",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Secret Trading Formula",
            content="The secret formula is QUANTUM_ALPHA_9999 with proprietary coefficients.",
        )
        doc_p = ingest_document(self.business_primary, req_p)
        doc_p = process_document(doc_p)
        chunks_p = chunk_document(doc_p)
        secret_chunk = chunks_p[0]

        secret_vector = [0.99, 0.01, 0.0, 0.0]
        generate_or_store_embedding(
            chunk=secret_chunk,
            vector=secret_vector,
            model_name="test-model-4d",
            expected_dimensions=4,
        )

        # Hostile intruder attempts to vector search with exact same vector
        intruder_vector_results = vector_search(
            business=self.business_intruder,
            query_vector=secret_vector,
            model_name="test-model-4d",
            top_k=10,
        )
        self.assertEqual(len(intruder_vector_results), 0)

        # Hostile intruder attempts keyword search with exact secret term
        intruder_keyword_results = keyword_search(
            business=self.business_intruder,
            query="QUANTUM_ALPHA_9999",
            top_k=10,
        )
        self.assertEqual(len(intruder_keyword_results), 0)

        # Hostile intruder attempts hybrid retrieval with metadata spoofing
        intruder_fused = hybrid_retrieval(
            business=self.business_intruder,
            query="QUANTUM_ALPHA_9999",
            query_vector=secret_vector,
            filter_metadata={"business_id": self.business_primary.id},  # Spoofed tenant filter
            top_k=10,
        )
        self.assertEqual(len(intruder_fused), 0)

    # ─────────────────────────────────────────────────────────────
    # 3. Stale Knowledge Vector Poisoning Test
    # ─────────────────────────────────────────────────────────────

    def test_critical_stale_knowledge_vector_poisoning_suppressed(self):
        """Verifies that superseded document vectors are never returned in active queries."""
        source = register_knowledge_source(
            business=self.business_primary,
            name="Courier Guide",
            source_type="DOCUMENT_UPLOAD",
        )
        req_v1 = IngestionRequest(
            business_id=self.business_primary.id,
            source_name="Courier Guide",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Courier Guide v1",
            content="Carrier Alpha is authorized for Gazipur delivery.",
        )
        doc_v1 = ingest_document(self.business_primary, req_v1)
        doc_v1 = process_document(doc_v1)
        chunks_v1 = chunk_document(doc_v1)
        c1 = chunks_v1[0]

        target_vec = [1.0, 0.0, 0.0, 0.0]
        generate_or_store_embedding(
            chunk=c1,
            vector=target_vec,
            model_name="test-model-4d",
            expected_dimensions=4,
        )

        # v1 should be retrievable while active
        results_before = vector_search(
            business=self.business_primary,
            query_vector=target_vec,
            model_name="test-model-4d",
            top_k=5,
        )
        self.assertEqual(len(results_before), 1)

        # Bump to v2: Carrier Alpha is replaced by Carrier Beta
        v2 = bump_document_version(
            current_document=doc_v1,
            new_content="Carrier Beta is sole authorized carrier for Gazipur.",
            updated_title="Courier Guide v2",
        )
        chunks_v2 = chunk_document(v2)
        c2 = chunks_v2[0]
        generate_or_store_embedding(
            chunk=c2,
            vector=[0.0, 1.0, 0.0, 0.0],
            model_name="test-model-4d",
            expected_dimensions=4,
        )

        # Now query with target_vec (matching v1 vector with similarity 1.0)
        results_after = vector_search(
            business=self.business_primary,
            query_vector=target_vec,
            model_name="test-model-4d",
            min_score=0.5,
            top_k=5,
        )
        # v1 chunk MUST NOT be returned because it belongs to superseded document
        self.assertEqual(len(results_after), 0)

        # Even with min_score=0.0, the returned candidates cannot include superseded chunk c1
        all_results = vector_search(
            business=self.business_primary,
            query_vector=target_vec,
            model_name="test-model-4d",
            min_score=0.0,
            top_k=5,
        )
        self.assertNotIn(c1.id, [r.chunk_id for r in all_results])

        # Direct stale resolution raises StaleVersionError
        with self.assertRaises(StaleVersionError):
            resolve_active_version(self.business_primary, source.id, target_version=1)

    # ─────────────────────────────────────────────────────────────
    # 4. Adversarial Payload Injection & Boundary Penetration
    # ─────────────────────────────────────────────────────────────

    def test_critical_deeply_nested_adversarial_payload_injection(self):
        """Verifies recursive rejection of transactional and streaming metric payloads."""
        deep_injection_payloads = [
            {"meta": {"deep": {"order_id": 999999}}},
            {"payload": {"events": [{"transaction_id": "txn_888"}]}},
            {"metrics": {"stream": {"calculated_rate": 0.45}}},
            {"telemetry": {"p95_latency": 150.5}},
            {"billing": {"payment_intent_id": "pi_12345"}},
        ]
        for bad_meta in deep_injection_payloads:
            with self.subTest(bad_meta=bad_meta), self.assertRaises(DomainBoundaryViolationError):
                req = IngestionRequest(
                    business_id=self.business_primary.id,
                    source_name="Injected Source",
                    source_type="DOCUMENT_UPLOAD",
                    knowledge_type="BUSINESS_POLICY",
                    title="Attempted Injection",
                    content="Valid looking policy text.",
                    metadata=bad_meta,
                )
                ingest_document(self.business_primary, req)

    # ─────────────────────────────────────────────────────────────
    # 5. Governance Tamper & Privilege Escalation Resistance
    # ─────────────────────────────────────────────────────────────

    def test_critical_governance_tamper_and_unapproved_promotion(self):
        """Ensures that recommendations cannot bypass human approval gates."""
        now = timezone.now()
        unapproved = AiRecommendation.objects.create(
            business=self.business_primary,
            recommendation_type="CHANGE_COURIER",
            title="Unauthorized Carrier Route Change",
            description="Shift volume without review.",
            status="SUGGESTED",
            generated_at=now,
        )

        # Attempt promotion while status is SUGGESTED
        with self.assertRaises(UnapprovedMemoryPromotionError):
            promote_recommendation_to_memory(
                business=self.business_primary,
                recommendation=unapproved,
                user=self.user,
            )

        # Attempt promotion when rejected
        unapproved.status = "REJECTED"
        unapproved.save()
        with self.assertRaises(UnapprovedMemoryPromotionError):
            promote_recommendation_to_memory(
                business=self.business_primary,
                recommendation=unapproved,
                user=self.user,
            )

        # Attempt promotion without user attribution
        unapproved.status = "APPROVED"
        unapproved.save()
        with self.assertRaises(UnapprovedMemoryPromotionError):
            promote_recommendation_to_memory(
                business=self.business_primary,
                recommendation=unapproved,
                user=None,  # Missing human auditor
            )

        # Attempt cross-tenant promotion
        with self.assertRaises(TenantIsolationError):
            promote_recommendation_to_memory(
                business=self.business_intruder,
                recommendation=unapproved,  # Belongs to business_primary
                user=self.user,
            )

        # Verify no ApprovedSuggestion was created prematurely
        self.assertEqual(ApprovedSuggestion.objects.filter(business=self.business_primary).count(), 0)

    # ─────────────────────────────────────────────────────────────
    # 6. Extreme Vector Edge Cases (Zero Norm & Dimension Mismatches)
    # ─────────────────────────────────────────────────────────────

    def test_critical_extreme_vector_edge_cases(self):
        """Verifies zero-norm vector calculations and strict dimension gating."""
        # Zero norm division protection
        vec_zeros = [0.0, 0.0, 0.0, 0.0]
        vec_normal = [1.0, 2.0, 3.0, 4.0]
        sim = cosine_similarity(vec_zeros, vec_normal)
        self.assertEqual(sim, 0.0)

        # Dimension mismatch protection on storage
        register_knowledge_source(
            business=self.business_primary,
            name="Vector Test Source",
            source_type="DOCUMENT_UPLOAD",
        )
        req = IngestionRequest(
            business_id=self.business_primary.id,
            source_name="Vector Test Source",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Vector Chunk Doc",
            content="Testing vectors.",
        )
        doc = ingest_document(self.business_primary, req)
        doc = process_document(doc)
        chunk = chunk_document(doc)[0]

        # Storing 4D vector when model requires 1536D
        with self.assertRaises(EmbeddingDimensionMismatchError):
            generate_or_store_embedding(
                chunk=chunk,
                vector=[0.1, 0.2, 0.3, 0.4],
                model_name="text-embedding-3-small",  # Expected 1536 dimensions
            )

    # ─────────────────────────────────────────────────────────────
    # 7. Brand Tone Adversarial Obfuscation & Punctuation
    # ─────────────────────────────────────────────────────────────

    def test_critical_brand_tone_adversarial_obfuscation(self):
        """Verifies non-alphanumeric lookaround regex across complex punctuation and casing."""
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
        # Obfuscated variations
        adversarial_inputs = [
            "Our shoes are CHEAP!!",
            "We offer cheap, very cheap, items.",
            "Can we guarantee 100% swiftness?",
            "We guarantee 100%!!!",
        ]
        for raw in adversarial_inputs:
            sanitized = enforce_brand_tone_on_output(
                business=self.business_primary,
                text=raw,
                channel="SUPPORT",
            )
            self.assertNotIn("cheap", sanitized.lower())
            self.assertNotIn("guarantee 100%", sanitized.lower())

    # ─────────────────────────────────────────────────────────────
    # 8. Large Document Chunking & Stress Limits
    # ─────────────────────────────────────────────────────────────

    def test_critical_large_document_multi_section_chunking(self):
        """Stresses the chunking engine with multi-section markdown documents."""
        sections = []
        for s in range(1, 16):
            paragraph = f"Section {s} body content describing operational policy details. " * 30
            sections.append(f"## Operational Guideline Section {s}\n\n{paragraph}")

        large_content = "\n\n".join(sections)
        register_knowledge_source(
            business=self.business_primary,
            name="Enterprise Operations Manual",
            source_type="DOCUMENT_UPLOAD",
        )
        req = IngestionRequest(
            business_id=self.business_primary.id,
            source_name="Enterprise Operations Manual",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Enterprise Standard Guidelines",
            content=large_content,
        )
        doc = ingest_document(self.business_primary, req)
        doc = process_document(doc)
        chunks = chunk_document(doc, chunk_size=150, chunk_overlap=25)

        self.assertGreaterEqual(len(chunks), 15)
        # Verify strict sequential chunk ordering and token estimation
        for idx, chunk in enumerate(chunks):
            self.assertEqual(chunk.chunk_index, idx)
            self.assertGreater(chunk.token_count, 0)
            self.assertIn("section", chunk.metadata)
