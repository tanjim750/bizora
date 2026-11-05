"""Requirement-linked tests for BI §11 (Support Analysis) - Ticket T-009.

Tests verify:
- Deterministic conversation volume calculation across half-open periods.
- Response time analysis with explicit clock telemetry (open clocks, pending replies, inverted clocks).
- Resolution time analysis with explicit incomplete conversation handling.
- Unresolved conversations tracking and SLA breach contract handling.
- Priority distribution and performance breakdown (LOW, NORMAL, HIGH, URGENT).
- AI/Human handover tracking and exact Decimal escalation rate.
- Customer support history connecting conversations to orders, products, and shipments.
- Support issue trends connecting conversations to orders, products, and couriers.
- Snapshot recording for the five registered support metrics and collision detection.
- Cross-tenant business isolation.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from app import models
from app.business_intelligence import metrics, support as subject


D = Decimal
START = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
END = START + timedelta(days=7)


class SupportTestCase(TestCase):
    def setUp(self):
        self.a = self.business("shop-a")
        self.b = self.business("shop-b")
        for b in (self.a, self.b):
            metrics.sync_metric_registry(business_id=b.pk)

    def business(self, slug):
        return models.Business.objects.create(
            name=slug, slug=slug, currency="BDT", created_at=START, updated_at=START,
        )

    def customer(self, business=None, name="Customer"):
        return models.Customer.objects.create(
            business=business or self.a, display_name=name,
            created_at=START, updated_at=START,
        )

    def product(self, business=None, name="Widget"):
        return models.Product.objects.create(
            business=business or self.a, name=name,
            created_at=START, updated_at=START,
        )

    def order(self, customer, business=None, when=None):
        t = when or START
        return models.Order.objects.create(
            business=business or self.a,
            customer=customer,
            order_number=f"ORD-{models.Order.objects.count() + 1}",
            status="DELIVERED",
            currency="BDT",
            total_amount=D("500.00"),
            ordered_at=t,
            created_at=t,
            updated_at=t,
        )

    def conversation(
        self,
        *,
        business=None,
        customer=None,
        channel="MESSENGER",
        status="OPEN",
        priority="NORMAL",
        started_at=None,
        resolved_at=None,
        ai_handover_state=None,
        source_metadata=None,
    ):
        t = started_at or START
        return models.Conversation.objects.create(
            business=business or self.a,
            customer=customer,
            channel=channel,
            status=status,
            priority=priority,
            started_at=t,
            resolved_at=resolved_at,
            ai_handover_state=ai_handover_state,
            source_metadata=source_metadata,
            created_at=t,
            updated_at=t,
        )

    def message(
        self,
        conversation,
        *,
        direction="INBOUND",
        sender_type="CUSTOMER",
        sent_at=None,
        content="Hello",
    ):
        t = sent_at or conversation.started_at
        return models.Message.objects.create(
            conversation=conversation,
            direction=direction,
            sender_type=sender_type,
            content=content,
            sent_at=t,
            created_at=t,
            updated_at=t,
        )

    def test_conversation_volume_and_tenant_isolation(self):
        # 2 conversations in scope for shop-a
        c1 = self.conversation(started_at=START + timedelta(hours=1), channel="WHATSAPP")
        c2 = self.conversation(started_at=START + timedelta(hours=2), channel="MESSENGER")

        # 1 conversation outside period (before)
        self.conversation(started_at=START - timedelta(hours=1))
        # 1 conversation outside period (at boundary period_end)
        self.conversation(started_at=END)
        # 1 conversation for shop-b
        self.conversation(business=self.b, started_at=START + timedelta(hours=1))

        # Overall volume
        volume_a = subject.calculate_conversation_volume(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )
        self.assertEqual(volume_a, 2)

        # Dimensioned volume by channel
        whatsapp_volume = subject.calculate_conversation_volume(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            dimension_type="CHANNEL",
            dimension_value="WHATSAPP",
        )
        self.assertEqual(whatsapp_volume, 1)

        # Shop b volume
        volume_b = subject.calculate_conversation_volume(
            business_id=self.b.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )
        self.assertEqual(volume_b, 1)

    def test_response_time_calculation_and_explicit_clocks(self):
        # Conv 1: Customer asks at t0+10s, Agent replies at t0+40s -> duration = 30s
        c1 = self.conversation(started_at=START)
        t_in_1 = START + timedelta(seconds=10)
        t_out_1 = START + timedelta(seconds=40)
        self.message(c1, direction="INBOUND", sender_type="CUSTOMER", sent_at=t_in_1)
        self.message(c1, direction="OUTBOUND", sender_type="AGENT", sent_at=t_out_1)

        # Conv 2: Customer asks at t0+20s, but NO outbound reply yet!
        # Incomplete response clock: must NOT be 0s, tracked in pending_response_clocks_count
        c2 = self.conversation(started_at=START)
        t_in_2 = START + timedelta(seconds=20)
        self.message(c2, direction="INBOUND", sender_type="CUSTOMER", sent_at=t_in_2)

        # Conv 3: Outbound reply timestamp earlier than inbound message (clock skew anomaly)
        # Inverted clock: excluded from durations, tracked in inverted_clocks_count
        c3 = self.conversation(started_at=START)
        t_in_3 = START + timedelta(seconds=50)
        t_out_3 = START + timedelta(seconds=30)
        self.message(c3, direction="INBOUND", sender_type="CUSTOMER", sent_at=t_in_3)
        self.message(c3, direction="OUTBOUND", sender_type="AI", sent_at=t_out_3)

        resp_summary = subject.calculate_response_time(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        self.assertEqual(resp_summary.initial_response_count, 1)
        self.assertEqual(resp_summary.average_initial_response_time, D("30.0000"))
        self.assertEqual(resp_summary.pending_response_clocks_count, 1)
        self.assertEqual(resp_summary.inverted_clocks_count, 1)

    def test_response_time_unavailable_when_zero_responses(self):
        # Only unanswered messages
        c = self.conversation(started_at=START)
        self.message(c, direction="INBOUND", sender_type="CUSTOMER", sent_at=START + timedelta(seconds=10))

        resp_summary = subject.calculate_response_time(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        self.assertEqual(resp_summary.initial_response_count, 0)
        self.assertEqual(resp_summary.average_initial_response_time, metrics.UNAVAILABLE)
        self.assertEqual(resp_summary.pending_response_clocks_count, 1)

    def test_resolution_time_calculation_and_incomplete_conversations(self):
        # Conv 1: Resolved in 300s
        t_res_1 = START + timedelta(seconds=300)
        self.conversation(started_at=START, status="RESOLVED", resolved_at=t_res_1)

        # Conv 2: Closed in 900s
        t_res_2 = START + timedelta(seconds=900)
        self.conversation(started_at=START, status="CLOSED", resolved_at=t_res_2)

        # Conv 3: Incomplete (OPEN, no resolved_at) -> clock open, excluded from durations, counted as unresolved
        self.conversation(started_at=START, status="OPEN", resolved_at=None)

        # Conv 4: Corrupted clock: resolved_at < started_at -> inverted clock anomaly
        self.conversation(started_at=START + timedelta(hours=2), status="RESOLVED", resolved_at=START + timedelta(hours=1))

        # Conv 5: Status RESOLVED, but missing resolved_at timestamp
        self.conversation(started_at=START, status="RESOLVED", resolved_at=None)

        res_summary = subject.calculate_resolution_time(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        # Average of 300s and 900s is 600s
        self.assertEqual(res_summary.resolved_conversations_count, 2)
        self.assertEqual(res_summary.average_resolution_time, D("600.0000"))
        self.assertEqual(res_summary.unresolved_conversations_count, 1)
        self.assertEqual(res_summary.missing_resolution_timestamp_count, 1)
        self.assertEqual(res_summary.inverted_clocks_count, 1)

    def test_resolution_time_unavailable_when_no_resolutions(self):
        # Only open conversations
        self.conversation(started_at=START, status="OPEN")
        self.conversation(started_at=START, status="PENDING")

        res_summary = subject.calculate_resolution_time(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        self.assertEqual(res_summary.resolved_conversations_count, 0)
        self.assertEqual(res_summary.average_resolution_time, metrics.UNAVAILABLE)
        self.assertEqual(res_summary.unresolved_conversations_count, 2)

    def test_unresolved_conversations_and_sla_breach(self):
        # Conv 1: Started 2 days before END -> age = 48 hours = 172800s
        c1 = self.conversation(started_at=END - timedelta(days=2), status="OPEN", priority="HIGH")
        # Conv 2: Started 1 hour before END -> age = 3600s
        c2 = self.conversation(started_at=END - timedelta(hours=1), status="PENDING", priority="LOW")
        # Conv 3: Resolved -> not in unresolved list
        self.conversation(started_at=START, status="RESOLVED", resolved_at=START + timedelta(hours=1))

        # With SLA threshold of 24 hours (86400s): c1 breaches, c2 does not
        unresolved = subject.analyze_unresolved_conversations(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            expected_resolution_seconds=86400,
        )

        self.assertEqual(len(unresolved), 2)
        c1_detail = next(u for u in unresolved if u.conversation_id == c1.pk)
        c2_detail = next(u for u in unresolved if u.conversation_id == c2.pk)

        self.assertEqual(c1_detail.age_seconds, D("172800"))
        self.assertTrue(c1_detail.breached_sla)

        self.assertEqual(c2_detail.age_seconds, D("3600"))
        self.assertFalse(c2_detail.breached_sla)

        # Full analysis check: without SLA threshold, returns UnavailableSupportEvidence
        analysis_no_sla = subject.analyze_support(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            expected_resolution_seconds=None,
        )
        self.assertIsInstance(analysis_no_sla.sla_breach_detection, subject.UnavailableSupportEvidence)
        self.assertEqual(
            analysis_no_sla.sla_breach_detection.reason,
            subject.UNAVAILABLE_MISSING_CONTRACT,
        )

    def test_priority_distribution_and_performance(self):
        # 1 URGENT, 2 HIGH, 1 NORMAL
        t_res = START + timedelta(seconds=120)
        c_urgent = self.conversation(started_at=START, priority="URGENT", status="RESOLVED", resolved_at=t_res)
        self.conversation(started_at=START, priority="HIGH", status="OPEN")
        self.conversation(started_at=START, priority="HIGH", status="OPEN")
        self.conversation(started_at=START, priority="NORMAL", status="OPEN")

        dist = subject.analyze_priority_distribution(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        by_priority = {p.priority: p for p in dist}

        # URGENT: 1 of 4 = 0.2500, average_resolution_time = 120.0000
        self.assertEqual(by_priority["URGENT"].conversation_count, 1)
        self.assertEqual(by_priority["URGENT"].share_of_total, D("0.2500"))
        self.assertEqual(by_priority["URGENT"].average_resolution_time, D("120.0000"))

        # HIGH: 2 of 4 = 0.5000, 2 unresolved
        self.assertEqual(by_priority["HIGH"].conversation_count, 2)
        self.assertEqual(by_priority["HIGH"].share_of_total, D("0.5000"))
        self.assertEqual(by_priority["HIGH"].unresolved_count, 2)

        # NORMAL: 1 of 4 = 0.2500
        self.assertEqual(by_priority["NORMAL"].conversation_count, 1)
        self.assertEqual(by_priority["NORMAL"].share_of_total, D("0.2500"))

        # LOW: 0 conversations
        self.assertEqual(by_priority["LOW"].conversation_count, 0)
        self.assertEqual(by_priority["LOW"].share_of_total, D("0.0000"))

    def test_handover_and_escalation_analysis(self):
        # Conv 1: ai_handover_state = 'HANDOVER_TO_HUMAN' -> escalated!
        c1 = self.conversation(started_at=START, ai_handover_state="HANDOVER_TO_HUMAN")

        # Conv 2: assignment AI followed by assignment AGENT -> escalated!
        c2 = self.conversation(started_at=START)
        models.ConversationAssignment.objects.create(
            conversation=c2, assignee_type="AI", assigned_at=START, created_at=START,
        )
        models.ConversationAssignment.objects.create(
            conversation=c2, assignee_type="AGENT", assigned_at=START + timedelta(minutes=5), created_at=START,
        )

        # Conv 3: Only handled by AI, not escalated
        c3 = self.conversation(started_at=START)
        models.ConversationAssignment.objects.create(
            conversation=c3, assignee_type="AI", assigned_at=START, created_at=START,
        )

        handover = subject.analyze_handover_and_escalation(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        self.assertEqual(handover.total_conversations, 3)
        self.assertEqual(handover.escalated_conversations_count, 2)
        # 2 / 3 = 0.6667
        self.assertEqual(handover.escalation_rate, D("0.6667"))
        self.assertGreaterEqual(handover.ai_to_human_handover_count, 2)

    def test_customer_support_history(self):
        cust = self.customer(name="Rahim")
        prod = self.product(name="Shirt")
        ord1 = self.order(cust, when=START)
        models.OrderItem.objects.create(
            order=ord1, product=prod, product_name="Shirt", quantity=2,
            unit_price=D("250.00"), total_amount=D("500.00"), created_at=START,
        )
        ship1 = models.Shipment.objects.create(
            business=self.a, customer=cust, order=ord1, provider="REDX", status="DELIVERED",
            tracking_code="RX-100", created_at=START, updated_at=START,
        )

        # 2 conversations for Rahim (repeat contact)
        c1 = self.conversation(customer=cust, started_at=START, status="RESOLVED", resolved_at=START + timedelta(minutes=10))
        c2 = self.conversation(customer=cust, started_at=START + timedelta(days=1), status="OPEN")

        summary = subject.analyze_customer_support_history(
            business_id=self.a.pk,
            customer_id=cust.pk,
        )

        self.assertEqual(summary.customer_id, cust.pk)
        self.assertEqual(summary.total_conversations, 2)
        self.assertEqual(summary.unresolved_conversations, 1)
        self.assertTrue(summary.repeat_contact)
        self.assertEqual(summary.order_ids, (ord1.pk,))
        self.assertEqual(summary.product_ids, (prod.pk,))
        self.assertEqual(summary.shipment_ids, (ship1.pk,))

    def test_support_issue_trends(self):
        cust = self.customer()
        prod = self.product(name="Shoes")
        ord1 = self.order(cust, when=START)
        models.OrderItem.objects.create(
            order=ord1, product=prod, product_name="Shoes", quantity=1,
            unit_price=D("500.00"), total_amount=D("500.00"), created_at=START,
        )
        models.Shipment.objects.create(
            business=self.a, customer=cust, order=ord1, provider="STEADFAST", status="DELIVERED",
            tracking_code="SF-100", created_at=START, updated_at=START,
        )

        # Conversation 1 linked to ord1 via Call
        c1 = self.conversation(customer=cust, started_at=START)
        models.Call.objects.create(
            business=self.a, customer=cust, conversation=c1, order=ord1, direction="INBOUND",
            status="COMPLETED", created_at=START, updated_at=START,
        )

        # Conversation 2 linked via source_metadata
        c2 = self.conversation(customer=cust, started_at=START + timedelta(hours=1), source_metadata={"order_id": ord1.pk})

        trends = subject.analyze_support_issue_trends(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        by_area = {t.issue_area: t for t in trends}
        self.assertIn("ORDER", by_area)
        self.assertEqual(by_area["ORDER"].entity_id_or_label, str(ord1.pk))
        self.assertEqual(by_area["ORDER"].conversation_count, 2)

        self.assertIn("PRODUCT", by_area)
        self.assertEqual(by_area["PRODUCT"].entity_id_or_label, str(prod.pk))

        self.assertIn("COURIER", by_area)
        self.assertEqual(by_area["COURIER"].entity_id_or_label, "STEADFAST")

    def test_record_support_metrics_and_snapshot_collision(self):
        # Create a conversation with response, resolution, and escalation
        c = self.conversation(
            started_at=START,
            status="RESOLVED",
            resolved_at=START + timedelta(seconds=200),
            ai_handover_state="ESCALATED",
        )
        self.message(c, direction="INBOUND", sender_type="CUSTOMER", sent_at=START + timedelta(seconds=10))
        self.message(c, direction="OUTBOUND", sender_type="AGENT", sent_at=START + timedelta(seconds=30))

        # Record snapshots
        recording = subject.record_support_metrics(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        self.assertEqual(len(recording.snapshots), 5)
        snap_map = dict(recording.snapshots)

        # All 5 metrics recorded
        self.assertEqual(snap_map["conversation_volume"].status, metrics.WRITE_CREATED)
        self.assertEqual(snap_map["response_time"].status, metrics.WRITE_CREATED)
        self.assertEqual(snap_map["resolution_time"].status, metrics.WRITE_CREATED)
        self.assertEqual(snap_map["unresolved_cases"].status, metrics.WRITE_CREATED)
        self.assertEqual(snap_map["escalation_rate"].status, metrics.WRITE_CREATED)

        # Verify values in database
        vol_snap = metrics.get_metric_snapshot(
            business_id=self.a.pk,
            metric_key="bi.metric.support_conversation_volume.v1",
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )
        self.assertIsNotNone(vol_snap)
        self.assertEqual(vol_snap.value, D("1.0000"))

        # Re-recording with same data is idempotent (UNCHANGED)
        rec2 = subject.record_support_metrics(
            business_id=self.a.pk,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )
        for _, write_res in rec2.snapshots:
            self.assertEqual(write_res.status, metrics.WRITE_UNCHANGED)

        # Test collision detection: manually record a snapshot with an alien calculation_rule
        alien_key = "bi.metric.support_conversation_volume.v1"
        metrics.record_metric_snapshot(
            business_id=self.a.pk,
            metric_key=alien_key,
            value=D("99.0000"),
            period_type="WEEK",
            period_start=START,
            period_end=END,
            calculation_rule="bi.metric.support_conversation_volume.v1.alien_rule",
        )

        with self.assertRaises(metrics.MetricSnapshotConflictError):
            subject.record_support_metrics(
                business_id=self.a.pk,
                period_type="WEEK",
                period_start=START,
                period_end=END,
            )

    def test_validation_errors(self):
        # Invalid business
        with self.assertRaises(subject.SupportValidationError):
            subject.analyze_support(
                business_id=-1,
                period_type="WEEK",
                period_start=START,
                period_end=END,
            )

        # Non-existent business
        with self.assertRaises(subject.SupportScopeError):
            subject.analyze_support(
                business_id=999999,
                period_type="WEEK",
                period_start=START,
                period_end=END,
            )

        # Inverted period
        with self.assertRaises(subject.SupportValidationError):
            subject.analyze_support(
                business_id=self.a.pk,
                period_type="WEEK",
                period_start=END,
                period_end=START,
            )

        # Naive datetime
        naive_start = datetime(2026, 10, 1, 0, 0)
        with self.assertRaises(subject.SupportValidationError):
            subject.analyze_support(
                business_id=self.a.pk,
                period_type="WEEK",
                period_start=naive_start,
                period_end=END,
            )

        # Invalid dimension_type
        with self.assertRaises(subject.SupportValidationError):
            subject.analyze_support(
                business_id=self.a.pk,
                period_type="WEEK",
                period_start=START,
                period_end=END,
                dimension_type="NONEXISTENT_DIMENSION",
                dimension_value="VAL",
            )

        # Customer not in business
        foreign_cust = self.customer(business=self.b)
        with self.assertRaises(subject.SupportScopeError):
            subject.analyze_customer_support_history(
                business_id=self.a.pk,
                customer_id=foreign_cust.pk,
            )

        # Unknown rule
        with self.assertRaises(subject.SupportValidationError):
            subject.get_support_rule("unknown_metric")
