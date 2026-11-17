"""Knowledge Base HTTP API views (KB-B1, KB-B2)."""
from typing import Any, Dict, List

from django.db.models import Count, Q
from django.db.models.functions import Substr
from django.http import Http404
from rest_framework.response import Response

from app.business_scope import BusinessScopedAPIView
from app.models import KnowledgeChunk, KnowledgeDocument, KnowledgeSource

from .params import MAX_BIGINT, read_int, read_status, reject_unknown
from .text import PREVIEW_CHARS, build_preview

ACTIVE_DOCUMENT_STATUSES = ("READY", "PUBLISHED")


class KnowledgeBaseView(BusinessScopedAPIView):
    """Base view for knowledge endpoints with business_id bounds checking."""

    def initial(self, request, *args, **kwargs):
        bid = kwargs.get("business_id")
        if isinstance(bid, int) and (bid < 1 or bid > MAX_BIGINT):
            raise Http404()
        super().initial(request, *args, **kwargs)


class KnowledgeSourcesView(KnowledgeBaseView):
    """GET sources list with aggregate counts and totals (read-only)."""

    def get(self, request, business_id: int):
        business = self.get_authorized_business()
        reject_unknown(request.query_params, {"status", "limit", "offset"})

        status = read_status(request.query_params)
        limit = read_int(request.query_params, "limit", default=25, minimum=1, maximum=100)
        offset = read_int(request.query_params, "offset", default=0, minimum=0, maximum=MAX_BIGINT)

        base_qs = KnowledgeSource.objects.filter(business=business)
        if status:
            base_qs = base_qs.filter(status=status)

        total_count = base_qs.count()
        page_sources = list(base_qs.order_by("-updated_at", "-id")[offset : offset + limit])

        source_ids = [s.pk for s in page_sources]
        doc_counts: Dict[int, int] = {}
        ready_counts: Dict[int, int] = {}
        chunk_counts: Dict[int, int] = {}

        if source_ids:
            doc_agg = (
                KnowledgeDocument.objects.filter(
                    business=business,
                    knowledge_source__business=business,
                    knowledge_source_id__in=source_ids,
                )
                .order_by()
                .values("knowledge_source_id")
                .annotate(
                    total=Count("id"),
                    ready=Count("id", filter=Q(status__in=ACTIVE_DOCUMENT_STATUSES)),
                )
            )
            for r in doc_agg:
                doc_counts[r["knowledge_source_id"]] = r["total"]
                ready_counts[r["knowledge_source_id"]] = r["ready"]

            chunk_agg = (
                KnowledgeChunk.objects.filter(
                    business=business,
                    knowledge_document__business=business,
                    knowledge_document__knowledge_source__business=business,
                    knowledge_document__knowledge_source_id__in=source_ids,
                )
                .order_by()
                .values("knowledge_document__knowledge_source_id")
                .annotate(total=Count("id"))
            )
            for r in chunk_agg:
                chunk_counts[r["knowledge_document__knowledge_source_id"]] = r["total"]

        # Totals over whole business (unfiltered by status/limit/offset)
        total_sources = KnowledgeSource.objects.filter(business=business).count()
        doc_totals = KnowledgeDocument.objects.filter(
            business=business,
            knowledge_source__business=business,
        ).aggregate(
            total=Count("id"),
            ready=Count("id", filter=Q(status__in=ACTIVE_DOCUMENT_STATUSES)),
        )
        total_chunks = KnowledgeChunk.objects.filter(
            business=business,
            knowledge_document__business=business,
            knowledge_document__knowledge_source__business=business,
        ).count()

        totals = {
            "sources": total_sources,
            "documents": doc_totals["total"] or 0,
            "ready_documents": doc_totals["ready"] or 0,
            "chunks": total_chunks,
        }

        results = []
        for s in page_sources:
            results.append(
                {
                    "id": s.pk,
                    "name": s.name,
                    "source_type": s.source_type,
                    "knowledge_type": s.knowledge_type,
                    "status": s.status,
                    "document_count": doc_counts.get(s.pk, 0),
                    "ready_document_count": ready_counts.get(s.pk, 0),
                    "chunk_count": chunk_counts.get(s.pk, 0),
                    "created_at": (
                        s.created_at.isoformat().replace("+00:00", "Z")
                        if s.created_at
                        else None
                    ),
                    "updated_at": (
                        s.updated_at.isoformat().replace("+00:00", "Z")
                        if s.updated_at
                        else None
                    ),
                }
            )

        return Response(
            {
                "business_id": business.pk,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "totals": totals,
                "results": results,
            }
        )


