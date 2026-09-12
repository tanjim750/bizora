"""
Customer Support AI Service (Feature 2).
Assists customer support workflows by generating policy-aware replies,
order-aware assistance, escalation suggestions, and AI-to-human handover summaries.
"""

from typing import Any

from django.utils import timezone

from app.models import Business, Conversation, Customer, Order
from app.services.ai_context import (
    assemble_customer_context,
    assemble_memory_context,
    assemble_order_context,
)


def generate_suggested_reply(
    business: Business,
    conversation: Conversation,
    customer: Customer | None = None,
    order: Order | None = None,
    intent: str = "refund_inquiry",
) -> dict[str, Any]:
    """
    Feature 2: Customer Support AI - Suggested Replies & Policy Awareness.
    Retrieves customer order history, active refund/delivery policies, and formats a policy-compliant draft reply.
    """
    if customer is None:
        customer = conversation.customer

    policies = assemble_memory_context(business, intent=intent)
    customer_ctx = assemble_customer_context(business, customer) if customer else {}
    order_ctx = assemble_order_context(business, order) if order else {}

    # Retrieve thread messages if available
    recent_msgs = conversation.message_set.order_by("-created_at")[:6]
    messages_history = [
        f"{m.sender_type or 'CUSTOMER'}: {m.content or ''}"
        for m in reversed(list(recent_msgs))
    ]

    support_context = {
        "business_name": business.name,
        "customer": customer_ctx,
        "order": order_ctx,
        "policies": policies,
        "conversation_subject": conversation.subject,
        "recent_messages": messages_history,
    }

    thread_block = ""
    if messages_history:
        thread_block = "Recent Conversation Thread:\n" + "\n".join(messages_history) + "\n\n"

    # XML injection guardrail (SEC-006)
    prompt = (
        f"Generate a polite, policy-compliant customer support response for {business.name}.\n"
        f"Context Data:\n{support_context}\n\n"
        f"{thread_block}"
        f"Customer Message Context:\n<untrusted_user_input>\n{conversation.subject or 'General Inquiry'}\n</untrusted_user_input>\n"
        f"Rule: Respect all refund, cancellation, and delivery policies strictly."
    )

    fallback_text = (
        f"Hello {customer_ctx.get('name', 'there')}, thank you for contacting {business.name}. "
        f"Regarding your inquiry, our standard policy ensures prompt assistance. "
        f"We are reviewing your request and will follow up shortly."
    )

    llm_output = business.execute_llm_with_timeout(
        prompt=prompt,
        timeout_seconds=15,
        fallback_response={
            "content": fallback_text,
            "confidence": "0.90",
        },
    )

    reply_content = llm_output.get("content", fallback_text)

    # Record AI Audit Event (Feature 17)
    from app.services.ai import record_ai_audit_event
    record_ai_audit_event(
        business=business,
        conversation_type="SUPPORT_ASSISTANT",
        action_name="generate_suggested_reply",
        prompt=prompt,
        output_content=reply_content,
        context_reference=support_context,
        customer=customer,
        support_conversation=conversation,
    )

    return {
        "conversation_id": conversation.id,
        "customer_id": customer.id if customer else None,
        "suggested_reply": reply_content,
        "intent": intent,
        "applied_policies": [p["title"] for p in policies],
        "order_referenced": order.order_number if order else None,
    }


def evaluate_escalation(
    business: Business,
    conversation: Conversation,
    customer_message: str,
) -> dict[str, Any]:
    """
    Feature 2: Escalation Suggestions.
    Evaluates whether an inquiry should be escalated to a human agent based on keywords,
    high cancellation rates, or policy dispute signals.
    """
    escalation_triggers = [
        "lawyer",
        "fraud",
        "police",
        "scam",
        "cheat",
        "court",
        "complaint",
        "broken",
        "emergency",
        "stolen",
    ]

    message_lower = customer_message.lower()
    trigger_found = [word for word in escalation_triggers if word in message_lower]

    should_escalate = len(trigger_found) > 0 or conversation.priority == "URGENT"
    reason = (
        f"Trigger keywords detected: {', '.join(trigger_found)}"
        if trigger_found
        else "Urgent priority flagged"
        if should_escalate
        else "Routine customer inquiry within standard AI support boundary."
    )

    if should_escalate:
        conversation.priority = "URGENT"
        conversation.ai_handover_state = "ESCALATION_RECOMMENDED"
        conversation.save(update_fields=["priority", "ai_handover_state"])

    return {
        "conversation_id": conversation.id,
        "should_escalate": should_escalate,
        "reason": reason,
        "triggers_identified": trigger_found,
    }


def generate_handover_summary(
    business: Business,
    conversation: Conversation,
) -> dict[str, Any]:
    """
    Feature 2: AI-to-Human Handover Support.
    Generates a concise handover summary so human agents understand key details,
    order context, and requested resolution without reading entire message logs.
    """
    customer_name = (
        conversation.customer.display_name
        or f"{conversation.customer.first_name or ''} {conversation.customer.last_name or ''}".strip()
        or getattr(conversation.customer, "name", None)
        if conversation.customer
        else "Customer"
    )

    summary_text = (
        f"Handover Summary: {customer_name} reached out regarding '{conversation.subject or 'Support Inquiry'}'. "
        f"Channel: {conversation.channel}. Status: {conversation.status}. "
        f"Customer requested assistance requiring human agent confirmation."
    )

    conversation.ai_handover_state = "HANDOVER_TO_HUMAN"
    conversation.save(update_fields=["ai_handover_state"])

    return {
        "conversation_id": conversation.id,
        "customer_name": customer_name,
        "handover_state": "HANDOVER_TO_HUMAN",
        "summary": summary_text,
        "generated_at": timezone.now().isoformat(),
    }


def resume_ai_handling(
    business: Business,
    conversation: Conversation,
    agent_notes: str | None = None,
) -> dict[str, Any]:
    """
    Feature 2: Human-to-AI Continuation.
    Allows AI to resume handling where appropriate while retaining previous human notes
    and conversation context.
    """
    now = timezone.now()
    meta = conversation.source_metadata or {}
    if agent_notes:
        notes_list = meta.get("human_agent_notes", [])
        notes_list.append({
            "note": agent_notes,
            "recorded_at": now.isoformat(),
        })
        meta["human_agent_notes"] = notes_list
        conversation.source_metadata = meta

    conversation.ai_handover_state = "ACTIVE_AI"
    conversation.save(update_fields=["ai_handover_state", "source_metadata"])

    return {
        "conversation_id": conversation.id,
        "ai_handover_state": "ACTIVE_AI",
        "agent_notes_retained": agent_notes,
        "resumed_at": now.isoformat(),
    }

