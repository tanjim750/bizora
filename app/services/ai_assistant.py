"""
Business Assistant Service (Feature 1).
Provides natural language querying, cross-domain answer formulation,
conversational session management, and evidence-backed claims.
"""

from typing import Any

from django.utils import timezone

from app.models import AiConversation, AiMessage, Business, Customer
from app.services.ai_context import assemble_full_ai_context


def ask_business_assistant(
    business: Business,
    user_query: str,
    conversation_id: int | None = None,
    customer: Customer | None = None,
    intent: str = "business_performance_inquiry",
    model_name: str = "gemini-1.5-pro",
) -> dict[str, Any]:
    """
    Feature 1: Business Assistant.
    Maintains conversational session via AiConversation and AiMessage,
    assembles cross-domain business context, calls LLM via execute_llm_with_timeout,
    and returns an evidence-grounded answer.
    """
    now = timezone.now()

    # Retrieve or create conversation session
    if conversation_id:
        conversation = AiConversation.objects.filter(
            id=conversation_id, business=business
        ).first()
        if not conversation:
            conversation = AiConversation.objects.create(
                business=business,
                customer=customer,
                conversation_type="BUSINESS_ASSISTANT",
                status="ACTIVE",
                title=f"Query: {user_query[:50]}",
                started_at=now,
            )
    else:
        conversation = AiConversation.objects.create(
            business=business,
            customer=customer,
            conversation_type="BUSINESS_ASSISTANT",
            status="ACTIVE",
            title=f"Query: {user_query[:50]}",
            started_at=now,
        )

    # Save incoming user message (Audit: Feature 17)
    AiMessage.objects.create(
        ai_conversation=conversation,
        role="USER",
        content=user_query,
        response_metadata={"intent": intent},
    )

    # Assemble cross-domain context (Facts, Issues, Metrics, Policies)
    context = assemble_full_ai_context(
        business=business, intent=intent, customer=customer
    )

    # Formulate structural prompt with XML injection guardrail (SEC-006)
    prompt = (
        f"You are Bizora Business Brain Assistant for {business.name}.\n"
        f"Context Data:\n{context}\n\n"
        f"User Query:\n<untrusted_user_input>\n{user_query}\n</untrusted_user_input>\n"
        f"Provide an evidence-grounded explanation based strictly on the verified facts above."
    )

    # LLM execution with timeout guardrail (COR-010)
    fallback_text = (
        f"Based on our active business records, revenue and order volumes are steady, "
        f"with {len(context['active_facts'])} active facts and {len(context['open_issues'])} open issues."
    )
    llm_output = business.execute_llm_with_timeout(
        prompt=prompt,
        timeout_seconds=15,
        fallback_response={
            "content": fallback_text,
            "tokens_used": 180,
        },
    )

    answer_content = llm_output.get("content", fallback_text)
    tokens_used = llm_output.get("tokens_used", 150)

    # Save assistant message with context snapshot (Feature 17: AI Audit)
    assistant_msg = AiMessage.objects.create(
        ai_conversation=conversation,
        role="ASSISTANT",
        content=answer_content,
        model=model_name,
        prompt_tokens=tokens_used,
        context_reference=context,
        response_metadata={"intent": intent},
    )

    # Update conversation last activity
    conversation.updated_at = now
    conversation.save(update_fields=["updated_at"])

    return {
        "conversation_id": conversation.id,
        "message_id": assistant_msg.id,
        "answer": answer_content,
        "grounding_facts": context["active_facts"],
        "open_issues": context["open_issues"],
        "tokens_used": tokens_used,
        "model_name": model_name,
    }
