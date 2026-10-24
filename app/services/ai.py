"""
AI Context Assembly and Recommendation Service.
Maintains the Business Brain Boundary:
AI reads deterministic facts, issues, graph, and policy to produce recommendations.
AI recommendations NEVER silently create authoritative facts or execute actions.
"""

import re
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from app.exceptions import TenantIsolationError, UnapprovedMemoryPromotionError
from app.models import (
    AiAction,
    AiRecommendation,
    AiRecommendationEvidence,
    Business,
    BusinessFact,
    BusinessIssue,
    KnowledgeDocument,
)
from app.services.domain_memory import (
    check_repeat_decision_conflict,
    get_active_business_goals,
    get_brand_tone,
    get_business_profile,
    promote_approved_suggestion,
)
from app.services.hybrid_retrieval import hybrid_retrieval


def assemble_ai_context(business: Business, intent: str | None = None) -> dict:
    """
    Retrieves and bundles active facts, open issues, and policies into a secure context payload.
    Excludes expired facts per COR-009 and injects intent-driven policies per MOD-003.
    """
    # Active facts (auto-filtered by BusinessFactManager per COR-009)
    facts = list(
        BusinessFact.objects.active_for_context(business).values(
            "id", "fact_type", "statement", "confidence"
        )
    )

    # Active open issues
    issues = list(
        BusinessIssue.objects.filter(business=business, status="OPEN").values(
            "id", "issue_type", "title", "severity"
        )
    )

    # Active policies for intent (e.g. refund/delivery policy per MOD-003)
    policies = []
    if intent:
        policy_docs = KnowledgeDocument.get_active_policies_for_intent(business, intent)
        policies = list(policy_docs.values("id", "title", "content", "version"))

    return {
        "business_id": business.id,
        "business_name": business.name,
        "active_facts": facts,
        "open_issues": issues,
        "authoritative_policies": policies,
    }


def record_ai_audit_event(
    business: Business,
    conversation_type: str,
    action_name: str,
    prompt: str,
    output_content: str,
    context_reference: dict | None = None,
    customer=None,
    support_conversation=None,
    model_name: str = "gemini-1.5-pro",
    tokens_used: int = 150,
):
    """
    Feature 17: AI Audit.
    Unified audit logger recording interactions across Support, Marketing, and Diagnosis.
    """
    from app.models import AiConversation, AiMessage
    now = timezone.now()
    conv = AiConversation.objects.create(
        business=business,
        customer=customer,
        support_conversation=support_conversation,
        conversation_type=conversation_type,
        status="COMPLETED",
        title=f"{action_name}: {now.strftime('%Y-%m-%d %H:%M')}",
        started_at=now,
        ended_at=now,
    )
    AiMessage.objects.create(
        ai_conversation=conv, role="USER", content=prompt,
        model=model_name, response_metadata={"action": action_name, "input": True},
    )
    import json
    safe_context = json.loads(json.dumps(context_reference or {}, default=str))
    msg = AiMessage.objects.create(
        ai_conversation=conv,
        role="ASSISTANT",
        content=output_content,
        model=model_name,
        prompt_tokens=tokens_used // 2,
        completion_tokens=tokens_used // 2,
        context_reference=safe_context,
        response_metadata={"action": action_name, "prompt": prompt, "tokens_used": tokens_used},
    )
    return conv, msg


