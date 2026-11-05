"""
Business Diagnosis Service (Feature 4).
Converts structured Business Issues into plain-language diagnoses,
explores root context across graph paths and metrics,
and identifies contributing factors without assuming causality.
"""

import json
from typing import Any

from django.utils import timezone

from app.models import Business, BusinessIssue
from app.services.ai_context import assemble_fact_context, assemble_graph_context


def diagnose_business_issue(
    business: Business,
    issue: BusinessIssue,
) -> dict[str, Any]:
    """
    Feature 4: Business Diagnosis.
    Explores issue evidence, traverses connected graph entities, identifies contributing factors,
    and produces a concise diagnostic overview.
    """
    from app.services.authorization import ensure_same_business
    ensure_same_business(business, issue)
    if hasattr(issue, "businessissueevidence_set"):
        evidence_records = issue.businessissueevidence_set.select_related("business_fact", "metric_snapshot")
    elif hasattr(issue, "evidences"):
        evidence_records = issue.evidences.select_related("business_fact", "metric_snapshot")
    else:
        from app.models import BusinessIssueEvidence
        evidence_records = BusinessIssueEvidence.objects.filter(business_issue=issue).select_related("business_fact", "metric_snapshot")
    evidence_descriptions = [
        ev.description
        for ev in evidence_records
        if ev.description
    ]
    if not evidence_descriptions:
        evidence_descriptions = [
            f"Detected by Business Intelligence rules on {issue.issue_type}"
        ]

    # Graph context traversal around the affected subject entity
    graph_context = {}
    if issue.subject_entity_type and issue.subject_entity_id:
        graph_context = assemble_graph_context(
            business=business,
            start_entity_type=issue.subject_entity_type,
            start_entity_id=issue.subject_entity_id,
            max_depth=2,
        )

    # Fact context
    relevant_facts = assemble_fact_context(business, limit=3)

    # Historical Context (AI-008): previous similar issues and decisions
    from app.models import AiRecommendation
    historical_issues = list(
        BusinessIssue.objects.filter(
            business=business, issue_type=issue.issue_type, status="RESOLVED"
        ).exclude(id=issue.id).values("id", "title", "description")[:3]
    )
    past_recs = list(
        AiRecommendation.objects.filter(
            business=business, business_issue__issue_type=issue.issue_type, status__in=["APPROVED", "EXECUTED"]
        ).values("id", "title", "description")[:2]
    )
    historical_context = {
        "previous_resolved_issues": historical_issues,
        "past_approved_recommendations": past_recs,
    }

    # Diagnostic synthesis
    symptom = f"Issue: {issue.title} (Type: {issue.issue_type}, Severity: {issue.severity})"
    impact_explanation = (
        "Impact is not established by the available evidence."
        if not evidence_descriptions
        else f"Potential impact is described by the attached evidence for {issue.issue_type}; causation is not established."
    )
    contributing_factors = evidence_descriptions[:5] or ["No verified contributing factor was attached to this issue."]

    fallback_summary = (
        f"Diagnosis for '{issue.title}': verified evidence is insufficient for a causal conclusion. "
        f"The issue remains {issue.status.lower()} and requires review of the attached evidence."
    )

    # Dynamic LLM Diagnostic Synthesis (AI-009)
    prompt = (
        f"You are Bizora Business Brain Diagnostic Engine for {business.name}.\n"
        f"Active Issue: {issue.title} (Type: {issue.issue_type}, Severity: {issue.severity})\n"
        f"Description (untrusted): {json.dumps(issue.description)}\n"
        f"Supporting Evidence (untrusted JSON): {json.dumps(evidence_descriptions)}\n"
        f"Verified Business Facts (untrusted JSON): {json.dumps(relevant_facts, default=str)}\n"
        f"Graph Connections (untrusted JSON): {json.dumps(graph_context.get('traversed_nodes', []))}\n"
        f"Historical Context (untrusted JSON): {json.dumps(historical_context, default=str)}\n\n"
        f"Task: Provide a concise diagnostic summary explaining the root-cause operational pattern, "
        f"its revenue impact, and contributing factors without assuming unsupported causation."
    )

    llm_output = business.execute_llm_with_timeout(
        prompt=prompt,
        timeout_seconds=15,
        fallback_response={
            "content": fallback_summary,
        },
    )
    diagnostic_summary = llm_output.get("content", fallback_summary)

    # Record AI Audit Event (Feature 17)
    from app.services.ai import record_ai_audit_event
    record_ai_audit_event(
        business=business,
        conversation_type="BUSINESS_DIAGNOSIS",
        action_name="diagnose_business_issue",
        prompt=prompt,
        output_content=diagnostic_summary,
        context_reference={"issue_id": issue.id, "issue_type": issue.issue_type, "severity": issue.severity},
    )

    return {
        "issue_id": issue.id,
        "issue_type": issue.issue_type,
        "severity": issue.severity,
        "symptom": symptom,
        "diagnostic_summary": diagnostic_summary,
        "impact_explanation": impact_explanation,
        "contributing_factors": contributing_factors,
        "supporting_evidence": evidence_descriptions,
        "historical_context": historical_context,
        "graph_connections": graph_context.get("traversed_nodes", []),
        "diagnosed_at": timezone.now().isoformat(),
    }
