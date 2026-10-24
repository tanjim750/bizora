"""
Core Knowledge Pipeline & Versioning Services (Features 11-14, 19).
Implementation of Knowledge Source registration, Document Ingestion, Processing,
Chunking, and Versioning with strict domain boundary and tenant isolation guardrails.
"""

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from django.db import transaction
from django.utils import timezone

from app.exceptions import DomainBoundaryViolationError, StaleVersionError, TenantIsolationError
from app.models import Business, KnowledgeChunk, KnowledgeDocument, KnowledgeSource


class KnowledgeSourceType(str, Enum):
    MANUAL_ENTRY = "MANUAL_ENTRY"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    WEBSITE_IMPORT = "WEBSITE_IMPORT"
    SYSTEM_KNOWLEDGE = "SYSTEM_KNOWLEDGE"
    POLICY_FILE = "POLICY_FILE"


class MemoryCategory(str, Enum):
    BUSINESS_PROFILE = "BUSINESS_PROFILE"
    BUSINESS_POLICY = "BUSINESS_POLICY"
    PRODUCT_KNOWLEDGE = "PRODUCT_KNOWLEDGE"
    DELIVERY_POLICY = "DELIVERY_POLICY"
    RETURN_REFUND_POLICY = "RETURN_REFUND_POLICY"
    BRAND_TONE = "BRAND_TONE"
    SUPPORT_KNOWLEDGE = "SUPPORT_KNOWLEDGE"
    BUSINESS_GOAL = "BUSINESS_GOAL"
    HISTORICAL_DECISION = "HISTORICAL_DECISION"
    APPROVED_SUGGESTION = "APPROVED_SUGGESTION"


PROHIBITED_SOURCE_TYPES = {
    "TRANSACTION_EVENT",
    "RAW_WEBHOOK",
    "ORDER_LOG",
    "LIVE_METRIC_SNAPSHOT",
    "BI_AGGREGATION",
    "ANOMALY_STREAM",
}

PROHIBITED_PAYLOAD_KEYS = {
    "order_id",
    "transaction_id",
    "payment_intent_id",
    "metric_window",
    "calculated_rate",
    "p95_latency",
}


@dataclass
class IngestionRequest:
    business_id: int
    source_name: str
    source_type: str
    knowledge_type: str
    title: str
    content: str
    document_type: str = "POLICY"
    file_name: str | None = None
    file_url: str | None = None
    mime_type: str = "text/plain"
    metadata: dict[str, Any] | None = None


def _contains_prohibited_keys(payload: Any) -> str | None:
    """Recursively checks whether any dictionary in payload contains prohibited keys."""
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k in PROHIBITED_PAYLOAD_KEYS:
                return k
            if k in ("event_type", "source_type") and v in PROHIBITED_SOURCE_TYPES:
                return f"{k}:{v}"
            found = _contains_prohibited_keys(v)
            if found:
                return found
    elif isinstance(payload, (list, tuple, set)):
        for item in payload:
            found = _contains_prohibited_keys(item)
            if found:
                return found
    return None


def validate_domain_boundaries(source_type: str, metadata: dict[str, Any] | None = None, content: str = ""):
    """
    Validates that incoming knowledge does not violate domain boundary invariants:
    - Business Memory != Business Data (no transactional events/keys)
    - Business Memory != Business Intelligence (no live metrics/anomalies)
    """
    if source_type in PROHIBITED_SOURCE_TYPES:
        raise DomainBoundaryViolationError(
            f"Prohibited source type '{source_type}'. Business Memory does not store raw transactional events or live BI metrics."
        )

    meta = metadata or {}
    prohibited_match = _contains_prohibited_keys(meta)
    if prohibited_match:
        raise DomainBoundaryViolationError(
            f"Prohibited transactional or metric payload detected ('{prohibited_match}'). "
            f"Transactional entities and live metrics belong in Business Data / BI."
        )


def validate_tenant_isolation(business_id: Any, expected_business: Business | None = None) -> int:
    """
    Validates tenant isolation: business_id must be non-null and match expected tenant if provided.
    """
    if business_id is None:
        raise TenantIsolationError("Tenant isolation violation: business_id cannot be null.")
    try:
        b_id = int(business_id)
        if b_id <= 0:
            raise TenantIsolationError(f"Invalid business_id '{business_id}'. Must be a positive integer.")
    except (ValueError, TypeError) as e:
        raise TenantIsolationError(f"Invalid business_id '{business_id}'. Must be an integer.") from e

    if expected_business is not None and expected_business.id != b_id:
        raise TenantIsolationError(
            f"Cross-tenant violation: requested business_id '{b_id}' does not match context business '{expected_business.id}'."
        )
    return b_id


