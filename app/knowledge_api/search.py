"""Keyword search endpoint and snippet extraction for Knowledge API (KB-B2)."""
import re
from typing import Any, List, Optional
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from app.models import KnowledgeChunk
from app.services.hybrid_retrieval import keyword_search

from .api import KnowledgeBaseView
from .params import read_int, reject_unknown

QUERY_MIN_CHARS = 2
QUERY_MAX_CHARS = 200
QUERY_MAX_WORDS = 10
DEFAULT_LIMIT = 10
MAX_LIMIT = 20
SNIPPET_CHARS = 240
SNIPPET_LEAD_CHARS = 60


def read_query(query_params: Any) -> str:
    """Read and validate the search query string `q`."""
    if "q" not in query_params:
        raise ValidationError({"q": "Type a word or phrase to search for."})

    values = query_params.getlist("q") if hasattr(query_params, "getlist") else [query_params["q"]]
    if len(values) > 1:
        raise ValidationError({"q": "Repeated parameter."})

    raw = values[0]
    if raw is None or raw == "":
        raise ValidationError({"q": "Type a word or phrase to search for."})

    stripped = str(raw).strip()
    if len(stripped) < QUERY_MIN_CHARS:
        raise ValidationError({"q": f"Query must be at least {QUERY_MIN_CHARS} characters."})

    if len(stripped) > QUERY_MAX_CHARS:
        raise ValidationError({"q": f"Query must be at most {QUERY_MAX_CHARS} characters."})

    words = stripped.split()
    if len(words) > QUERY_MAX_WORDS:
        raise ValidationError({"q": f"Query cannot exceed {QUERY_MAX_WORDS} words."})

    for ch in stripped:
        if ord(ch) < 32 and ch not in ("\t", "\n", "\r"):
            raise ValidationError({"q": "Query contains invalid control characters."})

    return stripped


def make_snippet(content: Optional[str], query: str, width: int = SNIPPET_CHARS) -> str:
    """Extract a clean, context-focused snippet around the query match."""
    if not content:
        return ""

    prefix = str(content)[:20000]
    cleaned_chars = [c for c in prefix if c.isprintable() or c.isspace()]
    cleaned = "".join(cleaned_chars)
    text = re.sub(r"\s+", " ", cleaned).strip()

    if not text:
        return ""

    if len(text) <= width:
        return text

    lower_text = text.lower()
    collapsed_query = re.sub(r"\s+", " ", query).strip().lower()
    index = -1

    if collapsed_query and collapsed_query in lower_text:
        index = lower_text.find(collapsed_query)
    else:
        words = [w.lower() for w in re.findall(r"\w+", query) if len(w) >= 2]
        for w in words:
            idx = lower_text.find(w)
            if idx != -1:
                index = idx
                break

    if index == -1:
        index = 0

    start = max(0, index - SNIPPET_LEAD_CHARS)
    end = min(len(text), start + width)
    start = max(0, end - width)

    prefix_ellipsis = "…" if start > 0 else ""
    suffix_ellipsis = "…" if end < len(text) else ""
    return f"{prefix_ellipsis}{text[start:end]}{suffix_ellipsis}"


class KnowledgeSearchView(KnowledgeBaseView):
    """GET keyword search over a business's active knowledge (read-only)."""

    def get(self, request, business_id: int):
        business = self.get_authorized_business()
        reject_unknown(request.query_params, {"q", "limit"})

        q = read_query(request.query_params)
        limit = read_int(request.query_params, "limit", default=DEFAULT_LIMIT, minimum=1, maximum=MAX_LIMIT)

        items = keyword_search(business=business, query=q, top_k=limit)
        chunk_ids = [it.chunk_id for it in items]

        chunk_meta_map = {}
        if chunk_ids:
            chunk_rows = (
                KnowledgeChunk.objects.filter(
                    business=business,
                    id__in=chunk_ids,
                ).values(
                    "id",
                    "chunk_index",
                    "knowledge_document__document_type",
                    "knowledge_document__knowledge_source_id",
                    "knowledge_document__knowledge_source__name",
                )
            )
            for r in chunk_rows:
                chunk_meta_map[r["id"]] = r

        results = []
        for it in items:
            meta = chunk_meta_map.get(it.chunk_id)
            if not meta:
                continue

            section_raw = it.metadata.get("section") if isinstance(it.metadata, dict) else None
            section = str(section_raw)[:120] if isinstance(section_raw, str) else None
            score = round(float(it.sparse_score), 3)
            snippet = make_snippet(it.content, q)

            results.append(
                {
                    "chunk_id": it.chunk_id,
                    "chunk_index": meta["chunk_index"],
                    "document_id": it.document_id,
                    "document_title": it.document_title,
                    "document_type": meta["knowledge_document__document_type"],
                    "version": it.version,
                    "source_id": meta["knowledge_document__knowledge_source_id"],
                    "source_name": meta["knowledge_document__knowledge_source__name"],
                    "section": section,
                    "score": score,
                    "snippet": snippet,
                }
            )

        return Response(
            {
                "business_id": business.pk,
                "query": q,
                "mode": "KEYWORD",
                "semantic_available": False,
                "limit": limit,
                "result_count": len(results),
                "results": results,
            }
        )
