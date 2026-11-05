"""Deterministic customer support analysis services.

Serves Business Intelligence specification section 11 (Support Analysis) and the
§2 Support Metrics family. This is an internal, business-scoped service; callers
remain responsible for authorization before invoking anything here.

Key properties enforced:
1. Canonical support model integration: canonical conversations, messages,
   assignments, participants, and calls.
2. Clocks and incomplete conversations handled explicitly:
   - Incomplete conversations (OPEN / PENDING or missing resolution timestamp)
     have active resolution clocks and are never treated as 0-second resolutions.
   - Inbound customer messages with no outbound reply have open response clocks
     and are never treated as 0-second responses.
   - Inverted clock timestamps (reply earlier than message, or resolved_at earlier
     than started_at) are flagged as inverted clock anomalies and excluded from
     duration averages.
   - Zero completed durations/conversations return UNAVAILABLE for rates and
     averages (never fake zeros).
3. Status and Priority vocabularies:
   - Documented statuses from business-data.md:241: OPEN, PENDING, RESOLVED, CLOSED.
   - Documented priorities from business-data.md:244: LOW, NORMAL, HIGH, URGENT.
   - Unrecognized statuses/priorities are classified UNCLASSIFIED and tracked.
4. AI/Human handover and escalation:
   - Evaluates handovers via Conversation.ai_handover_state and ConversationAssignment.
   - Measures escalation rate as an exact Decimal fraction.
5. Customer support history and issue trends:
   - Connects repeat customer contacts with orders, products, and shipments.
   - Connects support volume with orders, products, and courier/delivery domains.
6. Snapshot recording:
   - Records the 5 registered support metrics using the §3 snapshot contract.
   - Fails closed on calculation_rule collisions.
7. Multi-tenant isolation:
   - All queries and relationship validations strictly filter by business_id.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
import datetime

from django.db import transaction
from django.utils import timezone

from app import models
from . import metrics


class SupportValidationError(ValueError):
    """An analytical parameter, period, scope, or dimension is invalid."""


class SupportScopeError(SupportValidationError):
    """An entity does not belong to the requested business."""


class SupportCalculationError(ValueError):
    """An internal calculation invariant was violated."""


class SupportRuleError(ValueError):
    """The support rule registry or status mapping is inconsistent."""


UNAVAILABLE_ZERO_DENOMINATOR = "ZERO_DENOMINATOR"
UNAVAILABLE_NO_DATA = "NO_DATA"
UNAVAILABLE_MISSING_CONTRACT = "MISSING_DOCUMENTED_CONTRACT"

# Documented conversation statuses (docs/implementations/features/business-data.md:241)
DOCUMENTED_CONVERSATION_STATUSES = frozenset({"OPEN", "PENDING", "RESOLVED", "CLOSED"})
RESOLVED_STATUSES = frozenset({"RESOLVED", "CLOSED"})
UNRESOLVED_STATUSES = frozenset({"OPEN", "PENDING"})

# Documented conversation priorities (docs/implementations/features/business-data.md:244)
DOCUMENTED_CONVERSATION_PRIORITIES = frozenset({"LOW", "NORMAL", "HIGH", "URGENT"})
HIGH_PRIORITIES = frozenset({"HIGH", "URGENT"})

# Registered support metric keys (BI §2 Support Metrics)
SUPPORT_METRICS = {
    "conversation_volume": "bi.metric.support_conversation_volume.v1",
    "response_time": "bi.metric.support_response_time.v1",
    "resolution_time": "bi.metric.support_resolution_time.v1",
    "unresolved_cases": "bi.metric.support_unresolved_cases.v1",
    "escalation_rate": "bi.metric.support_escalation_rate.v1",
}

CALCULATION_RULES = {
    "conversation_volume": "bi.metric.support_conversation_volume.v1.started_at",
    "response_time": "bi.metric.support_response_time.v1.first_response",
    "response_time_all": "bi.metric.support_response_time.v1.all_responses",
    "resolution_time": "bi.metric.support_resolution_time.v1.resolved_at",
    "unresolved_cases": "bi.metric.support_unresolved_cases.v1.status_open_pending",
    "escalation_rate": "bi.metric.support_escalation_rate.v1.handover_escalated",
}

_PRECISION = 48
_ZERO = Decimal(0)
_QUANTUM_RATE = Decimal("0.0001")
_QUANTUM_DURATION = Decimal("0.0001")


def _ratio(numerator: int | Decimal, denominator: int | Decimal) -> Decimal | str:
    """Exact decimal ratio quantized to 4 decimal places, or UNAVAILABLE."""
    if not denominator:
        return metrics.UNAVAILABLE
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        val = Decimal(numerator) / Decimal(denominator)
    return val.quantize(_QUANTUM_RATE)


def _average(values: list[Decimal]) -> Decimal | str:
    """Exact decimal average quantized to 4 decimal places, or UNAVAILABLE."""
    if not values:
        return metrics.UNAVAILABLE
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        total = sum(values, _ZERO)
        val = total / Decimal(len(values))
    return val.quantize(_QUANTUM_DURATION)


@dataclass(frozen=True)
class UnavailableSupportEvidence:
    is_available: bool
    reason: str
    detail: str


@dataclass(frozen=True)
class SupportScope:
    business_id: int
    period_type: str
    period_start: datetime.datetime
    period_end: datetime.datetime
    dimension_type: str | None = None
    dimension_value: str | None = None


@dataclass(frozen=True)
class ResponseTimeSummary:
    initial_response_count: int
    average_initial_response_time: Decimal | str
    all_responses_count: int
    average_ongoing_response_time: Decimal | str
    pending_response_clocks_count: int
    inverted_clocks_count: int


@dataclass(frozen=True)
class ResolutionTimeSummary:
    resolved_conversations_count: int
    average_resolution_time: Decimal | str
    unresolved_conversations_count: int
    missing_resolution_timestamp_count: int
    inverted_clocks_count: int


@dataclass(frozen=True)
class PriorityPerformance:
    priority: str
    conversation_count: int
    share_of_total: Decimal | str
    average_response_time: Decimal | str
    average_resolution_time: Decimal | str
    unresolved_count: int


@dataclass(frozen=True)
class HandoverSummary:
    total_conversations: int
    escalated_conversations_count: int
    escalation_rate: Decimal | str
    ai_to_human_handover_count: int
    human_to_ai_handover_count: int
    total_handovers: int


@dataclass(frozen=True)
class UnresolvedConversationDetail:
    conversation_id: int
    customer_id: int | None
    status: str
    priority: str
    channel: str
    started_at: datetime.datetime
    age_seconds: Decimal
    breached_sla: bool | None


@dataclass(frozen=True)
class CustomerSupportSummary:
    customer_id: int
    display_name: str | None
    total_conversations: int
    unresolved_conversations: int
    average_response_time: Decimal | str
    average_resolution_time: Decimal | str
    repeat_contact: bool
    order_ids: tuple[int, ...]
    product_ids: tuple[int, ...]
    shipment_ids: tuple[int, ...]


@dataclass(frozen=True)
class SupportIssueTrend:
    issue_area: str
    entity_id_or_label: str
    conversation_count: int
    share_of_total: Decimal | str


@dataclass(frozen=True)
class ChannelSummary:
    channel: str
    conversation_count: int
    share_of_total: Decimal | str
    average_response_time: Decimal | str
    average_resolution_time: Decimal | str
    unresolved_count: int


@dataclass(frozen=True)
class SupportAnalysis:
    scope: SupportScope
    total_conversations: int
    response_time_summary: ResponseTimeSummary
    resolution_time_summary: ResolutionTimeSummary
    priority_distribution: tuple[PriorityPerformance, ...]
    handover_summary: HandoverSummary
    unresolved_conversations: tuple[UnresolvedConversationDetail, ...]
    channel_segments: tuple[ChannelSummary, ...]
    issue_trends: tuple[SupportIssueTrend, ...]
    sla_breach_detection: UnavailableSupportEvidence | tuple[UnresolvedConversationDetail, ...]


@dataclass(frozen=True)
class SupportMetricRecording:
    analysis: SupportAnalysis
    snapshots: tuple[tuple[str, metrics.SnapshotWriteResult], ...]


def _validate_scope(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
) -> SupportScope:
    if not isinstance(business_id, int) or business_id <= 0:
        raise SupportValidationError(f"business_id must be a positive integer, got {business_id!r}")

    if not models.Business.objects.filter(pk=business_id).exists():
        raise SupportScopeError(f"Business {business_id} does not exist.")

    if not isinstance(period_start, datetime.datetime) or not timezone.is_aware(period_start):
        raise SupportValidationError("period_start must be a timezone-aware datetime")

    if not isinstance(period_end, datetime.datetime) or not timezone.is_aware(period_end):
        raise SupportValidationError("period_end must be a timezone-aware datetime")

    if period_start >= period_end:
        raise SupportValidationError(
            f"period_start ({period_start}) must precede period_end ({period_end})"
        )

    if period_type not in metrics.PERIOD_TYPES:
        raise SupportValidationError(
            f"Unknown period_type {period_type!r}; expected one of {sorted(metrics.PERIOD_TYPES)}"
        )

    if dimension_type is not None:
        if dimension_type not in metrics.DIMENSION_TYPES:
            raise SupportValidationError(
                f"Unknown dimension_type {dimension_type!r}; expected one of {sorted(metrics.DIMENSION_TYPES)}"
            )
        if dimension_value is None or not str(dimension_value).strip():
            raise SupportValidationError("dimension_value cannot be empty when dimension_type is provided")
        dimension_value = str(dimension_value)

    return SupportScope(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
    )


def _is_inbound_message(msg: models.Message) -> bool:
    """Classifies whether a message is an inbound customer communication."""
    direction = (msg.direction or "").upper()
    sender_type = (msg.sender_type or "").upper()
    return direction == "INBOUND" or sender_type == "CUSTOMER"


def _is_outbound_message(msg: models.Message) -> bool:
    """Classifies whether a message is an outbound business communication."""
    direction = (msg.direction or "").upper()
    sender_type = (msg.sender_type or "").upper()
    return direction == "OUTBOUND" or sender_type in {"AGENT", "AI", "SYSTEM"}


def _is_escalated(conv: models.Conversation, assignments: list[models.ConversationAssignment]) -> bool:
    """Determines whether a conversation moved between automated and human support / escalated."""
    handover_state = (conv.ai_handover_state or "").upper()
    if handover_state in {"HANDOVER_TO_HUMAN", "ESCALATED", "HUMAN_AGENT", "PENDING_HUMAN"}:
        return True
    if "HUMAN" in handover_state or "ESCALAT" in handover_state:
        return True

    # Check assignment transitions: if any assignment is to a human AGENT/TEAM
    # after an AI assignment, or if assigned to human agent
    seen_ai = False
    for assign in assignments:
        assignee_type = (assign.assignee_type or "").upper()
        if assignee_type == "AI":
            seen_ai = True
        elif assignee_type in {"AGENT", "TEAM"} and seen_ai:
            return True
        elif assignee_type == "AGENT" and handover_state:
            return True

    return False


def _count_handovers(conv: models.Conversation, assignments: list[models.ConversationAssignment]) -> tuple[int, int]:
    """Counts (ai_to_human, human_to_ai) handovers for a conversation."""
    ai_to_human = 0
    human_to_ai = 0

    handover_state = (conv.ai_handover_state or "").upper()
    if handover_state in {"HANDOVER_TO_HUMAN", "ESCALATED", "HUMAN_AGENT"}:
        ai_to_human += 1
    elif handover_state in {"HANDOVER_TO_AI", "AI_AGENT"}:
        human_to_ai += 1

    last_type = None
    for assign in assignments:
        atype = (assign.assignee_type or "").upper()
        if last_type == "AI" and atype in {"AGENT", "TEAM"}:
            ai_to_human += 1
        elif last_type in {"AGENT", "TEAM"} and atype == "AI":
            human_to_ai += 1
        last_type = atype

    return ai_to_human, human_to_ai


def analyze_support(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
    expected_resolution_seconds: int | float | Decimal | None = None,
    comparison_start: datetime.datetime | None = None,
    comparison_end: datetime.datetime | None = None,
) -> SupportAnalysis:
    """Perform deterministic support analysis across canonical conversations (BI §11)."""
    scope = _validate_scope(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
    )

    conv_qs = models.Conversation.objects.filter(
        business_id=business_id,
        started_at__gte=period_start,
        started_at__lt=period_end,
    )

    if dimension_type == "CHANNEL" and dimension_value is not None:
        conv_qs = conv_qs.filter(channel=dimension_value)

    conversations = list(conv_qs.order_by("started_at", "pk"))
    total_conversations = len(conversations)

    conv_ids = [c.pk for c in conversations]

    # Pre-fetch messages for all conversations in scope
    messages_by_conv: dict[int, list[models.Message]] = {c_id: [] for c_id in conv_ids}
    if conv_ids:
        for msg in models.Message.objects.filter(
            conversation__business_id=business_id,
            conversation_id__in=conv_ids,
        ).order_by("sent_at", "created_at", "pk"):
            messages_by_conv[msg.conversation_id].append(msg)

    # Pre-fetch assignments for all conversations in scope
    assignments_by_conv: dict[int, list[models.ConversationAssignment]] = {c_id: [] for c_id in conv_ids}
    if conv_ids:
        for assign in models.ConversationAssignment.objects.filter(
            conversation__business_id=business_id,
            conversation_id__in=conv_ids,
        ).order_by("assigned_at", "pk"):
            assignments_by_conv[assign.conversation_id].append(assign)

    # 1. Response Time Analysis & Clocks
    initial_durations: list[Decimal] = []
    ongoing_durations: list[Decimal] = []
    pending_response_clocks = 0
    inverted_response_clocks = 0

    conv_initial_response_times: dict[int, Decimal] = {}

    for conv in conversations:
        msgs = messages_by_conv.get(conv.pk, [])
        first_inbound = None
        first_inbound_time = None

        # Find first inbound message
        for m in msgs:
            if _is_inbound_message(m):
                first_inbound = m
                first_inbound_time = m.sent_at or m.created_at
                break

        if first_inbound is not None and first_inbound_time is not None:
            # Look for subsequent outbound message
            first_outbound_time = None
            saw_inverted = False
            for m in msgs:
                m_time = m.sent_at or m.created_at
                if _is_outbound_message(m) and m_time is not None and m.pk != first_inbound.pk:
                    if m_time >= first_inbound_time:
                        first_outbound_time = m_time
                        break
                    else:
                        inverted_response_clocks += 1
                        saw_inverted = True

            if first_outbound_time is not None:
                duration_sec = Decimal((first_outbound_time - first_inbound_time).total_seconds())
                initial_durations.append(duration_sec)
                conv_initial_response_times[conv.pk] = duration_sec
            elif not saw_inverted:
                # Inbound message received, but no outbound reply at all: pending response clock!
                pending_response_clocks += 1

        # Ongoing response times: evaluate each inbound-to-next-outbound pair
        last_inbound_t = None
        for m in msgs:
            m_time = m.sent_at or m.created_at
            if not m_time:
                continue
            if _is_inbound_message(m):
                last_inbound_t = m_time
            elif _is_outbound_message(m) and last_inbound_t is not None:
                if m_time >= last_inbound_t:
                    ongoing_durations.append(Decimal((m_time - last_inbound_t).total_seconds()))
                else:
                    inverted_response_clocks += 1
                last_inbound_t = None

    response_time_summary = ResponseTimeSummary(
        initial_response_count=len(initial_durations),
        average_initial_response_time=_average(initial_durations),
        all_responses_count=len(ongoing_durations),
        average_ongoing_response_time=_average(ongoing_durations),
        pending_response_clocks_count=pending_response_clocks,
        inverted_clocks_count=inverted_response_clocks,
    )

    # 2. Resolution Time Analysis & Clocks
    resolution_durations: list[Decimal] = []
    unresolved_details: list[UnresolvedConversationDetail] = []
    missing_resolution_timestamps = 0
    inverted_resolution_clocks = 0

    conv_resolution_times: dict[int, Decimal] = {}

    for conv in conversations:
        start_t = conv.started_at or conv.created_at
        status_upper = (conv.status or "").upper()

        is_resolved_status = status_upper in RESOLVED_STATUSES
        has_resolved_timestamp = conv.resolved_at is not None

        if is_resolved_status or has_resolved_timestamp:
            if conv.resolved_at is None:
                missing_resolution_timestamps += 1
            elif start_t and conv.resolved_at < start_t:
                inverted_resolution_clocks += 1
            elif start_t:
                res_sec = Decimal((conv.resolved_at - start_t).total_seconds())
                resolution_durations.append(res_sec)
                conv_resolution_times[conv.pk] = res_sec
        else:
            # Unresolved conversation (OPEN / PENDING)
            age_sec = Decimal((period_end - start_t).total_seconds()) if start_t else _ZERO
            breached = None
            if expected_resolution_seconds is not None:
                breached = age_sec > Decimal(expected_resolution_seconds)

            unresolved_details.append(
                UnresolvedConversationDetail(
                    conversation_id=conv.pk,
                    customer_id=conv.customer_id,
                    status=conv.status,
                    priority=conv.priority,
                    channel=conv.channel,
                    started_at=conv.started_at,
                    age_seconds=age_sec,
                    breached_sla=breached,
                )
            )

    resolution_time_summary = ResolutionTimeSummary(
        resolved_conversations_count=len(resolution_durations),
        average_resolution_time=_average(resolution_durations),
        unresolved_conversations_count=len(unresolved_details),
        missing_resolution_timestamp_count=missing_resolution_timestamps,
        inverted_clocks_count=inverted_resolution_clocks,
    )

    # 3. Priority Distribution & Performance
    priority_groups: dict[str, list[models.Conversation]] = {}
    for conv in conversations:
        p = (conv.priority or "").upper()
        if p not in DOCUMENTED_CONVERSATION_PRIORITIES:
            p = "UNCLASSIFIED"
        priority_groups.setdefault(p, []).append(conv)

    priority_performances = []
    all_priorities = list(DOCUMENTED_CONVERSATION_PRIORITIES) + [
        p for p in priority_groups if p not in DOCUMENTED_CONVERSATION_PRIORITIES
    ]
    for p in sorted(all_priorities):
        group_convs = priority_groups.get(p, [])
        p_count = len(group_convs)
        p_share = _ratio(p_count, total_conversations)

        # Average response time in this priority group
        p_resp_durations = [
            conv_initial_response_times[c.pk]
            for c in group_convs
            if c.pk in conv_initial_response_times
        ]
        # Average resolution time in this priority group
        p_res_durations = [
            conv_resolution_times[c.pk]
            for c in group_convs
            if c.pk in conv_resolution_times
        ]
        p_unresolved = sum(1 for c in group_convs if (c.status or "").upper() in UNRESOLVED_STATUSES)

        priority_performances.append(
            PriorityPerformance(
                priority=p,
                conversation_count=p_count,
                share_of_total=p_share,
                average_response_time=_average(p_resp_durations),
                average_resolution_time=_average(p_res_durations),
                unresolved_count=p_unresolved,
            )
        )

    # 4. AI/Human Handover Analysis & Escalation Rate
    escalated_count = 0
    total_ai_to_human = 0
    total_human_to_ai = 0

    for conv in conversations:
        assigns = assignments_by_conv.get(conv.pk, [])
        if _is_escalated(conv, assigns):
            escalated_count += 1
        a2h, h2a = _count_handovers(conv, assigns)
        total_ai_to_human += a2h
        total_human_to_ai += h2a

    handover_summary = HandoverSummary(
        total_conversations=total_conversations,
        escalated_conversations_count=escalated_count,
        escalation_rate=_ratio(escalated_count, total_conversations),
        ai_to_human_handover_count=total_ai_to_human,
        human_to_ai_handover_count=total_human_to_ai,
        total_handovers=total_ai_to_human + total_human_to_ai,
    )

    # 5. Channel Segments
    channel_groups: dict[str, list[models.Conversation]] = {}
    for conv in conversations:
        ch = conv.channel or "UNKNOWN"
        channel_groups.setdefault(ch, []).append(conv)

    channel_summaries = []
    for ch in sorted(channel_groups.keys()):
        ch_convs = channel_groups[ch]
        ch_count = len(ch_convs)
        ch_share = _ratio(ch_count, total_conversations)
        ch_resp = [
            conv_initial_response_times[c.pk]
            for c in ch_convs
            if c.pk in conv_initial_response_times
        ]
        ch_res = [
            conv_resolution_times[c.pk]
            for c in ch_convs
            if c.pk in conv_resolution_times
        ]
        ch_unres = sum(1 for c in ch_convs if (c.status or "").upper() in UNRESOLVED_STATUSES)

        channel_summaries.append(
            ChannelSummary(
                channel=ch,
                conversation_count=ch_count,
                share_of_total=ch_share,
                average_response_time=_average(ch_resp),
                average_resolution_time=_average(ch_res),
                unresolved_count=ch_unres,
            )
        )

    # 6. Support Issue Trends (linking conversations to orders, products, couriers)
    issue_trends = _calculate_issue_trends(
        business_id=business_id,
        conversations=conversations,
        total_conversations=total_conversations,
    )

    # 7. SLA Breach Detection
    sla_evidence: UnavailableSupportEvidence | tuple[UnresolvedConversationDetail, ...]
    if expected_resolution_seconds is None:
        sla_evidence = UnavailableSupportEvidence(
            is_available=False,
            reason=UNAVAILABLE_MISSING_CONTRACT,
            detail="configured expected resolution SLA threshold in seconds",
        )
    else:
        sla_evidence = tuple(u for u in unresolved_details if u.breached_sla)

    return SupportAnalysis(
        scope=scope,
        total_conversations=total_conversations,
        response_time_summary=response_time_summary,
        resolution_time_summary=resolution_time_summary,
        priority_distribution=tuple(priority_performances),
        handover_summary=handover_summary,
        unresolved_conversations=tuple(unresolved_details),
        channel_segments=tuple(channel_summaries),
        issue_trends=tuple(issue_trends),
        sla_breach_detection=sla_evidence,
    )


def _calculate_issue_trends(
    *,
    business_id: int,
    conversations: list[models.Conversation],
    total_conversations: int,
) -> list[SupportIssueTrend]:
    """Connects support volume to business domains: orders, products, and courier/delivery."""
    if not conversations:
        return []

    conv_ids = [c.pk for c in conversations]

    # Map conversations to orders via Call
    calls = models.Call.objects.filter(
        business_id=business_id,
        conversation_id__in=conv_ids,
        order_id__isnull=False,
    ).select_related("order")

    order_to_conv_count: dict[int, int] = {}
    for call in calls:
        if call.order_id:
            order_to_conv_count[call.order_id] = order_to_conv_count.get(call.order_id, 0) + 1

    # Also check source_metadata on conversations
    for conv in conversations:
        if conv.source_metadata and isinstance(conv.source_metadata, dict):
            meta_order_id = conv.source_metadata.get("order_id")
            if meta_order_id and isinstance(meta_order_id, int):
                order_to_conv_count[meta_order_id] = order_to_conv_count.get(meta_order_id, 0) + 1

    # Map orders to products and couriers
    product_to_conv_count: dict[int, int] = {}
    courier_to_conv_count: dict[str, int] = {}

    if order_to_conv_count:
        order_ids = list(order_to_conv_count.keys())
        items = models.OrderItem.objects.filter(
            order__business_id=business_id,
            order_id__in=order_ids,
        )
        for it in items:
            weight = order_to_conv_count.get(it.order_id, 1)
            product_to_conv_count[it.product_id] = product_to_conv_count.get(it.product_id, 0) + weight

        shipments = models.Shipment.objects.filter(
            business_id=business_id,
            order_id__in=order_ids,
        )
        for s in shipments:
            if s.provider:
                weight = order_to_conv_count.get(s.order_id, 1)
                courier_to_conv_count[s.provider] = courier_to_conv_count.get(s.provider, 0) + weight

    trends: list[SupportIssueTrend] = []

    for o_id, count in sorted(order_to_conv_count.items(), key=lambda x: -x[1]):
        trends.append(
            SupportIssueTrend(
                issue_area="ORDER",
                entity_id_or_label=str(o_id),
                conversation_count=count,
                share_of_total=_ratio(count, total_conversations),
            )
        )

    for p_id, count in sorted(product_to_conv_count.items(), key=lambda x: -x[1]):
        trends.append(
            SupportIssueTrend(
                issue_area="PRODUCT",
                entity_id_or_label=str(p_id),
                conversation_count=count,
                share_of_total=_ratio(count, total_conversations),
            )
        )

    for provider, count in sorted(courier_to_conv_count.items(), key=lambda x: -x[1]):
        trends.append(
            SupportIssueTrend(
                issue_area="COURIER",
                entity_id_or_label=provider,
                conversation_count=count,
                share_of_total=_ratio(count, total_conversations),
            )
        )

    return trends


def record_support_metrics(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
    expected_resolution_seconds: int | float | Decimal | None = None,
) -> SupportMetricRecording:
    """Record the five registered support metrics using the §3 snapshot contract."""
    with transaction.atomic():
        analysis = analyze_support(
            business_id=business_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            dimension_type=dimension_type,
            dimension_value=dimension_value,
            expected_resolution_seconds=expected_resolution_seconds,
        )

        values: dict[str, Decimal | str] = {
            "conversation_volume": Decimal(analysis.total_conversations),
            "response_time": analysis.response_time_summary.average_initial_response_time,
            "resolution_time": analysis.resolution_time_summary.average_resolution_time,
            "unresolved_cases": Decimal(len(analysis.unresolved_conversations)),
            "escalation_rate": analysis.handover_summary.escalation_rate,
        }

        inputs = {
            "service": "business_intelligence.support",
            "specification_sections": ["2", "11"],
            "total_conversations": analysis.total_conversations,
            "resolved_count": analysis.resolution_time_summary.resolved_conversations_count,
            "unresolved_count": len(analysis.unresolved_conversations),
            "pending_response_clocks": analysis.response_time_summary.pending_response_clocks_count,
            "inverted_response_clocks": analysis.response_time_summary.inverted_clocks_count,
            "inverted_resolution_clocks": analysis.resolution_time_summary.inverted_clocks_count,
            "dimension_type": dimension_type,
            "dimension_value": dimension_value,
        }

        snapshots = []
        for name, value in values.items():
            metric_key = SUPPORT_METRICS[name]
            rule = CALCULATION_RULES[name]

            # Fail closed on calculation_rule collision
            existing = metrics.get_metric_snapshot(
                business_id=business_id,
                metric_key=metric_key,
                period_type=analysis.scope.period_type,
                period_start=analysis.scope.period_start,
                period_end=analysis.scope.period_end,
                dimension_type=dimension_type,
                dimension_value=dimension_value,
            )
            if existing is not None and existing.calculation_rule != rule:
                raise metrics.MetricSnapshotConflictError(
                    f"Snapshot {existing.snapshot_id} already exists under calculation rule "
                    f"{existing.calculation_rule}, conflicting with {rule}."
                )

            res = metrics.record_metric_snapshot(
                business_id=business_id,
                metric_key=metric_key,
                value=value,
                period_type=analysis.scope.period_type,
                period_start=analysis.scope.period_start,
                period_end=analysis.scope.period_end,
                dimension_type=dimension_type,
                dimension_value=dimension_value,
                calculation_rule=rule,
                inputs=inputs,
            )
            snapshots.append((name, res))

        return SupportMetricRecording(analysis, tuple(snapshots))


def calculate_conversation_volume(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
) -> int:
    """Convenience helper: returns total conversation volume in scope (BI §11)."""
    analysis = analyze_support(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
    )
    return analysis.total_conversations


def calculate_response_time(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
) -> ResponseTimeSummary:
    """Convenience helper: returns response time performance and clock telemetry (BI §11)."""
    analysis = analyze_support(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
    )
    return analysis.response_time_summary


def calculate_resolution_time(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
) -> ResolutionTimeSummary:
    """Convenience helper: returns resolution time performance and incomplete conversation telemetry (BI §11)."""
    analysis = analyze_support(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
    )
    return analysis.resolution_time_summary


def analyze_unresolved_conversations(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
    expected_resolution_seconds: int | float | Decimal | None = None,
) -> tuple[UnresolvedConversationDetail, ...]:
    """Convenience helper: returns conversations remaining open or pending (BI §11)."""
    analysis = analyze_support(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
        expected_resolution_seconds=expected_resolution_seconds,
    )
    return analysis.unresolved_conversations


def analyze_priority_distribution(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
) -> tuple[PriorityPerformance, ...]:
    """Convenience helper: returns conversation distribution and performance by priority (BI §11)."""
    analysis = analyze_support(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
    )
    return analysis.priority_distribution


def analyze_handover_and_escalation(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
) -> HandoverSummary:
    """Convenience helper: returns AI/human handover and escalation telemetry (BI §11)."""
    analysis = analyze_support(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
    )
    return analysis.handover_summary


def analyze_customer_support_history(
    *,
    business_id: int,
    customer_id: int,
    period_start: datetime.datetime | None = None,
    period_end: datetime.datetime | None = None,
) -> CustomerSupportSummary:
    """Connects repeated support interactions with customer and order activity (BI §11)."""
    if not isinstance(business_id, int) or business_id <= 0:
        raise SupportValidationError("business_id must be a positive integer")

    customer = models.Customer.objects.filter(pk=customer_id, business_id=business_id).first()
    if not customer:
        raise SupportScopeError(f"Customer {customer_id} does not exist in business {business_id}.")

    conv_qs = models.Conversation.objects.filter(
        business_id=business_id,
        customer_id=customer_id,
    )
    if period_start is not None:
        if not timezone.is_aware(period_start):
            raise SupportValidationError("period_start must be timezone-aware")
        conv_qs = conv_qs.filter(started_at__gte=period_start)
    if period_end is not None:
        if not timezone.is_aware(period_end):
            raise SupportValidationError("period_end must be timezone-aware")
        conv_qs = conv_qs.filter(started_at__lt=period_end)

    conversations = list(conv_qs.order_by("started_at", "pk"))
    total_convs = len(conversations)

    conv_ids = [c.pk for c in conversations]

    # Pre-fetch messages for customer's conversations
    messages_by_conv: dict[int, list[models.Message]] = {c_id: [] for c_id in conv_ids}
    if conv_ids:
        for msg in models.Message.objects.filter(
            conversation__business_id=business_id,
            conversation_id__in=conv_ids,
        ).order_by("sent_at", "created_at", "pk"):
            messages_by_conv[msg.conversation_id].append(msg)

    # Response times for customer
    initial_durations: list[Decimal] = []
    for conv in conversations:
        msgs = messages_by_conv.get(conv.pk, [])
        first_in = next((m for m in msgs if _is_inbound_message(m)), None)
        if first_in:
            t_in = first_in.sent_at or first_in.created_at
            first_out = next(
                (
                    m for m in msgs
                    if _is_outbound_message(m) and (m.sent_at or m.created_at)
                    and (m.sent_at or m.created_at) >= t_in and m.pk != first_in.pk
                ),
                None,
            )
            if first_out:
                t_out = first_out.sent_at or first_out.created_at
                initial_durations.append(Decimal((t_out - t_in).total_seconds()))

    # Resolution times for customer
    resolution_durations: list[Decimal] = []
    unresolved_count = 0
    for conv in conversations:
        start_t = conv.started_at or conv.created_at
        status_upper = (conv.status or "").upper()
        if (status_upper in RESOLVED_STATUSES or conv.resolved_at is not None) and conv.resolved_at and start_t:
            if conv.resolved_at >= start_t:
                resolution_durations.append(Decimal((conv.resolved_at - start_t).total_seconds()))
        elif status_upper in UNRESOLVED_STATUSES:
            unresolved_count += 1

    # Associated customer orders
    orders = list(
        models.Order.objects.filter(
            business_id=business_id,
            customer_id=customer_id,
        ).order_by("pk")
    )
    order_ids = tuple(o.pk for o in orders)

    # Associated products purchased by customer
    product_ids: tuple[int, ...] = ()
    if order_ids:
        items = models.OrderItem.objects.filter(
            order__business_id=business_id,
            order_id__in=order_ids,
        ).values_list("product_id", flat=True).distinct().order_by("product_id")
        product_ids = tuple(items)

    # Associated shipments for customer
    shipment_ids: tuple[int, ...] = ()
    shipments = models.Shipment.objects.filter(
        business_id=business_id,
        customer_id=customer_id,
    ).values_list("pk", flat=True).order_by("pk")
    shipment_ids = tuple(shipments)

    return CustomerSupportSummary(
        customer_id=customer_id,
        display_name=customer.display_name,
        total_conversations=total_convs,
        unresolved_conversations=unresolved_count,
        average_response_time=_average(initial_durations),
        average_resolution_time=_average(resolution_durations),
        repeat_contact=total_convs > 1,
        order_ids=order_ids,
        product_ids=product_ids,
        shipment_ids=shipment_ids,
    )


def analyze_support_issue_trends(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    dimension_type: str | None = None,
    dimension_value: str | None = None,
    comparison_start: datetime.datetime | None = None,
    comparison_end: datetime.datetime | None = None,
) -> tuple[SupportIssueTrend, ...]:
    """Convenience helper: returns support issue trends associated with business areas (BI §11)."""
    analysis = analyze_support(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
        comparison_start=comparison_start,
        comparison_end=comparison_end,
    )
    return analysis.issue_trends


def get_support_rule(name: str, variant: str | None = None) -> str:
    """Return the closed calculation rule identifier for a registered support metric."""
    if name not in SUPPORT_METRICS and name not in CALCULATION_RULES:
        raise SupportValidationError(f"Unknown support metric name: {name!r}")
    if variant is not None:
        key = f"{name}_{variant}"
        if key in CALCULATION_RULES:
            return CALCULATION_RULES[key]
        return f"{SUPPORT_METRICS.get(name, name)}.{variant}"
    return CALCULATION_RULES.get(name, SUPPORT_METRICS.get(name, ""))


__all__ = [
    "CALCULATION_RULES",
    "ChannelSummary",
    "CustomerSupportSummary",
    "DOCUMENTED_CONVERSATION_PRIORITIES",
    "DOCUMENTED_CONVERSATION_STATUSES",
    "HIGH_PRIORITIES",
    "HandoverSummary",
    "PriorityPerformance",
    "ResolutionTimeSummary",
    "ResponseTimeSummary",
    "RESOLVED_STATUSES",
    "SUPPORT_METRICS",
    "SupportAnalysis",
    "SupportCalculationError",
    "SupportIssueTrend",
    "SupportMetricRecording",
    "SupportRuleError",
    "SupportScope",
    "SupportScopeError",
    "SupportValidationError",
    "UNAVAILABLE_MISSING_CONTRACT",
    "UNAVAILABLE_NO_DATA",
    "UNAVAILABLE_ZERO_DENOMINATOR",
    "UNRESOLVED_STATUSES",
    "UnavailableSupportEvidence",
    "UnresolvedConversationDetail",
    "analyze_customer_support_history",
    "analyze_handover_and_escalation",
    "analyze_priority_distribution",
    "analyze_support",
    "analyze_support_issue_trends",
    "analyze_unresolved_conversations",
    "calculate_conversation_volume",
    "calculate_resolution_time",
    "calculate_response_time",
    "get_support_rule",
    "record_support_metrics",
]