def register_knowledge_source(
    business: Business,
    name: str,
    source_type: str,
    knowledge_type: str | None = None,
    source_reference: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> KnowledgeSource:
    """
    Feature 11: Knowledge Sources.
    Registers a new knowledge source with source classification, tenant isolation,
    and domain boundary validation.
    """
    if business is None or not getattr(business, "id", None):
        raise TenantIsolationError("Tenant isolation violation: valid business instance required.")

    validate_tenant_isolation(business.id)
    validate_domain_boundaries(source_type, metadata)

    return KnowledgeSource.objects.create(
        business=business,
        name=name,
        source_type=source_type,
        knowledge_type=knowledge_type,
        status="ACTIVE",
        source_reference=source_reference,
        metadata=metadata or {},
    )


def ingest_document(
    business: Business,
    request: IngestionRequest,
) -> KnowledgeDocument:
    """
    Feature 12: Document Ingestion.
    Ingests textual/uploaded documents into the business memory pipeline.
    Enforces boundary guardrails, tenant isolation, and attaches to KnowledgeSource.
    """
    validate_tenant_isolation(request.business_id, expected_business=business)
    validate_domain_boundaries(request.source_type, request.metadata, request.content)

    # Resolve or create the associated KnowledgeSource
    source = KnowledgeSource.objects.filter(business=business, name=request.source_name).first()
    if source:
        if source.status == "ARCHIVED":
            raise DomainBoundaryViolationError(
                f"Cannot ingest documents into ARCHIVED knowledge source '{source.name}'."
            )
    else:
        source = KnowledgeSource.objects.create(
            business=business,
            name=request.source_name,
            source_type=request.source_type,
            knowledge_type=request.knowledge_type,
            status="ACTIVE",
            metadata=request.metadata or {},
        )

    now = timezone.now()
    return KnowledgeDocument.objects.create(
        business=business,
        knowledge_source=source,
        title=request.title,
        document_type=request.document_type,
        content=request.content,
        file_name=request.file_name,
        file_url=request.file_url,
        mime_type=request.mime_type,
        status="PENDING",
        version=1,
        metadata=request.metadata or {},
        ingested_at=now,
    )



def process_document(
    document: KnowledgeDocument,
) -> KnowledgeDocument:
    """
    Feature 13: Document Processing.
    Normalizes content, preserves structure, calculates SHA-256 hash for deduplication,
    validates content presence, and marks document as READY.
    """
    if not document.content or not document.content.strip():
        document.status = "FAILED"
        document.save(update_fields=["status"])
        return document

    # Clean and normalize text
    raw_content = document.content
    cleaned_content = raw_content.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Generate SHA-256 content hash
    content_hash = hashlib.sha256(cleaned_content.encode("utf-8")).hexdigest()

    # Check for deduplication against existing processed documents for this business
    existing = (
        KnowledgeDocument.objects.filter(
            business=document.business,
            content_hash=content_hash,
            status__in=["READY", "PUBLISHED"],
        )
        .exclude(id=document.id)
        .first()
    )

    metadata = document.metadata or {}
    if existing:
        metadata["is_duplicate"] = True
        metadata["duplicate_of_id"] = existing.id
    else:
        metadata["is_duplicate"] = False

    document.content = cleaned_content
    document.content_hash = content_hash
    document.status = "READY"
    document.metadata = metadata
    document.processed_at = timezone.now()
    document.save()

    return document


def chunk_document(
    document: KnowledgeDocument,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[KnowledgeChunk]:
    """
    Feature 14: Knowledge Chunking.
    Splits document content into ordered, section-aware, token-bounded chunks
    while preserving document and tenant associations.
    """
    if not document.content:
        return []

    # Section-aware splitting by markdown headings
    heading_pattern = r"(^#{1,4}\s+[^\n]+)"
    raw_sections = re.split(heading_pattern, document.content, flags=re.MULTILINE)

    sections = []
    current_heading = "General"
    i = 0
    while i < len(raw_sections):
        part = raw_sections[i].strip()
        if not part:
            i += 1
            continue
        if re.match(r"^#{1,4}\s+", part):
            current_heading = part.lstrip("#").strip()
            body = raw_sections[i + 1].strip() if i + 1 < len(raw_sections) else ""
            sections.append((current_heading, body))
            i += 2
        else:
            sections.append((current_heading, part))
            i += 1

    chunks_data: list[tuple[str, str]] = []
    for heading, body in sections:
        if not body:
            continue
        words = body.split()
        if len(words) <= chunk_size:
            chunks_data.append((heading, body))
        else:
            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_words = words[start:end]
                chunks_data.append((heading, " ".join(chunk_words)))
                if end == len(words):
                    break
                start += max(1, chunk_size - chunk_overlap)

    created_chunks = []
    for idx, (heading, chunk_text) in enumerate(chunks_data):
        approx_tokens = max(1, len(chunk_text.split()))
        chunk_meta = {
            "section": heading,
            "version": document.version,
            "is_current": (document.status in ["READY", "PUBLISHED"]),
            "content_hash": document.content_hash,
            **(document.metadata or {}),
        }
        chunk = KnowledgeChunk.objects.create(
            business=document.business,
            knowledge_document=document,
            chunk_index=idx,
            content=chunk_text,
            token_count=approx_tokens,
            metadata=chunk_meta,
        )
        created_chunks.append(chunk)

    return created_chunks


def bump_document_version(
    current_document: KnowledgeDocument,
    new_content: str,
    updated_title: str | None = None,
    updated_metadata: dict[str, Any] | None = None,
) -> KnowledgeDocument:
    """
    Feature 19: Knowledge Versioning.
    Creates a new sequential document version (v1 -> v2) and atomically supersedes
    the previous document and its associated chunks.
    """
    with transaction.atomic():
        locked_doc = (
            KnowledgeDocument.objects.select_for_update()
            .get(pk=current_document.pk)
        )
        # Mark previous document as SUPERSEDED
        locked_doc.status = "SUPERSEDED"
        locked_doc.save(update_fields=["status", "updated_at"])

        # Atomically mark previous chunks as non-current
        for chunk in locked_doc.knowledgechunk_set.select_for_update():
            meta = chunk.metadata or {}
            meta["is_current"] = False
            meta["superseded_at"] = timezone.now().isoformat()
            chunk.metadata = meta
            chunk.save(update_fields=["metadata", "updated_at"])

        # Create new version
        new_version = locked_doc.version + 1
        cleaned_content = new_content.replace("\r\n", "\n").strip()
        new_hash = hashlib.sha256(cleaned_content.encode("utf-8")).hexdigest()

        meta = updated_metadata or dict(locked_doc.metadata or {})
        meta["supersedes_version"] = locked_doc.version

        new_doc = KnowledgeDocument.objects.create(
            business=locked_doc.business,
            knowledge_source=locked_doc.knowledge_source,
            title=updated_title or locked_doc.title,
            document_type=locked_doc.document_type,
            content=cleaned_content,
            file_name=locked_doc.file_name,
            file_url=locked_doc.file_url,
            mime_type=locked_doc.mime_type,
            status="READY",
            version=new_version,
            content_hash=new_hash,
            metadata=meta,
            ingested_at=timezone.now(),
            processed_at=timezone.now(),
        )
        return new_doc


def resolve_active_version(
    business: Business,
    knowledge_source_id: int,
    target_version: int | None = None,
) -> KnowledgeDocument:
    """
    Feature 19: Active vs Historical Version Resolution.
    Resolves the authoritative active version. If an explicitly requested version
    is SUPERSEDED, raises StaleVersionError to prevent stale grounding.
    """
    if business is None:
        raise TenantIsolationError("Tenant isolation violation: business cannot be null.")

    if target_version is not None:
        doc = KnowledgeDocument.objects.filter(
            business=business,
            knowledge_source_id=knowledge_source_id,
            version=target_version,
        ).first()
        if not doc:
            raise KnowledgeDocument.DoesNotExist(
                f"KnowledgeDocument for source {knowledge_source_id} version {target_version} does not exist."
            )
        if doc.status == "SUPERSEDED":
            raise StaleVersionError(
                f"Requested document version {target_version} is SUPERSEDED and cannot be used as active context."
            )
        return doc

    # Default to latest active/ready version
    active_doc = (
        KnowledgeDocument.objects.filter(
            business=business,
            knowledge_source_id=knowledge_source_id,
            status__in=["READY", "PUBLISHED"],
        )
        .order_by("-version")
        .first()
    )
    if not active_doc:
        raise KnowledgeDocument.DoesNotExist(
            f"No active KnowledgeDocument found for source {knowledge_source_id}."
        )
    return active_doc
