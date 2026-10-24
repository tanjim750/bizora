"""
Structured Domain Memory & Governance Services (Features 1-10).
Production-grade implementation of Business Profile, Policies, Product Knowledge,
Delivery Policy, Return & Refund Policy, Brand Tone, Support Knowledge,
Business Goals, Historical Decisions, and Human-in-the-Loop Approved Suggestions.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone

from app.exceptions import TenantIsolationError, UnapprovedMemoryPromotionError
from app.models import (
    AiRecommendation,
    ApprovedSuggestion,
    Business,
    BusinessGoal,
    BusinessMemory,
    HistoricalDecision,
    Product,
)

User = get_user_model()


@dataclass
class BusinessProfileData:
    name: str
    description: str
    industry: str
    operating_regions: list[str]
    target_customers: str
    operating_model: dict[str, Any]
    ai_context_summary: str
    source_tracking: str = "MANUAL_ENTRY"


@dataclass
class DeliveryPolicyData:
    coverage_zones: list[str]
    sla_hours: dict[str, int]
    charges: dict[str, float]
    courier_preferences: list[str]
    cod_rules: dict[str, Any]
    failed_delivery_handling: str


@dataclass
class ReturnRefundPolicyData:
    return_window_days: int
    eligible_conditions: list[str]
    non_returnable_conditions: list[str]
    refund_methods: list[str]
    replacement_allowed: bool
    cancellation_cutoff_hours: int


@dataclass
class BrandToneData:
    primary_tone: str
    style_guidelines: list[str]
    preferred_terms: list[str]
    restricted_words: list[str]
    channel_overrides: dict[str, dict[str, Any]]


def _require_valid_business(business: Business) -> Business:
    if business is None or not getattr(business, "id", None):
        raise TenantIsolationError("Tenant isolation violation: a non-null Business instance is required.")
    return business


# ─────────────────────────────────────────────────────────────
# Feature 1: Business Profile
# ─────────────────────────────────────────────────────────────

def set_business_profile(business: Business, profile: BusinessProfileData) -> BusinessMemory:
    _require_valid_business(business)
    with transaction.atomic():
        # Deactivate old profile versions
        BusinessMemory.objects.filter(
            business=business, memory_type="BUSINESS_PROFILE", is_active=True
        ).update(is_active=False)

        return BusinessMemory.objects.create(
            business=business,
            memory_type="BUSINESS_PROFILE",
            content=profile.description,
            metadata=asdict(profile),
            source_reference=profile.source_tracking,
            is_active=True,
        )


def get_business_profile(business: Business) -> dict[str, Any]:
    _require_valid_business(business)
    mem = (
        BusinessMemory.objects.filter(
            business=business, memory_type="BUSINESS_PROFILE", is_active=True
        )
        .order_by("-created_at")
        .first()
    )
    if not mem:
        return {
            "name": business.name,
            "description": "",
            "industry": "General",
            "operating_regions": [],
            "target_customers": "",
            "operating_model": {},
            "ai_context_summary": f"Operating profile for {business.name}.",
        }
    return mem.metadata or {}


# ─────────────────────────────────────────────────────────────
# Feature 2: Business Policies
# ─────────────────────────────────────────────────────────────

def set_business_policy(
    business: Business,
    policy_category: str,
    title: str,
    content: str,
    applicability: str = "ALL",
    metadata: dict[str, Any] | None = None,
) -> BusinessMemory:
    _require_valid_business(business)
    meta = {
        "category": policy_category,
        "title": title,
        "applicability": applicability,
        **(metadata or {}),
    }
    return BusinessMemory.objects.create(
        business=business,
        memory_type="BUSINESS_POLICY",
        content=content,
        metadata=meta,
        is_active=True,
    )


def get_active_policies(business: Business, policy_category: str | None = None) -> list[BusinessMemory]:
    _require_valid_business(business)
    qs = BusinessMemory.objects.filter(
        business=business, memory_type="BUSINESS_POLICY", is_active=True
    ).order_by("-created_at")
    if policy_category:
        qs = qs.filter(metadata__category=policy_category)
    return list(qs)


# ─────────────────────────────────────────────────────────────
# Feature 3: Product Knowledge
# ─────────────────────────────────────────────────────────────

def set_product_knowledge(
    business: Business,
    product: Product,
    knowledge_type: str,
    title: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> BusinessMemory:
    _require_valid_business(business)
    if product.business_id != business.id:
        raise TenantIsolationError("Product does not belong to the specified business tenant.")

    meta = {
        "knowledge_type": knowledge_type,
        "title": title,
        "product_sku": product.sku,
        "product_name": product.name,
        **(metadata or {}),
    }
    return BusinessMemory.objects.create(
        business=business,
        memory_type="PRODUCT_KNOWLEDGE",
        subject_entity_type="PRODUCT",
        subject_entity_id=product.id,
        content=content,
        metadata=meta,
        is_active=True,
    )


def get_product_knowledge(business: Business, product_id: int) -> list[BusinessMemory]:
    _require_valid_business(business)
    return list(
        BusinessMemory.objects.filter(
            business=business,
            memory_type="PRODUCT_KNOWLEDGE",
            subject_entity_type="PRODUCT",
            subject_entity_id=product_id,
            is_active=True,
        ).order_by("-created_at")
    )


# ─────────────────────────────────────────────────────────────
# Feature 4: Delivery Policy
# ─────────────────────────────────────────────────────────────

def set_delivery_policy(business: Business, policy: DeliveryPolicyData) -> BusinessMemory:
    _require_valid_business(business)
    with transaction.atomic():
        BusinessMemory.objects.filter(
            business=business, memory_type="DELIVERY_POLICY", is_active=True
        ).update(is_active=False)

        return BusinessMemory.objects.create(
            business=business,
            memory_type="DELIVERY_POLICY",
            content=policy.failed_delivery_handling,
            metadata=asdict(policy),
            is_active=True,
        )


def get_delivery_policy(business: Business) -> dict[str, Any]:
    _require_valid_business(business)
    mem = (
        BusinessMemory.objects.filter(
            business=business, memory_type="DELIVERY_POLICY", is_active=True
        )
        .order_by("-created_at")
        .first()
    )
    if not mem:
        return {}
    return mem.metadata or {}


# ─────────────────────────────────────────────────────────────
# Feature 5: Return & Refund Policy
# ─────────────────────────────────────────────────────────────

def set_return_refund_policy(business: Business, policy: ReturnRefundPolicyData) -> BusinessMemory:
    _require_valid_business(business)
    with transaction.atomic():
        BusinessMemory.objects.filter(
            business=business, memory_type="RETURN_REFUND_POLICY", is_active=True
        ).update(is_active=False)

        return BusinessMemory.objects.create(
            business=business,
            memory_type="RETURN_REFUND_POLICY",
            content=f"Return window is {policy.return_window_days} days. Eligible: {', '.join(policy.eligible_conditions)}.",
            metadata=asdict(policy),
            is_active=True,
        )


def get_return_refund_policy(business: Business) -> dict[str, Any]:
    _require_valid_business(business)
    mem = (
        BusinessMemory.objects.filter(
            business=business, memory_type="RETURN_REFUND_POLICY", is_active=True
        )
        .order_by("-created_at")
        .first()
    )
    if not mem:
        return {}
    return mem.metadata or {}


# ─────────────────────────────────────────────────────────────
# Feature 6: Brand Tone
# ─────────────────────────────────────────────────────────────

def set_brand_tone(business: Business, tone: BrandToneData) -> BusinessMemory:
    _require_valid_business(business)
    with transaction.atomic():
        BusinessMemory.objects.filter(
            business=business, memory_type="BRAND_TONE", is_active=True
        ).update(is_active=False)

        return BusinessMemory.objects.create(
            business=business,
            memory_type="BRAND_TONE",
            content=tone.primary_tone,
            metadata=asdict(tone),
            is_active=True,
        )


def get_brand_tone(business: Business, channel: str | None = None) -> dict[str, Any]:
    _require_valid_business(business)
    mem = (
        BusinessMemory.objects.filter(
            business=business, memory_type="BRAND_TONE", is_active=True
        )
        .order_by("-created_at")
        .first()
    )
    if not mem:
        return {
            "primary_tone": "Polite, professional, concise",
            "style_guidelines": [],
            "preferred_terms": [],
            "restricted_words": [],
            "channel_overrides": {},
        }
    data = dict(mem.metadata or {})
    if channel and "channel_overrides" in data:
        channel_upper = channel.upper()
        if channel_upper in data["channel_overrides"]:
            override = data["channel_overrides"][channel_upper]
            data.update(override)
    return data


def validate_text_against_brand_tone(business: Business, text: str, channel: str | None = None) -> list[str]:
    tone_cfg = get_brand_tone(business, channel=channel)
    restricted = tone_cfg.get("restricted_words", [])
    violations = []
    text_lower = text.lower()
    for word in restricted:
        w_lower = word.lower()
        pattern = rf"(?<![a-zA-Z0-9]){re.escape(w_lower)}(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            violations.append(word)
    return violations


# ─────────────────────────────────────────────────────────────
# Feature 7: Support Knowledge
# ─────────────────────────────────────────────────────────────

def set_support_knowledge(
    business: Business,
    category: str,
    question_or_topic: str,
    approved_answer: str,
    troubleshooting_tree: dict[str, Any] | None = None,
    escalation_team: str | None = None,
) -> BusinessMemory:
    _require_valid_business(business)
    meta = {
        "category": category,
        "question_or_topic": question_or_topic,
        "troubleshooting_tree": troubleshooting_tree or {},
        "escalation_team": escalation_team,
    }
    return BusinessMemory.objects.create(
        business=business,
        memory_type="SUPPORT_KNOWLEDGE",
        content=approved_answer,
        metadata=meta,
        is_active=True,
    )


def get_support_knowledge(business: Business, category: str | None = None) -> list[BusinessMemory]:
    _require_valid_business(business)
    qs = BusinessMemory.objects.filter(
        business=business, memory_type="SUPPORT_KNOWLEDGE", is_active=True
    ).order_by("-created_at")
    if category:
        qs = qs.filter(metadata__category=category)
    return list(qs)


# ─────────────────────────────────────────────────────────────
# Feature 8: Business Goals
# ─────────────────────────────────────────────────────────────

def set_business_goal(
    business: Business,
    name: str,
    category: str,
    priority: str,
    target_value: str,
    timeframe: str,
) -> BusinessGoal:
    _require_valid_business(business)
    return BusinessGoal.objects.create(
        business=business,
        name=name,
        category=category,
        priority=priority.upper(),
        target_text=target_value,
        timeframe=timeframe,
        status="ACTIVE",
    )



def get_active_business_goals(business: Business, category: str | None = None) -> list[BusinessGoal]:
    _require_valid_business(business)
    priority_order = models.Case(
        models.When(priority="HIGH", then=models.Value(1)),
        models.When(priority="MEDIUM", then=models.Value(2)),
        models.When(priority="LOW", then=models.Value(3)),
        default=models.Value(4),
        output_field=models.IntegerField(),
    )
    qs = BusinessGoal.objects.filter(business=business, status="ACTIVE").annotate(
        p_order=priority_order
    ).order_by("p_order", "-created_at")
    if category:
        qs = qs.filter(category=category)
    return list(qs)


# ─────────────────────────────────────────────────────────────
# Feature 9: Historical Decisions
# ─────────────────────────────────────────────────────────────

def record_historical_decision(
    business: Business,
    decision_type: str,
    title: str,
    rationale: str,
    outcome: str,
    context: dict[str, Any] | None = None,
    target_entity_type: str | None = None,
    target_entity_id: int | None = None,
    decided_by=None,
    decided_at=None,
) -> HistoricalDecision:
    _require_valid_business(business)
    now = decided_at or timezone.now()
    return HistoricalDecision.objects.create(
        business=business,
        decision_type=decision_type,
        title=title,
        rationale=rationale,
        outcome=outcome.upper(),
        context=context or {},
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        decided_by=decided_by,
        decided_at=now,
    )


def check_repeat_decision_conflict(
    business: Business,
    decision_type: str,
    target_entity_type: str | None = None,
    target_entity_id: int | None = None,
) -> HistoricalDecision | None:
    _require_valid_business(business)
    qs = HistoricalDecision.objects.filter(
        business=business,
        decision_type=decision_type,
        outcome__in=["REJECTED", "INEFFECTIVE", "FAILED"],
    )
    if target_entity_type:
        qs = qs.filter(target_entity_type=target_entity_type)
    if target_entity_id:
        qs = qs.filter(target_entity_id=target_entity_id)

    return qs.order_by("-decided_at").first()


# ─────────────────────────────────────────────────────────────
# Feature 10: Approved Suggestions
# ─────────────────────────────────────────────────────────────

def promote_approved_suggestion(
    business: Business,
    recommendation: AiRecommendation,
    approved_by,
    approved_at,
) -> ApprovedSuggestion:
    _require_valid_business(business)

    if recommendation.business_id != business.id:
        raise TenantIsolationError(
            f"Cross-tenant violation: recommendation belongs to business {recommendation.business_id}, not {business.id}."
        )

    # Mandatory Human-in-the-Loop Governance Gate
    if (
        not approved_by
        or not approved_at
        or recommendation.status != "APPROVED"
    ):
        raise UnapprovedMemoryPromotionError(
            "Cannot promote unapproved AI recommendation to durable Business Memory. "
            "A recommendation must be explicitly human-approved (status='APPROVED', approved_by, approved_at)."
        )


    # Check for existing promotion
    existing = ApprovedSuggestion.objects.filter(
        business=business,
        ai_recommendation=recommendation,
    ).first()
    if existing:
        return existing

    return ApprovedSuggestion.objects.create(
        business=business,
        ai_recommendation=recommendation,
        suggestion_type=recommendation.recommendation_type,
        title=recommendation.title,
        suggestion=recommendation.description,
        approved_by=approved_by,
        approved_at=approved_at,
        status="APPROVED",
        context=recommendation.metadata or {},
    )
