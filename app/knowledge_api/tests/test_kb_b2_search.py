"""Tests for knowledge search endpoint (KB-B2)."""
from datetime import datetime, timezone
import json
import socket
from unittest.mock import patch

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


class SnippetUnitTests(SimpleTestCase):
    def test_make_snippet_unit(self):
        from app.knowledge_api.search import make_snippet

        # Empty content gives ""
        self.assertEqual(make_snippet("", "refund"), "")
        self.assertEqual(make_snippet(None, "refund"), "")

        # Short text comes back whole without …
        short = "This is a short text about refunds."
        self.assertEqual(make_snippet(short, "refund"), short)

        # 10000-character text gives at most 242 characters
        long_text = "Before " + ("padding " * 1000) + "refund in middle " + ("after " * 1000)
        snippet = make_snippet(long_text, "refund")
        self.assertLessEqual(len(snippet), 242)
        self.assertIn("refund", snippet)
        self.assertTrue(snippet.startswith("…"))
        self.assertTrue(snippet.endswith("…"))

        # Match near the end still fills the window
        end_text = ("intro " * 500) + "find the keyword here at the end"
        snippet_end = make_snippet(end_text, "keyword")
        self.assertIn("keyword", snippet_end)
        self.assertTrue(snippet_end.startswith("…"))
        self.assertFalse(snippet_end.endswith("…"))

        # Case insensitive
        self.assertIn("REFUND", make_snippet("We have a REFUND policy here.", "refund"))

        # Whitespace collapsed and control characters removed
        ctrl_text = "Lots of \x00 weird \x07 spaces   and   tabs\t\t\nhere"
        snip_ctrl = make_snippet(ctrl_text, "spaces")
        self.assertNotIn("\x00", snip_ctrl)
        self.assertNotIn("\x07", snip_ctrl)
        self.assertNotIn("   ", snip_ctrl)

        # Whole-phrase match is preferred over a single word
        phrase_text = "word1 only here, then much later we have the exact whole phrase match"
        snip_phrase = make_snippet(phrase_text, "whole phrase")
        self.assertIn("whole phrase", snip_phrase)

        # No match gives the start of the text
        no_match_text = "Just some text that does not have the target query words at all" * 10
        snip_no_match = make_snippet(no_match_text, "zebra")
        self.assertTrue(snip_no_match.startswith("Just some text"))


class KnowledgeSearchRouteMountTests(SimpleTestCase):
    def test_routes_resolve(self):
        match_search = resolve("/api/businesses/7/knowledge/search/")
        self.assertEqual(match_search.url_name, "knowledge-search")
        self.assertEqual(match_search.kwargs.get("business_id"), 7)

        match_v1 = resolve("/api/v1/businesses/7/knowledge/search/")
        self.assertEqual(match_v1.url_name, "knowledge-search")
        self.assertEqual(match_v1.kwargs.get("business_id"), 7)


