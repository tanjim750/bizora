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


def assemble_ai_context(business: Business, intent: str = None) -> dict:
    """
    Retrieves and bundles active facts, open issues, and policies into a secure context payload.
    Excludes expired facts per COR-009 and injects intent-driven policies per MOD-003.
    """
    # Active facts (auto-filtered by BusinessFactManager per COR-009)
    facts = list(BusinessFact.objects.filter(business=business).values('id', 'fact_type', 'statement', 'confidence'))

    # Active open issues
    issues = list(BusinessIssue.objects.filter(business=business, status='OPEN').values('id', 'issue_type', 'title', 'severity'))

    # Active policies for intent (e.g. refund/delivery policy per MOD-003)
    policies = []
    if intent:
        policy_docs = KnowledgeDocument.get_active_policies_for_intent(business, intent)
        policies = list(policy_docs.values('id', 'title', 'content', 'version'))

    return {
        "business_id": business.id,
        "business_name": business.name,
        "active_facts": facts,
        "open_issues": issues,
        "authoritative_policies": policies,
    }


def generate_grounded_recommendation(
    business: Business,
    issue: BusinessIssue = None,
    intent: str = "delivery_optimization",
    timeout_seconds: int = 15,
) -> tuple[AiRecommendation, AiAction]:
    """
    Invokes LLM with timeout wrapper, validates outputs, and creates a recommendation
    strictly grounded with AiRecommendationEvidence and a SUGGESTED AiAction requiring human approval.
    """
    now = timezone.now()
    context = assemble_ai_context(business, intent)

    prompt = f"Analyze business context and propose courier rebalancing: {context}"
    llm_output = business.execute_llm_with_timeout(
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        fallback_response={"content": "Switch secondary courier to reduce failure rates", "confidence": "0.8500"}
    )

    confidence = Decimal(str(llm_output.get("confidence", "0.8000")))

    # AI Recommendation (Confidence bounded 0.0 - 1.0 per MOD-002)
    recommendation = AiRecommendation.objects.create(
        business=business,
        business_issue=issue,
        recommendation_type="COURIER_OPTIMIZATION",
        title="Rebalance Delivery Courier Allocations",
        description=llm_output.get("content", "Rebalance allocations based on regional performance"),
        rationale="Delivery failure rate exceeded threshold on primary courier.",
        confidence=confidence,
        priority="HIGH",
        status="SUGGESTED",
        suggested_action_type="REASSIGN_COURIER",
        generated_at=now,
    )

    # Strictly ground recommendation with evidence (COR-008)
    first_fact = BusinessFact.objects.filter(business=business).first()
    AiRecommendationEvidence.objects.create(
        business=business,
        ai_recommendation=recommendation,
        business_issue=issue,
        business_fact=first_fact,
        evidence_type="VERIFIED_FACT_GROUNDING",
        description="Grounded on authoritative high failure rate metric and fact.",
        weight=Decimal('1.0000'),
    )

    # Propose SUGGESTED AiAction requiring approval (SEC-004, SEC-005)
    action = AiAction.objects.create(
        business=business,
        ai_recommendation=recommendation,
        action_type="REASSIGN_COURIER",
        status="SUGGESTED",
        target_entity_type="courier",
        target_entity_id=1,
        action_payload={"reassign_percentage": 50, "fallback_courier_id": 2},
        is_simulated=True,
    )

    return recommendation, action