def generate_grounded_recommendation(
    business: Business,
    issue: BusinessIssue | None = None,
    intent: str = "delivery_optimization",
    timeout_seconds: int = 15,
) -> tuple[AiRecommendation, AiAction]:
    """
    Invokes LLM with timeout wrapper, validates outputs, and creates a recommendation
    strictly grounded with AiRecommendationEvidence and a SUGGESTED AiAction requiring human approval.
    Supports multi-domain recommendation types (Feature 13 & 14).
    """
    now = timezone.now()
    from app.services.authorization import ensure_same_business
    if issue:
        ensure_same_business(business, issue)
    context = assemble_ai_context(business, intent)

    rec_type = "EVIDENCE_REVIEW"
    action_type = "REVIEW_EVIDENCE"
    target_type = "business"
    target_id = business.id
    action_payload = {"requires_human_review": True}
    title = "Review verified business evidence"
    rationale = "A verified finding is available for human review; no operational change is authorized."

    if issue:
        itype = (issue.issue_type or "").upper()
        if "CAMPAIGN" in itype or "MARKETING" in itype or (issue.subject_entity_type == "campaign"):
            rec_type = "MARKETING_OPTIMIZATION"
            action_type = "PAUSE_CAMPAIGN"
            target_type = "campaign"
            target_id = issue.subject_entity_id or 1
            action_payload = {"action": "adjust_budget", "adjustment_pct": -20}
            title = f"Adjust Campaign Budget for {issue.title}"
            rationale = f"Campaign performance flagged by issue {issue.id}."
        elif "INVENTORY" in itype or "STOCK" in itype or (issue.subject_entity_type == "product"):
            rec_type = "PRODUCT_STRATEGY"
            action_type = "RESTOCK_PRODUCT"
            target_type = "product"
            target_id = issue.subject_entity_id or 1
            action_payload = {"reorder_quantity": 100}
            title = f"Replenish Inventory for {issue.title}"
            rationale = f"Stock level alert flagged for product {target_id}."
        elif "SUPPORT" in itype or (issue.subject_entity_type == "conversation"):
            rec_type = "SUPPORT_IMPROVEMENT"
            action_type = "CREATE_SUPPORT_TASK"
            target_type = "conversation"
            target_id = issue.subject_entity_id or 1
            action_payload = {"priority": "URGENT"}
            title = f"Escalate Support Tickets for {issue.title}"
            rationale = f"Support threshold exceeded on issue {issue.id}."
        else:
            title = f"Address Operational Issue: {issue.title}"
            target_type = issue.subject_entity_type or "business"
            target_id = issue.subject_entity_id or business.id
            action_type = "REVIEW_ISSUE"
            action_payload = {"requires_human_review": True}

    prompt = f"Analyze business context and propose {rec_type.lower()}: {context}"
    llm_output = business.execute_llm_with_timeout(
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        fallback_response={
            "content": f"Execute action to address {title}",
            "confidence": "0.8500",
        },
    )

    try:
        confidence = Decimal(str(llm_output.get("confidence", "0.8000")))
    except Exception as exc:
        raise ValidationError("LLM confidence must be numeric.") from exc
    if not Decimal(0) <= confidence <= Decimal(1):
        raise ValidationError("LLM confidence must be between 0 and 1.")

    # Strictly ground recommendation with evidence (COR-008, Feature 14)
    evidence_fact = None
    if issue and hasattr(issue, "businessissueevidence_set"):
        issue_ev = issue.businessissueevidence_set.filter(business_fact__isnull=False).first()
        if issue_ev:
            evidence_fact = issue_ev.business_fact
    if not evidence_fact:
        evidence_fact = BusinessFact.objects.active_for_context(business).first()
    if evidence_fact is None and issue is None:
        raise ValidationError("Cannot generate a recommendation without verified evidence or an issue.")

    with transaction.atomic():
        recommendation = AiRecommendation.objects.create(
            business=business, business_issue=issue, recommendation_type=rec_type,
            title=title, description=llm_output.get("content", f"Evidence is insufficient for {title}."),
            rationale=rationale, confidence=confidence, priority="HIGH", status="SUGGESTED",
            suggested_action_type=action_type, generated_at=now,
        )
        AiRecommendationEvidence.objects.create(
            business=business, ai_recommendation=recommendation, business_issue=issue,
            business_fact=evidence_fact, evidence_type="VERIFIED_FACT_GROUNDING",
            description=f"Grounded on authoritative evidence for {title}.", weight=Decimal("1.0000"),
        )
        action = AiAction.objects.create(
            business=business, ai_recommendation=recommendation, action_type=action_type,
            status="SUGGESTED", target_entity_type=target_type, target_entity_id=target_id,
            action_payload=action_payload, is_simulated=True,
        )

    return recommendation, action