class KnowledgeDocumentsView(KnowledgeBaseView):
    """GET documents list with source info, chunk count, and text preview (read-only)."""

    def get(self, request, business_id: int):
        business = self.get_authorized_business()
        reject_unknown(request.query_params, {"source", "status", "limit", "offset"})

        source = read_int(request.query_params, "source", default=None, minimum=1, maximum=MAX_BIGINT)
        status = read_status(request.query_params)
        limit = read_int(request.query_params, "limit", default=25, minimum=1, maximum=100)
        offset = read_int(request.query_params, "offset", default=0, minimum=0, maximum=MAX_BIGINT)

        base_qs = KnowledgeDocument.objects.filter(
            business=business,
            knowledge_source__business=business,
        )
        if source is not None:
            base_qs = base_qs.filter(knowledge_source_id=source)
        if status:
            base_qs = base_qs.filter(status=status)

        total_count = base_qs.count()
        page_docs = list(
            base_qs.defer("content", "file_url", "file_name", "content_hash")
            .annotate(preview_raw=Substr("content", 1, PREVIEW_CHARS + 1))
            .order_by("knowledge_source_id", "title", "-version", "id")[offset : offset + limit]
        )

        page_source_ids = list({d.knowledge_source_id for d in page_docs if d.knowledge_source_id})
        sources_map = {}
        if page_source_ids:
            sources_qs = KnowledgeSource.objects.filter(
                business=business,
                id__in=page_source_ids,
            ).only("id", "name", "status")
            for s in sources_qs:
                sources_map[s.pk] = s

        page_doc_ids = [d.pk for d in page_docs]
        chunk_counts: Dict[int, int] = {}
        if page_doc_ids:
            chunk_agg = (
                KnowledgeChunk.objects.filter(
                    business=business,
                    knowledge_document__business=business,
                    knowledge_document_id__in=page_doc_ids,
                )
                .order_by()
                .values("knowledge_document_id")
                .annotate(total=Count("id"))
            )
            for r in chunk_agg:
                chunk_counts[r["knowledge_document_id"]] = r["total"]

        results = []
        for doc in page_docs:
            src = sources_map.get(doc.knowledge_source_id)
            src_name = src.name if src else None
            src_status = src.status if src else None
            chunks = chunk_counts.get(doc.pk, 0)
            searchable = (
                doc.status in ACTIVE_DOCUMENT_STATUSES
                and src_status == "ACTIVE"
                and chunks > 0
            )
            is_duplicate = (
                isinstance(doc.metadata, dict)
                and doc.metadata.get("is_duplicate") is True
            )
            preview = build_preview(getattr(doc, "preview_raw", None))

            results.append(
                {
                    "id": doc.pk,
                    "source_id": doc.knowledge_source_id,
                    "source_name": src_name,
                    "source_status": src_status,
                    "title": doc.title,
                    "document_type": doc.document_type,
                    "mime_type": doc.mime_type,
                    "version": doc.version,
                    "status": doc.status,
                    "searchable": searchable,
                    "is_duplicate": is_duplicate,
                    "chunk_count": chunks,
                    "preview": preview,
                    "ingested_at": (
                        doc.ingested_at.isoformat().replace("+00:00", "Z")
                        if doc.ingested_at
                        else None
                    ),
                    "processed_at": (
                        doc.processed_at.isoformat().replace("+00:00", "Z")
                        if doc.processed_at
                        else None
                    ),
                    "created_at": (
                        doc.created_at.isoformat().replace("+00:00", "Z")
                        if doc.created_at
                        else None
                    ),
                    "updated_at": (
                        doc.updated_at.isoformat().replace("+00:00", "Z")
                        if doc.updated_at
                        else None
                    ),
                }
            )

        return Response(
            {
                "business_id": business.pk,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "results": results,
            }
        )