class KnowledgeSearchApiTests(TestCase):
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

        # Business A active source & ready doc
        self.source_active = KnowledgeSource.objects.create(
            business=self.business,
            name="Active Support Guide",
            source_type="MANUAL",
            status="ACTIVE",
            created_at=NOW,
        )
        self.doc_ready = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.source_active,
            title="Refund Guidelines",
            document_type="POLICY",
            version=1,
            status="READY",
            created_at=NOW,
        )

        # Chunk 0: Exact phrase "The refund window starts on the delivery date"
        self.chunk_0 = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=self.doc_ready,
            chunk_index=0,
            content="The refund window starts on the delivery date. Please keep the receipt.",
            metadata={
                "is_current": True,
                "section": "Refund window",
                "secret_key": "SENTINEL_META",
                "content_hash": "SENTINEL_HASH",
            },
            token_count=15,
        )
        # Vector embedding on chunk 0
        KnowledgeEmbedding.objects.create(
            business=self.business,
            knowledge_chunk=self.chunk_0,
            model="test-model-4d",
            dimensions=4,
            embedding=[0.12345, 0.23456, 0.34567, 0.45678],
        )

        # Chunk 1: Only word "refund" without "window"
        self.chunk_1 = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=self.doc_ready,
            chunk_index=1,
            content="Refunds are paid to the original payment method promptly.",
            metadata={"is_current": True, "section": "Payment methods"},
            token_count=12,
        )

        # Excluded materials:
        # 1. Superseded doc
        doc_super = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.source_active,
            title="Old Refund",
            status="SUPERSEDED",
            created_at=NOW,
        )
        self.chunk_super = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=doc_super,
            chunk_index=0,
            content="The refund window was 30 days previously.",
            metadata={"is_current": True},
            token_count=10,
        )

        # 2. Pending doc
        doc_pend = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.source_active,
            title="Pending Refund",
            status="PENDING",
            created_at=NOW,
        )
        self.chunk_pend = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=doc_pend,
            chunk_index=0,
            content="The refund window pending draft.",
            metadata={"is_current": True},
            token_count=10,
        )

        # 3. Failed doc
        doc_failed = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=self.source_active,
            title="Failed Refund",
            status="FAILED",
            created_at=NOW,
        )
        self.chunk_failed = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=doc_failed,
            chunk_index=0,
            content="The refund window failed ingestion.",
            metadata={"is_current": True},
            token_count=10,
        )

        # 4. Archived source
        source_archived = KnowledgeSource.objects.create(
            business=self.business,
            name="Archived Source",
            source_type="MANUAL",
            status="ARCHIVED",
            created_at=NOW,
        )
        doc_arch = KnowledgeDocument.objects.create(
            business=self.business,
            knowledge_source=source_archived,
            title="Archived Refund",
            status="READY",
            created_at=NOW,
        )
        self.chunk_arch = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=doc_arch,
            chunk_index=0,
            content="The refund window archived note.",
            metadata={"is_current": True},
            token_count=10,
        )

        # 5. Chunk with is_current: False
        self.chunk_not_current = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=self.doc_ready,
            chunk_index=2,
            content="The refund window historical snapshot.",
            metadata={"is_current": False},
            token_count=10,
        )

        # Business B objects
        self.source_b = KnowledgeSource.objects.create(
            business=self.other_business,
            name="Beta Active Source",
            status="ACTIVE",
            created_at=NOW,
        )
        self.doc_b = KnowledgeDocument.objects.create(
            business=self.other_business,
            knowledge_source=self.source_b,
            title="Foreign secret title",
            status="READY",
            created_at=NOW,
        )
        self.chunk_b = KnowledgeChunk.objects.create(
            business=self.other_business,
            knowledge_document=self.doc_b,
            chunk_index=0,
            content="Foreign refund window content with secret tokens.",
            metadata={"is_current": True},
            token_count=10,
        )

        self.client_owner = client_for(self.owner)
        self.client_manager = client_for(self.manager)
        self.client_operator = client_for(self.operator)
        self.client_viewer = client_for(self.viewer)
        self.client_inactive = client_for(self.inactive)
        self.client_outsider = client_for(self.outsider)
        self.client_non_member = client_for(self.non_member)

    def test_search_refund_as_manager(self):
        url = f"/api/businesses/{self.business.pk}/knowledge/search/?q=refund%20window"
        resp = self.client_manager.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Contract keys
        self.assertEqual(
            set(data.keys()),
            {"business_id", "query", "mode", "semantic_available", "limit", "result_count", "results"},
        )
        self.assertEqual(data["business_id"], self.business.pk)
        self.assertEqual(data["mode"], "KEYWORD")
        self.assertEqual(data["semantic_available"], False)
        self.assertEqual(data["query"], "refund window")
        self.assertEqual(data["limit"], 10)

        results = data["results"]
        self.assertEqual(data["result_count"], len(results))
        self.assertGreaterEqual(len(results), 1)

        expected_item_keys = {
            "chunk_id", "chunk_index", "document_id", "document_title",
            "document_type", "version", "source_id", "source_name",
            "section", "score", "snippet",
        }
        for r in results:
            self.assertEqual(set(r.keys()), expected_item_keys)

        # Chunk 0 has the exact phrase, so it must score higher than chunk 1
        r0 = next(r for r in results if r["chunk_id"] == self.chunk_0.pk)
        self.assertEqual(r0["section"], "Refund window")
        self.assertEqual(r0["document_title"], "Refund Guidelines")
        self.assertEqual(r0["document_type"], "POLICY")
        self.assertEqual(r0["source_name"], "Active Support Guide")
        self.assertEqual(r0["chunk_index"], 0)

        if len(results) > 1:
            r1 = next((r for r in results if r["chunk_id"] == self.chunk_1.pk), None)
            if r1:
                self.assertGreater(r0["score"], r1["score"])

        # Echo trimmed query
        resp_trim = self.client_manager.get(f"/api/businesses/{self.business.pk}/knowledge/search/?q=%20%20refund%20%20")
        self.assertEqual(resp_trim.status_code, 200)
        self.assertEqual(resp_trim.json()["query"], "refund")

    def test_excluded_material_never_appears(self):
        url = f"/api/businesses/{self.business.pk}/knowledge/search/?q=refund&limit=20"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        returned_chunk_ids = {r["chunk_id"] for r in results}

        # Excluded chunks
        self.assertNotIn(self.chunk_super.pk, returned_chunk_ids)
        self.assertNotIn(self.chunk_pend.pk, returned_chunk_ids)
        self.assertNotIn(self.chunk_failed.pk, returned_chunk_ids)
        self.assertNotIn(self.chunk_arch.pk, returned_chunk_ids)
        self.assertNotIn(self.chunk_not_current.pk, returned_chunk_ids)
        self.assertNotIn(self.chunk_b.pk, returned_chunk_ids)

        raw_text = resp.content.decode("utf-8")
        self.assertNotIn("Foreign secret title", raw_text)
        self.assertNotIn("Beta Active Source", raw_text)

        # Search as member of B returns only B's chunk
        url_b = f"/api/businesses/{self.other_business.pk}/knowledge/search/?q=refund"
        resp_b = self.client_outsider.get(url_b)
        self.assertEqual(resp_b.status_code, 200)
        b_results = resp_b.json()["results"]
        self.assertEqual([r["chunk_id"] for r in b_results], [self.chunk_b.pk])

    def test_no_leakage_of_secrets(self):
        # Create a large chunk of 10000 chars
        large_chunk = KnowledgeChunk.objects.create(
            business=self.business,
            knowledge_document=self.doc_ready,
            chunk_index=5,
            content="refund " + ("word " * 2000),
            metadata={"is_current": True},
            token_count=2000,
        )
        url = f"/api/businesses/{self.business.pk}/knowledge/search/?q=refund"
        resp = self.client_owner.get(url)
        self.assertEqual(resp.status_code, 200)
        text = resp.content.decode("utf-8")

        for forbidden in ("SENTINEL_META", "SENTINEL_HASH", "0.12345"):
            self.assertNotIn(forbidden, text)

        forbidden_keys = {
            "content", "metadata", "embedding", "embeddings", "vector",
            "file_url", "file_name", "content_hash", "source_reference", "is_current",
        }

        def assert_no_keys(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    self.assertNotIn(k, forbidden_keys)
                    assert_no_keys(v)
            elif isinstance(obj, list):
                for item in obj:
                    assert_no_keys(item)

        assert_no_keys(resp.json())
        self.assertLess(len(resp.content), 8000)

    def test_keyword_only_and_offline(self):
        url = f"/api/businesses/{self.business.pk}/knowledge/search/?q=refund"

        def forbidden_connect(*args, **kwargs):
            raise AssertionError("network call attempted")

        with patch("app.services.hybrid_retrieval.vector_search") as mock_vec, \
             patch("app.services.hybrid_retrieval.hybrid_retrieval") as mock_hyb, \
             patch("socket.socket.connect", side_effect=forbidden_connect):
            resp = self.client_owner.get(url)
            self.assertEqual(resp.status_code, 200)
            mock_vec.assert_not_called()
            mock_hyb.assert_not_called()

        # Unsupported query parameters give 400
        for bad_p in ("semantic=1", "vector=1,2,3,4", "source=1", f"business_id={self.business.pk}"):
            r = self.client_owner.get(f"{url}&{bad_p}")
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json()["code"], "INVALID_DATA")

    def test_validation_400_cases(self):
        base_url = f"/api/businesses/{self.business.pk}/knowledge/search/"

        # Missing q
        r = self.client_owner.get(base_url)
        self.assertEqual(r.status_code, 400)

        # Empty / whitespace q
        for q in ("", "%20%20", "a"):
            r = self.client_owner.get(f"{base_url}?q={q}")
            self.assertEqual(r.status_code, 400)
            self.assertIn("q", r.json()["fields"])

        # 201 characters
        r = self.client_owner.get(f"{base_url}?q={'a' * 201}")
        self.assertEqual(r.status_code, 400)

        # 11 words
        r = self.client_owner.get(f"{base_url}?q=one%20two%20three%20four%20five%20six%20seven%20eight%20nine%20ten%20eleven")
        self.assertEqual(r.status_code, 400)

        # Control character NUL (%00)
        r = self.client_owner.get(f"{base_url}?q=refund%00test")
        self.assertEqual(r.status_code, 400)

        # Repeated q
        r = self.client_owner.get(f"{base_url}?q=refund&q=window")
        self.assertEqual(r.status_code, 400)

        # Limit validation
        for bad_lim in ("0", "21", "abc"):
            r = self.client_owner.get(f"{base_url}?q=refund&limit={bad_lim}")
            self.assertEqual(r.status_code, 400)
            self.assertIn("limit", r.json()["fields"])

        # Default limit is 10, limit=3 returns 3
        # Create 12 matching chunks
        for i in range(12):
            KnowledgeChunk.objects.create(
                business=self.business,
                knowledge_document=self.doc_ready,
                chunk_index=10 + i,
                content=f"Batch test refund item {i}",
                metadata={"is_current": True},
                token_count=10,
            )

        r_def = self.client_owner.get(f"{base_url}?q=refund")
        self.assertEqual(r_def.status_code, 200)
        self.assertEqual(r_def.json()["limit"], 10)
        self.assertEqual(len(r_def.json()["results"]), 10)

        r_3 = self.client_owner.get(f"{base_url}?q=refund&limit=3")
        self.assertEqual(r_3.status_code, 200)
        self.assertEqual(r_3.json()["limit"], 3)
        self.assertEqual(len(r_3.json()["results"]), 3)

        # LIKE wildcard %25%25 does not match everything
        r_wild = self.client_owner.get(f"{base_url}?q=%25%25")
        self.assertEqual(r_wild.status_code, 200)
        self.assertEqual(r_wild.json()["results"], [])

    def test_empty_business_and_no_match(self):
        empty_biz = Business.objects.create(name="Empty Biz", slug="empty-biz", currency="BDT")
        owner_empty = make_member(empty_biz, role="OWNER")
        r_empty = client_for(owner_empty).get(f"/api/businesses/{empty_biz.pk}/knowledge/search/?q=refund")
        self.assertEqual(r_empty.status_code, 200)
        self.assertEqual(r_empty.json()["results"], [])
        self.assertEqual(r_empty.json()["result_count"], 0)

        # No match on existing business
        r_nomatch = self.client_owner.get(f"/api/businesses/{self.business.pk}/knowledge/search/?q=unmatchedzebra")
        self.assertEqual(r_nomatch.status_code, 200)
        self.assertEqual(r_nomatch.json()["results"], [])
        self.assertEqual(r_nomatch.json()["result_count"], 0)

    def test_access_roles_and_methods(self):
        url = f"/api/businesses/{self.business.pk}/knowledge/search/?q=refund"

        for client in (self.client_owner, self.client_manager, self.client_operator, self.client_viewer):
            r = client.get(url)
            self.assertEqual(r.status_code, 200)

        for client in (self.client_inactive, self.client_outsider, self.client_non_member):
            r = client.get(url)
            self.assertEqual(r.status_code, 403)
            self.assertEqual(set(r.json().keys()), {"code", "detail"})

        anon_client = client_for(None)
        r_anon = anon_client.get(url)
        self.assertIn(r_anon.status_code, (401, 403))

        huge_url = url.replace(f"businesses/{self.business.pk}/", "businesses/99999999999999999999/")
        r_huge = self.client_owner.get(huge_url)
        self.assertEqual(r_huge.status_code, 404)

        for method in ("post", "put", "patch", "delete"):
            m_call = getattr(self.client_owner, method)
            r_m = m_call(url, data={})
            self.assertEqual(r_m.status_code, 405)

    def test_bounded_queries(self):
        url = f"/api/businesses/{self.business.pk}/knowledge/search/?q=delivery"
        with CaptureQueriesContext(connection) as ctx_1:
            r1 = self.client_owner.get(url)
            self.assertEqual(r1.status_code, 200)
            q_count_1 = len(ctx_1)
            self.assertLessEqual(q_count_1, 10)

        # Search with 10 results
        url_10 = f"/api/businesses/{self.business.pk}/knowledge/search/?q=refund&limit=10"
        with CaptureQueriesContext(connection) as ctx_10:
            r10 = self.client_owner.get(url_10)
            self.assertEqual(r10.status_code, 200)
            self.assertEqual(len(ctx_10), q_count_1)
