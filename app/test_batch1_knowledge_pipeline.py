"""
Batch 1 Test Suite: Core Knowledge Pipeline & Versioning (Features 11-14, 19).
Validates happy paths, domain boundary violations, tenant isolation, deduplication, and atomic versioning.
"""

from django.test import TestCase

from app.exceptions import DomainBoundaryViolationError, StaleVersionError, TenantIsolationError
from app.models import Business, KnowledgeChunk, KnowledgeDocument, KnowledgeSource
from app.services.knowledge_pipeline import (
    IngestionRequest,
    KnowledgeSourceType,
    bump_document_version,
    chunk_document,
    ingest_document,
    process_document,
    register_knowledge_source,
    resolve_active_version,
)


class Batch1KnowledgePipelineTests(TestCase):
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

    # ─────────────────────────────────────────────────────────────
    # Feature 11: Knowledge Sources
    # ─────────────────────────────────────────────────────────────

    def test_feature_11_register_knowledge_source_happy_path(self):
        source = register_knowledge_source(
            business=self.business_a,
            name="Apex Return Policy 2026",
            source_type=KnowledgeSourceType.POLICY_FILE.value,
            knowledge_type="RETURN_REFUND_POLICY",
            source_reference="docs/policies/return_v1.pdf",
            metadata={"department": "Customer Support", "channel": "WEB"},
        )
        self.assertIsNotNone(source.id)
        self.assertEqual(source.business, self.business_a)
        self.assertEqual(source.status, "ACTIVE")
        self.assertEqual(source.source_type, KnowledgeSourceType.POLICY_FILE.value)

    def test_feature_11_register_knowledge_source_prohibited_boundary_types(self):
        prohibited_types = [
            "TRANSACTION_EVENT",
            "RAW_WEBHOOK",
            "ORDER_LOG",
            "LIVE_METRIC_SNAPSHOT",
            "BI_AGGREGATION",
            "ANOMALY_STREAM",
        ]
        for bad_type in prohibited_types:
            with self.subTest(bad_type=bad_type):
                with self.assertRaises(DomainBoundaryViolationError):
                    register_knowledge_source(
                        business=self.business_a,
                        name=f"Invalid {bad_type}",
                        source_type=bad_type,
                    )

    def test_feature_11_register_knowledge_source_tenant_isolation(self):
        with self.assertRaises(TenantIsolationError):
            register_knowledge_source(
                business=None,  # type: ignore
                name="Null Tenant Source",
                source_type=KnowledgeSourceType.MANUAL_ENTRY.value,
            )

    # ─────────────────────────────────────────────────────────────
    # Feature 12: Document Ingestion
    # ─────────────────────────────────────────────────────────────

    def test_feature_12_ingest_document_happy_path(self):
        source = KnowledgeSource.objects.create(
            business=self.business_a,
            name="Operations Manual",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
        )
        req = IngestionRequest(
            business_id=self.business_a.id,
            source_name=source.name,
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Standard Delivery SLA",
            content="# Delivery SLA\n\nInside Dhaka deliveries take 24-48 hours.",
            document_type="POLICY",
            file_name="delivery_sla.md",
            mime_type="text/markdown",
            metadata={"priority": "HIGH"},
        )
        doc = ingest_document(business=self.business_a, request=req)
        self.assertIsNotNone(doc.id)
        self.assertEqual(doc.business, self.business_a)
        self.assertEqual(doc.status, "PENDING")
        self.assertEqual(doc.version, 1)

    def test_feature_12_ingest_document_rejects_transactional_payload_keys(self):
        bad_keys = ["order_id", "transaction_id", "payment_intent_id"]
        for key in bad_keys:
            with self.subTest(key=key):
                req = IngestionRequest(
                    business_id=self.business_a.id,
                    source_name="Raw Order Event",
                    source_type="DOCUMENT_UPLOAD",
                    knowledge_type="BUSINESS_POLICY",
                    title="Order Log",
                    content="Order event data",
                    metadata={key: "txn_99999", "event_type": "ORDER_CREATED"},
                )
                with self.assertRaises(DomainBoundaryViolationError):
                    ingest_document(business=self.business_a, request=req)

    def test_feature_12_ingest_document_rejects_live_metric_payload_keys(self):
        bad_keys = ["metric_window", "calculated_rate", "p95_latency"]
        for key in bad_keys:
            with self.subTest(key=key):
                req = IngestionRequest(
                    business_id=self.business_a.id,
                    source_name="Live BI Snapshot",
                    source_type="DOCUMENT_UPLOAD",
                    knowledge_type="BUSINESS_POLICY",
                    title="Live Metric Anomaly",
                    content="Anomaly details",
                    metadata={key: "0.19", "calculated_rate": "19%"},
                )
                with self.assertRaises(DomainBoundaryViolationError):
                    ingest_document(business=self.business_a, request=req)

    def test_feature_12_ingest_document_cross_tenant_rejection(self):
        req = IngestionRequest(
            business_id=self.business_b.id,  # Business B ID passed
            source_name="Cross Tenant Doc",
            source_type="MANUAL_ENTRY",
            knowledge_type="BUSINESS_POLICY",
            title="Unauthorized Cross Tenant",
            content="Cross tenant test content",
        )
        with self.assertRaises(TenantIsolationError):
            ingest_document(business=self.business_a, request=req)  # Context is Business A

    # ─────────────────────────────────────────────────────────────
    # Feature 13: Document Processing & Deduplication
    # ─────────────────────────────────────────────────────────────

    def test_feature_13_process_document_generates_sha256_hash_and_normalizes(self):
        source = KnowledgeSource.objects.create(
            business=self.business_a,
            name="Markdown Guidelines",
            source_type="DOCUMENT_UPLOAD",
        )
        doc = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=source,
            title="Brand Voice Rules",
            content="   # Brand Voice Guidelines\r\n\r\nCommunicate politely and clearly.   ",
            status="PENDING",
            version=1,
        )
        processed = process_document(doc)
        self.assertEqual(processed.status, "READY")
        self.assertIsNotNone(processed.content_hash)
        self.assertEqual(len(processed.content_hash), 64)  # SHA-256 hex digest length
        self.assertIn("Brand Voice Guidelines", processed.content)
        self.assertIsNotNone(processed.processed_at)

    def test_feature_13_process_document_deduplication_detection(self):
        source = KnowledgeSource.objects.create(
            business=self.business_a,
            name="Duplicate Test Source",
            source_type="DOCUMENT_UPLOAD",
        )
        raw_text = "Consistent policy guidelines text."
        doc1 = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=source,
            title="Policy Doc 1",
            content=raw_text,
            status="PENDING",
            version=1,
        )
        proc1 = process_document(doc1)

        doc2 = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=source,
            title="Policy Doc 2",
            content=raw_text,
            status="PENDING",
            version=1,
        )
        proc2 = process_document(doc2)
        self.assertEqual(proc1.content_hash, proc2.content_hash)
        self.assertEqual(proc2.metadata.get("is_duplicate"), True)

    # ─────────────────────────────────────────────────────────────
    # Feature 14: Knowledge Chunking
    # ─────────────────────────────────────────────────────────────

    def test_feature_14_chunk_document_ordered_section_aware(self):
        source = KnowledgeSource.objects.create(
            business=self.business_a,
            name="FAQ Source",
            source_type="DOCUMENT_UPLOAD",
        )
        multi_section_content = (
            "## Section 1: Ordering\n\nCustomers can place orders 24/7 via the website.\n\n"
            "## Section 2: Payments\n\nWe accept bKash, Nagad, Visa, Mastercard, and Cash on Delivery.\n\n"
            "## Section 3: Returns\n\nReturns must be initiated within 7 calendar days of receipt."
        )
        doc = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=source,
            title="Store FAQ",
            content=multi_section_content,
            status="READY",
            version=1,
            content_hash="abc123hash",
        )
        chunks = chunk_document(doc, chunk_size=200, chunk_overlap=20)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[1].chunk_index, 1)
        self.assertEqual(chunks[2].chunk_index, 2)
        # Verify tenant isolation and source traceability
        for chunk in chunks:
            self.assertEqual(chunk.business, self.business_a)
            self.assertEqual(chunk.knowledge_document, doc)
            self.assertGreater(chunk.token_count, 0)
            self.assertIn("section", chunk.metadata)

    # ─────────────────────────────────────────────────────────────
    # Feature 19: Knowledge Versioning
    # ─────────────────────────────────────────────────────────────

    def test_feature_19_bump_document_version_atomically_supersedes_v1(self):
        source = KnowledgeSource.objects.create(
            business=self.business_a,
            name="Refund Policy",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="RETURN_REFUND_POLICY",
        )
        v1_doc = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=source,
            title="Refund Policy v1",
            content="Returns accepted within 7 days.",
            status="READY",
            version=1,
        )
        c1 = KnowledgeChunk.objects.create(
            business=self.business_a,
            knowledge_document=v1_doc,
            chunk_index=0,
            content="Returns accepted within 7 days.",
            token_count=6,
            metadata={"is_current": True},
        )

        v2_doc = bump_document_version(
            current_document=v1_doc,
            new_content="Returns accepted within 14 days for VIP customers.",
            updated_title="Refund Policy v2",
        )
        self.assertEqual(v2_doc.version, 2)
        self.assertEqual(v2_doc.status, "READY")

        # Verify v1 is now SUPERSEDED
        v1_doc.refresh_from_db()
        self.assertEqual(v1_doc.status, "SUPERSEDED")

        # Verify v1 chunks are marked non-current/superseded
        c1.refresh_from_db()
        self.assertEqual(c1.metadata.get("is_current"), False)

    def test_feature_19_resolve_active_version_and_stale_rejection(self):
        source = KnowledgeSource.objects.create(
            business=self.business_a,
            name="Courier SLA",
            source_type="POLICY_FILE",
        )
        v1 = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=source,
            title="Courier SLA v1",
            content="Dhaka 3 days.",
            status="SUPERSEDED",
            version=1,
        )
        v2 = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=source,
            title="Courier SLA v2",
            content="Dhaka 24 hours.",
            status="READY",
            version=2,
        )
        active = resolve_active_version(business=self.business_a, knowledge_source_id=source.id)
        self.assertEqual(active.id, v2.id)
        self.assertEqual(active.version, 2)

        # Asking specifically for superseded version in an active retrieval context raises StaleVersionError
        with self.assertRaises(StaleVersionError):
            resolve_active_version(
                business=self.business_a,
                knowledge_source_id=source.id,
                target_version=1,  # Target version 1 is SUPERSEDED
            )

    # ─────────────────────────────────────────────────────────────
    # Phase 4 Mutation Audits: Deep Nested Keys & Archived Sources
    # ─────────────────────────────────────────────────────────────

    def test_mutation_rejects_deeply_nested_prohibited_transactional_keys(self):
        nested_metadata = {
            "origin": "external_sync",
            "nested": {
                "level2": {
                    "order_id": "12345",
                }
            }
        }
        req = IngestionRequest(
            business_id=self.business_a.id,
            source_name="Nested Ingestion",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Sneaky Transactional Ingestion",
            content="Valid looking policy text.",
            metadata=nested_metadata,
        )
        with self.assertRaises(DomainBoundaryViolationError):
            ingest_document(business=self.business_a, request=req)

    def test_mutation_ingest_into_archived_source_is_rejected(self):
        archived_source = KnowledgeSource.objects.create(
            business=self.business_a,
            name="Decommissioned Policy",
            source_type="DOCUMENT_UPLOAD",
            status="ARCHIVED",
        )
        req = IngestionRequest(
            business_id=self.business_a.id,
            source_name="Decommissioned Policy",
            source_type="DOCUMENT_UPLOAD",
            knowledge_type="BUSINESS_POLICY",
            title="Attempting Ingestion to Archived Source",
            content="Should be rejected because source is ARCHIVED.",
        )
        with self.assertRaises(DomainBoundaryViolationError):
            ingest_document(business=self.business_a, request=req)

    def test_mutation_empty_document_processing_fails_cleanly(self):
        source = KnowledgeSource.objects.create(
            business=self.business_a,
            name="Empty Doc Source",
            source_type="DOCUMENT_UPLOAD",
        )
        empty_doc = KnowledgeDocument.objects.create(
            business=self.business_a,
            knowledge_source=source,
            title="Blank Document",
            content="   \n\t  ",
            status="PENDING",
            version=1,
        )
        processed = process_document(empty_doc)
        self.assertEqual(processed.status, "FAILED")