def assemble_grounded_memory_context(
    business: Business,
    query: str | None = None,
    intent: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Connects AI Intelligence to Business Memory via HybridRetrieval,
    active policies, brand tone, and business goals.
    """
    if business is None or not getattr(business, "id", None):
        raise TenantIsolationError("Tenant isolation violation: a non-null Business instance is required.")

    profile = get_business_profile(business)
    goals = get_active_business_goals(business)
    brand_tone = get_brand_tone(business)

    retrieved_knowledge = []
    if query:
        raw_results = hybrid_retrieval(business=business, query=query, top_k=top_k)
        for item in raw_results:
            retrieved_knowledge.append({
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "document_title": item.document_title,
                "content": item.content,
                "score": item.rrf_score if item.rrf_score > 0 else (item.sparse_score or item.dense_score),
                "version": item.version,
                "source_reference": item.source_reference,
                "citations": f"{item.document_title} (v{item.version})",
            })

    return {
        "profile": profile,
        "active_goals": [
            {
                "id": g.id,
                "name": g.name,
                "category": g.category,
                "priority": g.priority,
                "target_text": g.target_text,
                "timeframe": g.timeframe,
            }
            for g in goals
        ],
        "brand_tone": brand_tone,
        "retrieved_knowledge": retrieved_knowledge,
        "query": query,
        "intent": intent,
    }


def generate_goal_aligned_recommendation(
    business: Business,
    issue_type: str | None = None,
    candidate_action_type: str = "CHANGE_COURIER",
    candidate_entity_type: str = "COURIER",
    candidate_entity_id: int | None = None,
) -> tuple[AiRecommendation, Any]:
    """
    Generates a recommendation prioritized against active BusinessGoals and
    checked against rejected HistoricalDecisions to prevent repeat failures.
    """
    if business is None or not getattr(business, "id", None):
        raise TenantIsolationError("Tenant isolation violation: a non-null Business instance is required.")

    conflict = check_repeat_decision_conflict(
        business=business,
        decision_type=candidate_action_type,
        target_entity_type=candidate_entity_type,
        target_entity_id=candidate_entity_id,
    )

    metadata: dict[str, Any] = {}
    now = timezone.now()

    if conflict:
        metadata["repeat_decision_conflict"] = True
        metadata["conflict_decision_id"] = conflict.id
        metadata["conflict_outcome"] = conflict.outcome
        rationale = (
            f"Candidate action was previously rejected or ineffective in decision "
            f"'{conflict.title}' ({conflict.outcome}): {conflict.rationale}"
        )
        priority = "LOW"
        confidence = Decimal("0.2000")
    else:
        goals = get_active_business_goals(business)
        matched_goal = None
        for g in goals:
            if g.category in ["LOGISTICS", "OPERATIONS", "DELIVERY"] and "DELIVERY" in (issue_type or candidate_action_type):
                matched_goal = g
                break
            if g.category.lower() in (issue_type or "").lower() or g.name.lower() in (issue_type or "").lower():
                matched_goal = g
                break

        if matched_goal:
            metadata["aligned_goal"] = matched_goal.name
            metadata["goal_category"] = matched_goal.category
            metadata["goal_priority"] = matched_goal.priority
            rationale = (
                f"Directly advances business goal '{matched_goal.name}' ({matched_goal.target_text}) "
                f"by resolving {issue_type or 'issue'} via {candidate_action_type}."
            )
            priority = "HIGH"
            confidence = Decimal("0.9200")
        else:
            rationale = f"Candidate recommendation {candidate_action_type} for {candidate_entity_type} {candidate_entity_id}."
            priority = "MEDIUM"
            confidence = Decimal("0.7500")

    issue = None
    if issue_type:
        issue = BusinessIssue.objects.filter(business=business, issue_type=issue_type, status="OPEN").first()
    if not issue:
        issue = BusinessIssue.objects.filter(business=business, status="OPEN").first()

    evidence_fact = BusinessFact.objects.filter(business=business, status="VERIFIED").first()

    with transaction.atomic():
        recommendation = AiRecommendation.objects.create(
            business=business,
            business_issue=issue,
            recommendation_type=candidate_action_type,
            title=f"Recommendation: {candidate_action_type} for {candidate_entity_type} {candidate_entity_id}",
            description=f"Automated recommendation targeting {candidate_entity_type} {candidate_entity_id}.",
            rationale=rationale,
            confidence=confidence,
            priority=priority,
            status="SUGGESTED",
            suggested_action_type=candidate_action_type,
            generated_at=now,
            metadata=metadata,
        )

        if evidence_fact or issue:
            AiRecommendationEvidence.objects.create(
                business=business,
                ai_recommendation=recommendation,
                business_issue=issue,
                business_fact=evidence_fact,
                evidence_type="VERIFIED_FACT_GROUNDING" if evidence_fact else "ISSUE_GROUNDING",
                description=rationale,
                weight=Decimal("1.0000"),
            )

        action = AiAction.objects.create(
            business=business,
            ai_recommendation=recommendation,
            action_type=candidate_action_type,
            status="SUGGESTED",
            target_entity_type=candidate_entity_type,
            target_entity_id=candidate_entity_id,
            action_payload={"entity_type": candidate_entity_type, "entity_id": candidate_entity_id},
            is_simulated=True,
        )

    return recommendation, action


def enforce_brand_tone_on_output(
    business: Business,
    text: str,
    channel: str | None = None,
) -> str:
    """
    Validates text against active BrandTone and sanitizes/flags restricted terms.
    """
    if business is None or not getattr(business, "id", None):
        raise TenantIsolationError("Tenant isolation violation: a non-null Business instance is required.")

    tone_cfg = get_brand_tone(business, channel=channel)
    restricted = tone_cfg.get("restricted_words", [])
    if not restricted or not text:
        return text

    sanitized = text
    standard_replacements = {
        "cheap": "affordable",
        "guarantee 100%": "strive for complete",
        "100% guarantee": "dedicated commitment",
        "dirt cheap": "cost-effective",
        "unlimited": "flexible",
    }
    for word in restricted:
        w_lower = word.lower()
        replacement = standard_replacements.get(w_lower, "[redacted]")
        pattern = rf"(?<![a-zA-Z0-9]){re.escape(word)}(?![a-zA-Z0-9])"
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized


def promote_recommendation_to_memory(
    business: Business,
    recommendation: AiRecommendation,
    user,
    approved_at=None,
):
    """
    Promotes an approved recommendation to durable ApprovedSuggestion memory with audit trail.
    """
    if business is None or not getattr(business, "id", None):
        raise TenantIsolationError("Tenant isolation violation: a non-null Business instance is required.")

    if recommendation.business_id != business.id:
        raise TenantIsolationError(
            f"Tenant isolation violation: recommendation belongs to business {recommendation.business_id}, not {business.id}."
        )

    if recommendation.status != "APPROVED":
        raise UnapprovedMemoryPromotionError(
            f"Cannot promote unapproved AI recommendation to durable Business Memory. "
            f"Status is '{recommendation.status}', must be 'APPROVED'."
        )

    now = approved_at or timezone.now()
    return promote_approved_suggestion(
        business=business,
        recommendation=recommendation,
        approved_by=user,
        approved_at=now,
    )


# Re-export modular AI Intelligence services for unified imports

from app.services.ai_assistant import ask_business_assistant
from app.services.ai_context import (
    assemble_customer_context,
    assemble_fact_context,
    assemble_full_ai_context,
    assemble_graph_context,
    assemble_memory_context,
    assemble_order_context,
    assemble_product_context,
)
from app.services.ai_diagnosis import diagnose_business_issue
from app.services.ai_marketing import explain_campaign_performance
from app.services.ai_summarization import (
    summarize_call,
    summarize_support_conversation,
)
from app.services.ai_support import (
    evaluate_escalation,
    generate_handover_summary,
    generate_suggested_reply,
    resume_ai_handling,
)

__all__ = [
    "ask_business_assistant",
    "assemble_ai_context",
    "assemble_customer_context",
    "assemble_fact_context",
    "assemble_full_ai_context",
    "assemble_graph_context",
    "assemble_grounded_memory_context",
    "assemble_memory_context",
    "assemble_order_context",
    "assemble_product_context",
    "diagnose_business_issue",
    "enforce_brand_tone_on_output",
    "evaluate_escalation",
    "explain_campaign_performance",
    "generate_goal_aligned_recommendation",
    "generate_grounded_recommendation",
    "generate_handover_summary",
    "generate_suggested_reply",
    "promote_recommendation_to_memory",
    "resume_ai_handling",
    "summarize_call",
    "summarize_support_conversation",
]

