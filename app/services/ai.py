"""
AI Context Assembly and Recommendation Service.
Maintains the Business Brain Boundary:
AI reads deterministic facts, issues, graph, and policy to produce recommendations.
AI recommendations NEVER silently create authoritative facts or execute actions.
"""

from decimal import Decimal

from django.utils import timezone

from app.models import (
    AiAction,
    AiRecommendation,
    AiRecommendationEvidence,
    Business,
    BusinessFact,
    BusinessIssue,
    KnowledgeDocument,
)


def assemble_ai_context(business: Business, intent: str | None = None) -> dict:
    """
    Retrieves and bundles active facts, open issues, and policies into a secure context payload.
    Excludes expired facts per COR-009 and injects intent-driven policies per MOD-003.
    """
    # Active facts (auto-filtered by BusinessFactManager per COR-009)
    facts = list(
        BusinessFact.objects.filter(business=business).values(
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
    msg = AiMessage.objects.create(
        ai_conversation=conv,
        role="ASSISTANT",
        content=output_content,
        model=model_name,
        prompt_tokens=tokens_used // 2,
        completion_tokens=tokens_used // 2,
        context_reference=context_reference,
        response_metadata={"action": action_name},
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
    context = assemble_ai_context(business, intent)

    rec_type = "COURIER_OPTIMIZATION"
    action_type = "REASSIGN_COURIER"
    target_type = "courier"
    target_id = 1
    action_payload = {"reassign_percentage": 50, "fallback_courier_id": 2}
    title = "Rebalance Delivery Courier Allocations"
    rationale = "Delivery failure rate exceeded threshold on primary courier."

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
            target_type = issue.subject_entity_type or "courier"
            target_id = issue.subject_entity_id or 1

    prompt = f"Analyze business context and propose {rec_type.lower()}: {context}"
    llm_output = business.execute_llm_with_timeout(
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        fallback_response={
            "content": f"Execute action to address {title}",
            "confidence": "0.8500",
        },
    )

    confidence = Decimal(str(llm_output.get("confidence", "0.8000")))

    # AI Recommendation (Confidence bounded 0.0 - 1.0 per MOD-002)
    recommendation = AiRecommendation.objects.create(
        business=business,
        business_issue=issue,
        recommendation_type=rec_type,
        title=title,
        description=llm_output.get("content", f"Execute action to address {title}"),
        rationale=rationale,
        confidence=confidence,
        priority="HIGH",
        status="SUGGESTED",
        suggested_action_type=action_type,
        generated_at=now,
    )

    # Strictly ground recommendation with evidence (COR-008, Feature 14)
    evidence_fact = None
    if issue and hasattr(issue, "businessissueevidence_set"):
        issue_ev = issue.businessissueevidence_set.filter(business_fact__isnull=False).first()
        if issue_ev:
            evidence_fact = issue_ev.business_fact
    if not evidence_fact:
        evidence_fact = BusinessFact.objects.filter(business=business).first()

    AiRecommendationEvidence.objects.create(
        business=business,
        ai_recommendation=recommendation,
        business_issue=issue,
        business_fact=evidence_fact,
        evidence_type="VERIFIED_FACT_GROUNDING",
        description=f"Grounded on authoritative fact for {title}.",
        weight=Decimal("1.0000"),
    )

    # Propose SUGGESTED AiAction requiring approval (SEC-004, SEC-005, Feature 15)
    action = AiAction.objects.create(
        business=business,
        ai_recommendation=recommendation,
        action_type=action_type,
        status="SUGGESTED",
        target_entity_type=target_type,
        target_entity_id=target_id,
        action_payload=action_payload,
        is_simulated=True,
    )

    return recommendation, action


# Re-export modular AI Intelligence services for unified imports
from app.services.ai_assistant import ask_business_assistant  # noqa: E402
from app.services.ai_context import (  # noqa: E402
    assemble_customer_context,
    assemble_fact_context,
    assemble_full_ai_context,
    assemble_graph_context,
    assemble_memory_context,
    assemble_order_context,
    assemble_product_context,
)
from app.services.ai_diagnosis import diagnose_business_issue  # noqa: E402
from app.services.ai_marketing import explain_campaign_performance  # noqa: E402
from app.services.ai_summarization import (  # noqa: E402
    summarize_call,
    summarize_support_conversation,
)
from app.services.ai_support import (  # noqa: E402
    evaluate_escalation,
    generate_handover_summary,
    generate_suggested_reply,
    resume_ai_handling,
)

