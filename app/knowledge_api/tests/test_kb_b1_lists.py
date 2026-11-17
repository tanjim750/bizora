"""Tests for knowledge sources and documents list endpoints (KB-B1)."""
from datetime import datetime, timezone
import json

from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import resolve

from app.models import (
    Business,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeEmbedding,
    KnowledgeSource,
)
from app.tests.bi_graph_helpers import client_for, make_member, make_user

NOW = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)


class KnowledgeRouteMountTests(SimpleTestCase):
    def test_routes_resolve(self):
        match_sources = resolve("/api/businesses/7/knowledge/sources/")
        self.assertEqual(match_sources.url_name, "knowledge-sources")
        self.assertEqual(match_sources.kwargs.get("business_id"), 7)

        match_docs = resolve("/api/v1/businesses/7/knowledge/documents/")
        self.assertEqual(match_docs.url_name, "knowledge-documents")
        self.assertEqual(match_docs.kwargs.get("business_id"), 7)


class KnowledgeApiListsTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(
            name="Alpha Corp", slug="alpha-corp", currency="BDT", created_at=NOW
        )
        self.other_business = Business.objects.create(
            name="Beta Corp", slug="beta-corp", currency="BDT", created_at=NOW
        )

        self.owner = make_member(self.business, role="OWNER")
        self.manager = make_member(self.business, role="MANAGER")
        self.operator = make_member(self.business, role="OPERATOR")
        self.viewer = make_member(self.business, role="VIEWER")
        self.inactive = make_member(self.business, role="VIEWER", is_active=False)
        self.outsider = make_member(self.other_business, role="OWNER")
        self.non_member = make_user()
        self.superuser = make_user(is_superuser=True)

        # Business A sources
        self.s1 = KnowledgeSource.objects.create(
            business=self.business,
            name="Source Alpha S1",
            source_type="MANUAL",
            knowledge_type="SUPPORT",
            status="ACTIVE",
            source_reference="https://example.com/?token=SENTINEL_REF",
            created_at=NOW,
        )
        self.s2 = KnowledgeSource.objects.create(
            business=self.business,
            name="Source Alpha S2",
            source_type="MANUAL",
            knowledge_type="SUPPORT",
            status="ARCHIVED",
            created_at=NOW,
        )
        self.s3 = KnowledgeSource.objects.create(
            business=self.business,
            name="Source Alpha S3",
            source_type="MANUAL",
            knowledge_type=None,
            status="ACTIVE",
            created_at=NOW,
        )

        # D1: READY, version 2, 2 chunks, metadata with secret, content_hash, file_url, file_name
        self.d1 = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.s1,
            title="Document Alpha D1",
            document_type="POLICY",
            mime_type="text/plain",
            version=2,
            status="READY",
            content="Short preview content for doc 1",
            metadata={"is_duplicate": True, "secret_key": "SENTINEL_META"},
            content_hash="SENTINEL_HASH",
            file_url="https://files.example.com/SENTINEL_URL",
            file_name="SENTINEL_FILE.pdf",
            ingested_at=NOW,
            processed_at=NOW,
            created_at=NOW,
        )
        self.c1_1 = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=self.d1,
            chunk_index=0,
            content="Chunk 1 content",
            token_count=10,
        )
        self.c1_2 = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=self.d1,
            chunk_index=1,
            content="Chunk 2 content",
            token_count=10,
        )
        # Vector embedding on c1_1
        KnowledgeEmbedding.objects.create(
            business=self.business,
            knowledge_chunk=self.c1_1,
            model="test-model-4d",
            dimensions=4,
            embedding=[0.12345, 0.23456, 0.34567, 0.45678],
        )

        # D2: SUPERSEDED, version 1, 1 chunk
        self.d2 = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.s1,
            title="Document Alpha D2",
            document_type="POLICY",
            version=1,
            status="SUPERSEDED",
            content="Older version text",
            created_at=NOW,
        )
        self.c2_1 = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=self.d2,
            chunk_index=0,
            content="Old chunk",
            token_count=5,
        )

        # D3: Under S2 (ARCHIVED), READY, 1 chunk
        self.d3 = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.s2,
            title="Document Alpha D3",
            document_type="FAQ",
            version=1,
            status="READY",
            content="Archived doc content",
            created_at=NOW,
        )
        self.c3_1 = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=self.d3,
            chunk_index=0,
            content="Archived chunk",
            token_count=5,
        )

        # D4: READY, no chunks, content=None
        self.d4 = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.s1,
            title="Document Alpha D4",
            document_type="NOTE",
            version=1,
            status="READY",
            content=None,
            created_at=NOW,
        )

        # D5: 5000 chars content
        self.d5 = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.s1,
            title="Document Alpha D5",
            document_type="GUIDE",
            version=1,
            status="READY",
            content="A" * 5000,
            created_at=NOW,
        )

        # D6: 200,000 chars content
        self.d6 = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.s1,
            title="Document Alpha D6",
            document_type="BOOK",
            version=1,
            status="READY",
            content="B" * 200000,
            created_at=NOW,
        )

        # Distinct updated_at ordering for sources
        KnowledgeSource.objects.filter(pk=self.s1.pk).update(
            updated_at=datetime(2026, 11, 17, 12, 10, 0, tzinfo=timezone.utc)
        )
        KnowledgeSource.objects.filter(pk=self.s2.pk).update(
            updated_at=datetime(2026, 11, 17, 12, 5, 0, tzinfo=timezone.utc)
        )
        KnowledgeSource.objects.filter(pk=self.s3.pk).update(
            updated_at=datetime(2026, 11, 17, 12, 1, 0, tzinfo=timezone.utc)
        )

        # Business B objects
        self.other_source = KnowledgeSource.objects.create(
            business=self.other_business,
            name="Beta Source",
            source_type="MANUAL",
            status="ACTIVE",
            created_at=NOW,
        )
        self.other_doc = KnowledgeDocument.objects.create(
            business=self.other_business,
            knowledge_source=self.other_source,
            title="Foreign secret title",
            version=1,
            status="READY",
            content="Secret beta content",
            created_at=NOW,
        )
        self.other_chunk = KnowledgeChunk.objects.create(
            business=self.other_business,
            knowledge_document=self.other_doc,
            chunk_index=0,
            content="Secret beta chunk",
            token_count=10,
        )

        self.client_owner = client_for(self.owner)
        self.client_manager = client_for(self.manager)
        self.client_operator = client_for(self.operator)
        self.client_viewer = client_for(self.viewer)
        self.client_inactive = client_for(self.inactive)
        self.client_outsider = client_for(self.outsider)
        self.client_non_member = client_for(self.non_member)
        self.client_superuser = client_for(self.superuser)

    def test_sources_list_and_totals(self):
        url = f"/api/businesses/{self.business.pk}/knowledge/sources/"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Contract keys
        self.assertEqual(set(data.keys()), {"business_id", "total_count", "limit", "offset", "totals", "results"})
        self.assertEqual(data["business_id"], self.business.pk)
        self.assertEqual(data["total_count"], 3)
        self.assertEqual(data["limit"], 25)
        self.assertEqual(data["offset"], 0)

        # Totals over whole business
        totals = data["totals"]
        self.assertEqual(set(totals.keys()), {"sources", "documents", "ready_documents", "chunks"})
        self.assertEqual(totals["sources"], 3)
        self.assertEqual(totals["documents"], 6)  # D1, D2, D3, D4, D5, D6
        self.assertEqual(totals["ready_documents"], 5)  # D1, D3, D4, D5, D6
        self.assertEqual(totals["chunks"], 4)  # c1_1, c1_2, c2_1, c3_1

        # Results ordered by updated_at desc (s1, s2, s3)
        results = data["results"]
        self.assertEqual(len(results), 3)
        self.assertEqual([r["id"] for r in results], [self.s1.pk, self.s2.pk, self.s3.pk])

        # Exact result keys
        expected_item_keys = {
            "id", "name", "source_type", "knowledge_type", "status",
            "document_count", "ready_document_count", "chunk_count",
            "created_at", "updated_at",
        }
        for r in results:
            self.assertEqual(set(r.keys()), expected_item_keys)

        # Counts check
        r_s1 = results[0]
        self.assertEqual(r_s1["document_count"], 5)  # D1, D2, D4, D5, D6
        self.assertEqual(r_s1["ready_document_count"], 4)  # D1, D4, D5, D6
        self.assertEqual(r_s1["chunk_count"], 3)  # c1_1, c1_2, c2_1

        r_s2 = results[1]
        self.assertEqual(r_s2["document_count"], 1)  # D3
        self.assertEqual(r_s2["ready_document_count"], 1)
        self.assertEqual(r_s2["chunk_count"], 1)  # c3_1

        r_s3 = results[2]
        self.assertEqual(r_s3["document_count"], 0)
        self.assertEqual(r_s3["ready_document_count"], 0)
        self.assertEqual(r_s3["chunk_count"], 0)

        # Filter ?status=ARCHIVED
        resp_filt = self.client_owner.get(f"{url}?status=ARCHIVED")
        self.assertEqual(resp_filt.status_code, 200)
        data_filt = resp_filt.json()
        self.assertEqual(data_filt["total_count"], 1)
        self.assertEqual(len(data_filt["results"]), 1)
        self.assertEqual(data_filt["results"][0]["id"], self.s2.pk)
        # Totals unchanged
        self.assertEqual(data_filt["totals"]["sources"], 3)

        # Pagination
        resp_p = self.client_owner.get(f"{url}?limit=1&offset=1")
        data_p = resp_p.json()
        self.assertEqual(data_p["total_count"], 3)
        self.assertEqual(len(data_p["results"]), 1)
        self.assertEqual(data_p["results"][0]["id"], self.s2.pk)

    def test_documents_list_searchable_duplicate_and_preview(self):
        url = f"/api/businesses/{self.business.pk}/knowledge/documents/"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(set(data.keys()), {"business_id", "total_count", "limit", "offset", "results"})
        self.assertEqual(data["business_id"], self.business.pk)
        self.assertEqual(data["total_count"], 6)

        results = data["results"]
        expected_item_keys = {
            "id", "source_id", "source_name", "source_status", "title",
            "document_type", "mime_type", "version", "status", "searchable",
            "is_duplicate", "chunk_count", "preview", "ingested_at", "processed_at",
            "created_at", "updated_at",
        }
        for r in results:
            self.assertEqual(set(r.keys()), expected_item_keys)

        by_id = {r["id"]: r for r in results}

        # D1: searchable true (READY, S1 is ACTIVE, chunk_count 2 > 0), is_duplicate true
        r_d1 = by_id[self.d1.pk]
        self.assertTrue(r_d1["searchable"])
        self.assertTrue(r_d1["is_duplicate"])
        self.assertEqual(r_d1["chunk_count"], 2)
        self.assertEqual(r_d1["preview"], "Short preview content for doc 1")

        # D2: searchable false (SUPERSEDED)
        r_d2 = by_id[self.d2.pk]
        self.assertFalse(r_d2["searchable"])
        self.assertFalse(r_d2["is_duplicate"])
        self.assertEqual(r_d2["chunk_count"], 1)

        # D3: searchable false (Source S2 is ARCHIVED)
        r_d3 = by_id[self.d3.pk]
        self.assertFalse(r_d3["searchable"])
        self.assertFalse(r_d3["is_duplicate"])
        self.assertEqual(r_d3["chunk_count"], 1)

        # D4: searchable false (no chunks), preview is None
        r_d4 = by_id[self.d4.pk]
        self.assertFalse(r_d4["searchable"])
        self.assertFalse(r_d4["is_duplicate"])
        self.assertEqual(r_d4["chunk_count"], 0)
        self.assertIsNone(r_d4["preview"])

        # D5: 5000 chars preview <= 161 chars, ending with …
        r_d5 = by_id[self.d5.pk]
        self.assertLessEqual(len(r_d5["preview"]), 161)
        self.assertTrue(r_d5["preview"].endswith("…"))

        # Filter by source
        r_src = self.client_owner.get(f"{url}?source={self.s2.pk}")
        self.assertEqual(r_src.status_code, 200)
        self.assertEqual(r_src.json()["total_count"], 1)
        self.assertEqual(r_src.json()["results"][0]["id"], self.d3.pk)

        # Filter by foreign source -> 200 with total_count 0
        r_foreign = self.client_owner.get(f"{url}?source={self.other_source.pk}")
        self.assertEqual(r_foreign.status_code, 200)
        self.assertEqual(r_foreign.json()["total_count"], 0)
        self.assertEqual(r_foreign.json()["results"], [])

        # Filter by nonexistent source
        r_none = self.client_owner.get(f"{url}?source=987654")
        self.assertEqual(r_none.status_code, 200)
        self.assertEqual(r_foreign.json(), r_none.json())

    def test_bad_input_gives_400(self):
        urls = [
            f"/api/businesses/{self.business.pk}/knowledge/sources/",
            f"/api/businesses/{self.business.pk}/knowledge/documents/",
        ]
        bad_params = [
            ("limit=0", "limit"),
            ("limit=101", "limit"),
            ("limit=abc", "limit"),
            ("limit=1.5", "limit"),
            ("limit=1&limit=2", "limit"),
            ("offset=-1", "offset"),
            ("status=archived", "status"),  # must be upper case / valid enum regex
            ("foo=1", "foo"),
            (f"business_id={self.other_business.pk}", "business_id"),
        ]

        for base_url in urls:
            for qs, field in bad_params:
                resp = self.client_owner.get(f"{base_url}?{qs}")
                self.assertEqual(resp.status_code, 400, f"Expected 400 for {base_url}?{qs}")
                data = resp.json()
                self.assertEqual(data["code"], "INVALID_DATA")
                self.assertIn(field, data["fields"])

        # Documents specific bad inputs
        doc_url = f"/api/businesses/{self.business.pk}/knowledge/documents/"
        for qs, field in [("source=0", "source"), ("source=abc", "source")]:
            resp = self.client_owner.get(f"{doc_url}?{qs}")
            self.assertEqual(resp.status_code, 400)
            data = resp.json()
            self.assertEqual(data["code"], "INVALID_DATA")
            self.assertIn(field, data["fields"])

    def test_no_leakage_of_secrets_or_metadata(self):
        urls = [
            f"/api/businesses/{self.business.pk}/knowledge/sources/",
            f"/api/businesses/{self.business.pk}/knowledge/documents/",
        ]
        forbidden_strings = [
            "SENTINEL_META",
            "SENTINEL_HASH",
            "SENTINEL_URL",
            "SENTINEL_FILE",
            "SENTINEL_REF",
            "0.12345",
            "Foreign secret title",
        ]
        forbidden_keys = {
            "content",
            "metadata",
            "embedding",
            "embeddings",
            "vector",
            "file_url",
            "file_name",
            "content_hash",
            "source_reference",
        }

        def assert_no_forbidden_keys(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    self.assertNotIn(k, forbidden_keys)
                    assert_no_forbidden_keys(v)
            elif isinstance(obj, list):
                for item in obj:
                    assert_no_forbidden_keys(item)

        for url in urls:
            resp = self.client_owner.get(url)
            self.assertEqual(resp.status_code, 200)
            text = resp.content.decode("utf-8")
            for forbidden in forbidden_strings:
                self.assertNotIn(forbidden, text)
            assert_no_forbidden_keys(resp.json())

        # Response size test: 200,000 char document must be smaller than 20,000 bytes
        doc_resp = self.client_owner.get(f"/api/businesses/{self.business.pk}/knowledge/documents/?limit=100")
        self.assertLess(len(doc_resp.content), 20000)

    def test_access_roles_and_methods(self):
        urls = [
            f"/api/businesses/{self.business.pk}/knowledge/sources/",
            f"/api/businesses/{self.business.pk}/knowledge/documents/",
        ]

        for url in urls:
            # OWNER, MANAGER, OPERATOR, VIEWER get 200
            for client in (self.client_owner, self.client_manager, self.client_operator, self.client_viewer):
                r = client.get(url)
                self.assertEqual(r.status_code, 200)

            # Inactive, outsider, non-member get 403 with {"code", "detail"}
            for client in (self.client_inactive, self.client_outsider, self.client_non_member):
                r = client.get(url)
                self.assertEqual(r.status_code, 403)
                data = r.json()
                self.assertEqual(set(data.keys()), {"code", "detail"})
                self.assertNotIn(str(self.business.pk), data["detail"])

            # Anonymous gets 401 or 403
            anon_client = client_for(None)
            r_anon = anon_client.get(url)
            self.assertIn(r_anon.status_code, (401, 403))

            # Member of B asking for missing business gives same status and JSON as asking for business A
            missing_url = url.replace(f"businesses/{self.business.pk}/", "businesses/987654321/")
            r_missing_b = self.client_outsider.get(missing_url)
            r_alpha_b = self.client_outsider.get(url)
            self.assertEqual(r_missing_b.status_code, 403)
            self.assertEqual(r_missing_b.json(), r_alpha_b.json())

            # Superuser asking for missing business gets 404
            r_super_missing = self.client_superuser.get(missing_url)
            self.assertEqual(r_super_missing.status_code, 404)

            # Huge business id gives 404, not 500
            huge_url = url.replace(f"businesses/{self.business.pk}/", "businesses/99999999999999999999/")
            r_huge = self.client_owner.get(huge_url)
            self.assertEqual(r_huge.status_code, 404)

            # As OWNER: post, put, patch, delete give 405 and row counts don't change
            sources_before = KnowledgeSource.objects.count()
            docs_before = KnowledgeDocument.objects.count()
            chunks_before = KnowledgeChunk.objects.count()

            for method in ("post", "put", "patch", "delete"):
                m_call = getattr(self.client_owner, method)
                r_m = m_call(url, data={})
                self.assertEqual(r_m.status_code, 405)

            self.assertEqual(KnowledgeSource.objects.count(), sources_before)
            self.assertEqual(KnowledgeDocument.objects.count(), docs_before)
            self.assertEqual(KnowledgeChunk.objects.count(), chunks_before)

            # As VIEWER: post, put, patch, delete give 403 or 405
            for method in ("post", "put", "patch", "delete"):
                m_call = getattr(self.client_viewer, method)
                r_m = m_call(url, data={})
                self.assertIn(r_m.status_code, (403, 405))

    def test_bounded_queries(self):
        url_sources = f"/api/businesses/{self.business.pk}/knowledge/sources/"
        url_docs = f"/api/businesses/{self.business.pk}/knowledge/documents/"

        with CaptureQueriesContext(connection) as ctx_sources:
            r = self.client_owner.get(url_sources)
            self.assertEqual(r.status_code, 200)
            sources_queries = len(ctx_sources)
            self.assertLessEqual(sources_queries, 12)

        with CaptureQueriesContext(connection) as ctx_docs:
            r = self.client_owner.get(url_docs)
            self.assertEqual(r.status_code, 200)
            docs_queries = len(ctx_docs)
            self.assertLessEqual(docs_queries, 12)

        # Add more sources and documents to verify query count is constant (not per-row)
        for i in range(10):
            s = KnowledgeSource.objects.create(
                business=self.business,
                name=f"Source Extra {i}",
                source_type="MANUAL",
                status="ACTIVE",
                created_at=NOW,
            )
            for j in range(2):
                d = KnowledgeDocument.objects.create(
                    business=self.business,
                    knowledge_source=s,
                    title=f"Doc Extra {i}_{j}",
                    version=1,
                    status="READY",
                    content="Extra text",
                    created_at=NOW,
                )
                KnowledgeChunk.objects.create(
                    business=self.business,
                    knowledge_document=d,
                    chunk_index=0,
                    content="Extra chunk",
                    token_count=5,
                )

        with CaptureQueriesContext(connection) as ctx_sources_scale:
            r = self.client_owner.get(url_sources)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(ctx_sources_scale), sources_queries)

        with CaptureQueriesContext(connection) as ctx_docs_scale:
            r = self.client_owner.get(url_docs)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(ctx_docs_scale), docs_queries)
