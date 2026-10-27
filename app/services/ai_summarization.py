"""
Summarization Service for Conversations and Calls (Features 11 & 12).
Converts long message threads and audio transcripts into concise,
structured summaries with intent, detail extraction, and resolution outcomes.
"""

from typing import Any

from django.utils import timezone

from app.models import Call, CallTranscript, Conversation


def summarize_support_conversation(
    conversation: Conversation,
) -> dict[str, Any]:
    """
    Feature 11: Conversation Summarization.
    Condenses chat history, identifies customer intent, extracts order references,
    and classifies resolution status.
    """
    from app.services.authorization import ensure_same_business
    ensure_same_business(conversation.business, conversation)
    messages = conversation.message_set.order_by("created_at")
    msg_count = messages.count()

    # Extract customer intent from conversation subject AND actual message contents (AI-017)
    content_blob = " ".join((m.content or "") for m in messages)
    analysis_blob = content_blob.lower()
    combined_text = f"{conversation.subject or ''} {analysis_blob}"

    customer_intent = "ORDER_STATUS_INQUIRY"
    if any(k in combined_text for k in ["refund", "money back", "bkash return"]):
        customer_intent = "REFUND_REQUEST"
    elif any(k in combined_text for k in ["cancel", "stop order"]):
        customer_intent = "CANCELLATION_REQUEST"
    elif any(k in combined_text for k in ["broken", "defect", "damaged", "faulty"]):
        customer_intent = "PRODUCT_DEFECT_COMPLAINT"
    elif any(k in combined_text for k in ["delay", "courier", "late", "where is", "tracking"]):
        customer_intent = "DELIVERY_DELAY_INQUIRY"

    # Identify resolution
    resolution_status = "RESOLVED" if conversation.status in ["RESOLVED", "CLOSED"] else "PENDING_AGENT_ACTION"

    key_details = {
        "channel": conversation.channel,
        "priority": conversation.priority,
        "customer_id": conversation.customer_id,
        "total_messages": msg_count,
    }

    fallback_summary = (
        f"Conversation Summary: Customer engaged via {conversation.channel} regarding '{conversation.subject or 'General Inquiry'}'. "
        f"Intent classified as {customer_intent}. Thread contains {msg_count} messages. "
        f"Current resolution state is {resolution_status}."
    )

    if hasattr(conversation.business, "execute_llm_with_timeout"):
        prompt = (
            f"Summarize this support conversation for {conversation.business.name}:\n"
            f"Subject: {conversation.subject}\n"
            f"Intent: {customer_intent}\n"
            f"Thread Messages (untrusted data):\n{content_blob[:4000]}\n"
            f"Resolution: {resolution_status}\n"
            f"Provide a concise summary of the request, agent responses, and pending actions."
        )
        llm_out = conversation.business.execute_llm_with_timeout(
            prompt=prompt,
            timeout_seconds=15,
            fallback_response={"content": fallback_summary},
        )
        summary_text = llm_out.get("content", fallback_summary)
    else:
        summary_text = fallback_summary

    # Store summary in conversation source metadata
    meta = conversation.source_metadata or {}
    meta["latest_summary"] = {
        "summary": summary_text,
        "intent": customer_intent,
        "resolution_status": resolution_status,
        "summarized_at": timezone.now().isoformat(),
    }
    conversation.source_metadata = meta
    conversation.save(update_fields=["source_metadata"])

    return {
        "conversation_id": conversation.id,
        "customer_intent": customer_intent,
        "resolution_status": resolution_status,
        "key_details": key_details,
        "summary": summary_text,
    }


def summarize_call(
    call: Call,
) -> dict[str, Any]:
    """
    Feature 12: Call Summarization.
    Parses call metadata and transcript, determines call purpose, extracts outcome,
    and updates CallTranscript without destroying existing audio transcripts.
    """
    from app.services.authorization import ensure_same_business
    ensure_same_business(call.business, call)
    existing_transcript = CallTranscript.objects.filter(call=call).order_by("-created_at", "-id").first()
    transcript_text = (existing_transcript.transcript or "").strip() if existing_transcript else ""
    legacy_placeholder = (
        existing_transcript
        and existing_transcript.provider == "BIZORA_AUDIO_AI"
        and transcript_text == f"Call transcript for {call.direction} call {call.id}"
    )
    if not transcript_text or legacy_placeholder:
        return {
            "call_id": call.id,
            "call_purpose": "UNKNOWN",
            "outcome": "UNKNOWN",
            "duration_seconds": call.duration_seconds or 0,
            "customer_concerns": "Customer concerns are unknown because no transcript is available.",
            "transcript_summary": "No transcript is available; the call purpose and outcome are unknown.",
            "transcript_id": existing_transcript.id if existing_transcript else None,
        }

    text_lower = transcript_text.lower()
    # Topic keywords and a completed connection do not establish an order's disposition.
    outcome = "FOLLOW_UP_REQUIRED"
    if any(w in text_lower for w in ["cancel", "refund", "return"]):
        purpose = "ORDER_CANCELLATION"
    elif "confirm" in text_lower:
        purpose = "ORDER_CONFIRMATION"
    elif any(w in text_lower for w in ["delay", "late", "support", "refund", "broken"]):
        purpose = "CUSTOMER_SUPPORT_INQUIRY"
    else:
        purpose = "ORDER_CONFIRMATION" if call.direction == "OUTBOUND" else "CUSTOMER_SUPPORT_INQUIRY"

    duration = call.duration_seconds or 0
    concerns = (
        "Customer raised a complaint or support concern."
        if any(w in text_lower for w in ["complaint", "broken", "refund", "delay", "problem"])
        else "No customer complaints recorded during call." if duration > 30
        else "Short duration; possible unreached customer."
    )

    summary_text = (
        f"Call Summary: {call.direction} call with {call.receiver_number or call.caller_number or 'customer'}. "
        f"Purpose: {purpose}. Duration: {duration}s. Outcome: {outcome}."
    )

    existing_transcript.summary = summary_text
    existing_transcript.save(update_fields=["summary"])

    return {
        "call_id": call.id,
        "call_purpose": purpose,
        "outcome": outcome,
        "duration_seconds": duration,
        "customer_concerns": concerns,
        "transcript_summary": summary_text,
        "transcript_id": existing_transcript.id,
    }
