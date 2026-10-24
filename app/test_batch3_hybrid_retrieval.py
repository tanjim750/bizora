"""
Batch 3 Test Suite: Embeddings & Hybrid Retrieval Engine (Features 15-18).
Validates vector generation, dimension mismatch guardrails, vector cosine similarity search,
keyword search, Reciprocal Rank Fusion (RRF), tenant isolation, and citation preservation.
"""

from django.test import TestCase

from app.exceptions import (
    EmbeddingDimensionMismatchError,
    StaleVersionError,
    TenantIsolationError,
)
from app.models import Business, KnowledgeChunk, KnowledgeDocument, KnowledgeEmbedding, KnowledgeSource
from app.services.hybrid_retrieval import (
    cosine_similarity,
    generate_or_store_embedding,
    hybrid_retrieval,
    keyword_search,
    vector_search,
)


class Batch3HybridRetrievalTests(TestCase):
    def setUp(self):
        self.business_a = Business.objects.create(
            name="Apex Retail Dhaka",
            slug="apex-retail-dhaka",
            currency="BDT",
            timezone="Asia/Dhaka",
        )
        self.business_b = Business.objects.create(
            name="Barisal Gadgets",
            slug="barisal-gadgets",
            currency="BDT",
            timezone="Asia/Dhaka",
        )

        # Knowledge Source & Documents for Business A
        self.source_a = KnowledgeSource.objects.create(
            business=self.business_a,
            name="Operations & Policies",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            source_reference="docs/ops_2026.pdf",
        )
        self.doc_a1 = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=self.source_a,
            title="Dhaka Delivery Policy",
            document_type="POLICY",
            content="Delivery inside Dhaka takes 24 hours. Charge is 60 BDT. Preferred courier is Pathao.",
            status="READY",
            version=1,
            metadata={"category": "DELIVERY_POLICY", "region": "DHAKA"},
        )
        self.chunk_a1 = KnowledgeChunk.objects.create(
            business=self.business_a,
            knowledge_document=self.doc_a1,
            chunk_index=0,
            content="Delivery inside Dhaka takes 24 hours. Charge is 60 BDT. Preferred courier is Pathao.",
            token_count=16,
            metadata={"is_current": True, "category": "DELIVERY_POLICY", "region": "DHAKA"},
        )

        self.doc_a2 = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=self.source_a,
            title="Footwear Return Guidelines",
            document_type="POLICY",
            content="Customers may return unworn Pegasus running shoes within 7 days. SKU: APX-PEG-01.",
            status="READY",
            version=1,
            metadata={"category": "RETURN_REFUND_POLICY", "product_sku": "APX-PEG-01"},
        )
        self.chunk_a2 = KnowledgeChunk.objects.create(
            business=self.business_a,
            knowledge_document=self.doc_a2,
            chunk_index=0,
            content="Customers may return unworn Pegasus running shoes within 7 days. SKU: APX-PEG-01.",
            token_count=15,
            metadata={"is_current": True, "category": "RETURN_REFUND_POLICY", "product_sku": "APX-PEG-01"},
        )

        # Superseded document for Business A
        self.doc_a_old = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=self.source_a,
            title="Old Obsolete Policy v0",
            document_type="POLICY",
            content="Obsolete delivery rules from 2020.",
            status="SUPERSEDED",
            version=0,
        )
        self.chunk_a_old = KnowledgeChunk.objects.create(
            business=self.business_a,
            knowledge_document=self.doc_a_old,
            chunk_index=0,
            content="Obsolete delivery rules from 2020.",
            token_count=6,
            metadata={"is_current": False},
        )

        # Document & Chunk for Business B (Tenant Isolation check)
        self.source_b = KnowledgeSource.objects.create(
            business=self.business_b,
            name="Barisal Policies",
            source_type="DOCUMENT_UPLOAD",
        )
        self.doc_b1 = KnowledgeDocument.objects.create(
            business=self.business_b,
            knowledge_source=self.source_b,
            title="Barisal Delivery Rules",
            document_type="POLICY",
            content="Delivery inside Barisal town takes 12 hours. Charge is 40 BDT. SKU: APX-PEG-01.",
            status="READY",
            version=1,
        )
        self.chunk_b1 = KnowledgeChunk.objects.create(
            business=self.business_b,
            knowledge_document=self.doc_b1,
            chunk_index=0,
            content="Delivery inside Barisal town takes 12 hours. Charge is 40 BDT. SKU: APX-PEG-01.",
            token_count=15,
            metadata={"is_current": True},
        )

    # ─────────────────────────────────────────────────────────────
    # Feature 15: Embeddings & Dimension Verification
    # ─────────────────────────────────────────────────────────────

    def test_feature_15_store_embedding_happy_path(self):
        # 4D vector using test-model-4d
        vec = [0.1, 0.5, -0.2, 0.8]
        emb = generate_or_store_embedding(
            chunk=self.chunk_a1,
            vector=vec,
            model_name="test-model-4d",
            expected_dimensions=4,
        )
        self.assertIsNotNone(emb.id)
        self.assertEqual(emb.dimensions, 4)
        self.assertEqual(emb.model, "test-model-4d")
        self.assertEqual(emb.business, self.business_a)

    def test_feature_15_dimension_mismatch_raises_error(self):
        # text-embedding-3-small expects 1536 dimensions, but only 4 provided
        short_vec = [0.1, 0.2, 0.3, 0.4]
        with self.assertRaises(EmbeddingDimensionMismatchError):
            generate_or_store_embedding(
                chunk=self.chunk_a1,
                vector=short_vec,
                model_name="text-embedding-3-small",
                expected_dimensions=1536,
            )

    # ─────────────────────────────────────────────────────────────
    # Feature 16: Vector Search
    # ─────────────────────────────────────────────────────────────

    def test_feature_16_vector_search_ranking_and_isolation(self):
        # Chunk A1 (Delivery) embedding: close to [1, 0, 0, 0]
        generate_or_store_embedding(
            chunk=self.chunk_a1,
            vector=[1.0, 0.0, 0.0, 0.0],
            model_name="test-model-4d",
            expected_dimensions=4,
        )
        # Chunk A2 (Return) embedding: orthogonal [0, 1, 0, 0]
        generate_or_store_embedding(
            chunk=self.chunk_a2,
            vector=[0.0, 1.0, 0.0, 0.0],
            model_name="test-model-4d",
            expected_dimensions=4,
        )
        # Chunk A Old (Superseded) embedding
        generate_or_store_embedding(
            chunk=self.chunk_a_old,
            vector=[1.0, 0.0, 0.0, 0.0],
            model_name="test-model-4d",
            expected_dimensions=4,
        )
        # Chunk B1 (Business B) embedding
        generate_or_store_embedding(
            chunk=self.chunk_b1,
            vector=[1.0, 0.0, 0.0, 0.0],
            model_name="test-model-4d",
            expected_dimensions=4,
        )

        # Query vector matching Chunk A1
        query_vec = [0.95, 0.05, 0.0, 0.0]
        results = vector_search(
            business=self.business_a,
            query_vector=query_vec,
            top_k=5,
            model_name="test-model-4d",
        )
        self.assertGreaterEqual(len(results), 1)
        # Chunk A1 should be top result
        self.assertEqual(results[0].chunk_id, self.chunk_a1.id)
        self.assertGreater(results[0].dense_score, 0.9)

        # Invariant checks:
        result_chunk_ids = [r.chunk_id for r in results]
        # Never return superseded chunks in active retrieval
        self.assertNotIn(self.chunk_a_old.id, result_chunk_ids)
        # Never return other tenant chunks
        self.assertNotIn(self.chunk_b1.id, result_chunk_ids)

    # ─────────────────────────────────────────────────────────────
    # Feature 17: Keyword Search
    # ─────────────────────────────────────────────────────────────

    def test_feature_17_keyword_search_exact_sku_and_tenant_isolation(self):
        # Search exact SKU: APX-PEG-01
        results = keyword_search(business=self.business_a, query="APX-PEG-01", top_k=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].chunk_id, self.chunk_a2.id)

        # Verify tenant isolation: Business B has chunk with same SKU, but must NOT be in results
        result_chunk_ids = [r.chunk_id for r in results]
        self.assertNotIn(self.chunk_b1.id, result_chunk_ids)

    def test_feature_17_keyword_search_term_relevance(self):
        results = keyword_search(business=self.business_a, query="Dhaka courier Pathao", top_k=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].chunk_id, self.chunk_a1.id)
        self.assertGreater(results[0].sparse_score, 0.0)

    # ─────────────────────────────────────────────────────────────
    # Feature 18: Hybrid Retrieval & Reciprocal Rank Fusion (RRF)
    # ─────────────────────────────────────────────────────────────

    def test_feature_18_hybrid_retrieval_rrf_scoring_and_evidence(self):
        # Setup embeddings
        generate_or_store_embedding(
            chunk=self.chunk_a1,
            vector=[1.0, 0.0, 0.0, 0.0],
            model_name="test-model-4d",
            expected_dimensions=4,
        )
        generate_or_store_embedding(
            chunk=self.chunk_a2,
            vector=[0.0, 1.0, 0.0, 0.0],
            model_name="test-model-4d",
            expected_dimensions=4,
        )

        query = "Dhaka Pathao delivery"
        query_vec = [0.98, 0.02, 0.0, 0.0]

        hybrid_results = hybrid_retrieval(
            business=self.business_a,
            query=query,
            query_vector=query_vec,
            top_k=3,
            rrf_k=60,
        )
        self.assertGreaterEqual(len(hybrid_results), 1)
        top = hybrid_results[0]

        # Top item should be chunk A1
        self.assertEqual(top.chunk_id, self.chunk_a1.id)
        self.assertGreater(top.rrf_score, 0.0)
        self.assertGreater(top.dense_score, 0.0)
        self.assertGreater(top.sparse_score, 0.0)

        # Evidence preservation verification
        self.assertEqual(top.document_title, "Dhaka Delivery Policy")
        self.assertEqual(top.version, 1)
        self.assertEqual(top.source_reference, "docs/ops_2026.pdf")
        self.assertIn("category", top.metadata)

    def test_feature_18_hybrid_retrieval_context_filtering(self):
        # Filtering by category restricts results
        results = hybrid_retrieval(
            business=self.business_a,
            query="return shoes or delivery",
            filter_metadata={"category": "DELIVERY_POLICY"},
        )
        for r in results:
            self.assertEqual(r.metadata.get("category"), "DELIVERY_POLICY")
            self.assertNotEqual(r.chunk_id, self.chunk_a2.id)

    # ─────────────────────────────────────────────────────────────
    # Phase 4 Mutation Audits: Zero Norm, Null Tenant, Stale Exclusion
    # ─────────────────────────────────────────────────────────────

    def test_mutation_zero_norm_vector_does_not_crash_cosine_similarity(self):
        score = cosine_similarity([0.0, 0.0, 0.0, 0.0], [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(score, 0.0)

    def test_mutation_hybrid_retrieval_null_tenant_raises_error(self):
        with self.assertRaises(TenantIsolationError):
            hybrid_retrieval(business=None, query="Dhaka delivery")  # type: ignore

    def test_mutation_keyword_search_strictly_excludes_superseded_or_inactive_chunks(self):
        # chunk_a_old has text 'Obsolete delivery rules from 2020.'
        results = keyword_search(business=self.business_a, query="Obsolete delivery rules")
        chunk_ids = [r.chunk_id for r in results]
        self.assertNotIn(self.chunk_a_old.id, chunk_ids)

