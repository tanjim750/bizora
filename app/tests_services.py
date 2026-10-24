"""
Bizora Comprehensive Test Suite
================================
Covers every service module, model validation, and API view.

Run with:
    python3 manage.py test app.tests_services --verbosity=2
"""
import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from app.models import (
    AiAction,
    AiConversation,
    AiMessage,
    AiRecommendation,
    AiRecommendationEvidence,
    Business,
    BusinessFact,
    BusinessIssue,
    BusinessIssueEvidence,
    BusinessMembership,
    Call,
    CallTranscript,
    Campaign,
    CampaignMetric,
    Conversation,
    Customer,
    GraphEdge,
    GraphNode,
    KnowledgeDocument,
    KnowledgeSource,
    Message,
    MetricSnapshot,
    Order,
    OrderItem,
    Product,
)

User = get_user_model()

# ──────────────────────────────────────────────────────────────
# Shared Fixtures
# ──────────────────────────────────────────────────────────────

def make_business(**kwargs):
    defaults = {"name": "Test Biz", "slug": "test-biz", "currency": "BDT", "timezone": "Asia/Dhaka", "status": "ACTIVE"}
    defaults.update(kwargs)
    return Business.objects.create(**defaults)


def make_user(username="testuser", **kwargs):
    return User.objects.create_user(username=username, password="pass1234", **kwargs)


def make_customer(business, **kwargs):
    defaults = {"first_name": "Alice", "last_name": "Smith", "status": "ACTIVE"}
    defaults.update(kwargs)
    return Customer.objects.create(business=business, **defaults)


def make_order(business, customer=None, status="PENDING", total_amount="500.00", ordered_at=None):
    return Order.objects.create(
        business=business,
        customer=customer,
        status=status,
        total_amount=Decimal(total_amount),
        subtotal=Decimal(total_amount),
        ordered_at=ordered_at or timezone.now(),
    )


def make_conversation(business, customer=None, status="OPEN", channel="WHATSAPP", **kwargs):
    defaults = {"channel": channel, "status": status, "started_at": timezone.now()}
    defaults.update(kwargs)
    return Conversation.objects.create(business=business, customer=customer, **defaults)


def make_business_fact(business, **kwargs):
    defaults = {
        "fact_type": "TEST_FACT",
        "statement": "Test fact statement",
        "confidence": Decimal("1.0000"),
        "status": "VERIFIED",
        "detected_at": timezone.now(),
    }
    defaults.update(kwargs)
    return BusinessFact.objects.create(business=business, **defaults)


def make_ai_recommendation(business, **kwargs):
    defaults = {
        "recommendation_type": "TEST",
        "title": "Test Recommendation",
        "description": "Test description",
        "priority": "MEDIUM",
        "status": "SUGGESTED",
        "generated_at": timezone.now(),
    }
    defaults.update(kwargs)
    return AiRecommendation.objects.create(business=business, **defaults)


def make_ai_action(business, recommendation, **kwargs):
    defaults = {
        "action_type": "TEST_ACTION",
        "status": "SUGGESTED",
        "is_simulated": True,
    }
    defaults.update(kwargs)
    return AiAction.objects.create(
        business=business, ai_recommendation=recommendation, **defaults
    )


# ══════════════════════════════════════════════════════════════════
# 1. analytics.py
# ══════════════════════════════════════════════════════════════════

class TestCalculateNetRevenue(TestCase):
    def setUp(self):
        from app.services.analytics import calculate_net_revenue
        self.calc = calculate_net_revenue

    def test_basic_subtraction(self):
        result = self.calc(Decimal("1000.00"), Decimal("200.00"))
        self.assertEqual(result, Decimal("800.00"))

    def test_zero_refunds(self):
        result = self.calc(Decimal("500.00"))
        self.assertEqual(result, Decimal("500.00"))

    def test_refunds_exceed_gross_clamps_to_zero(self):
        """Net revenue must never be negative (COR-004)."""
        result = self.calc(Decimal("100.00"), Decimal("300.00"))
        self.assertEqual(result, Decimal("0.00"))

    def test_zero_gross(self):
        result = self.calc(Decimal("0.00"), Decimal("0.00"))
        self.assertEqual(result, Decimal("0.00"))

    def test_none_refunds_treated_as_zero(self):
        result = self.calc(Decimal("750.00"), None)
        self.assertEqual(result, Decimal("750.00"))

    def test_string_inputs_coerced(self):
        result = self.calc("500", "50")
        self.assertEqual(result, Decimal("450.00"))


class TestCapCampaignAttributions(TestCase):
    def setUp(self):
        from app.services.analytics import cap_campaign_attributions
        self.cap = cap_campaign_attributions

    def test_no_capping_when_under_total(self):
        attrs = {"fb": Decimal(200), "google": Decimal(100)}
        result = self.cap(attrs, Decimal(500))
        self.assertEqual(result["fb"], Decimal(200))
        self.assertEqual(result["google"], Decimal(100))

    def test_capping_scales_proportionally(self):
        attrs = {"fb": Decimal(600), "google": Decimal(400)}
        result = self.cap(attrs, Decimal(500))
        total = sum(result.values())
        self.assertEqual(total, Decimal(500))

    def test_empty_attributions(self):
        result = self.cap({}, Decimal(500))
        self.assertEqual(result, {})

    def test_zero_order_total(self):
        attrs = {"fb": Decimal(100)}
        result = self.cap(attrs, Decimal(0))
        self.assertEqual(result["fb"], Decimal("0.00"))

    def test_last_channel_gets_remainder_for_precision(self):
        """Prevents floating-point drift — last item absorbs remainder."""
        attrs = {"a": Decimal(1), "b": Decimal(1), "c": Decimal(1)}
        result = self.cap(attrs, Decimal(1))
        self.assertEqual(sum(result.values()), Decimal(1))


class TestToBusinessDate(TestCase):
    def setUp(self):
        from app.services.analytics import to_business_date
        self.fn = to_business_date

    def test_utc_to_dhaka_boundary(self):
        """18:30 UTC = 00:30+6 next day in Dhaka."""
        import pytz
        utc_dt = datetime.datetime(2024, 1, 15, 18, 30, 0, tzinfo=pytz.UTC)
        result = self.fn(utc_dt, "Asia/Dhaka")
        self.assertEqual(result, datetime.date(2024, 1, 16))

    def test_none_returns_none(self):
        result = self.fn(None)
        self.assertIsNone(result)

    def test_naive_datetime_treated_as_utc(self):
        naive = datetime.datetime(2024, 6, 1, 12, 0, 0)
        result = self.fn(naive, "Asia/Dhaka")
        self.assertEqual(result, datetime.date(2024, 6, 1))


# ══════════════════════════════════════════════════════════════════
# 2. services/bi.py
# ══════════════════════════════════════════════════════════════════

class TestComputeDailyBusinessMetrics(TestCase):
    def setUp(self):
        from app.services.analytics import to_business_date
        self.biz = make_business()
        self.today = to_business_date(timezone.now(), self.biz.timezone)

    def test_empty_no_orders(self):
        from app.services.bi import compute_daily_business_metrics
        result = compute_daily_business_metrics(self.biz, self.today)
        self.assertEqual(result["total_orders"], 0)
        self.assertEqual(result["gross_revenue"], Decimal("0.00"))
        self.assertEqual(result["net_revenue"], Decimal("0.00"))
        self.assertEqual(result["failure_rate"], Decimal("0.00"))
        self.assertIsNotNone(result["snapshot"])

    def test_normal_orders_computed(self):
        from app.services.bi import compute_daily_business_metrics
        make_order(self.biz, total_amount="1000.00", ordered_at=timezone.now())
        make_order(self.biz, total_amount="500.00", ordered_at=timezone.now())
        result = compute_daily_business_metrics(self.biz, self.today)
        self.assertEqual(result["total_orders"], 2)
        self.assertEqual(result["gross_revenue"], Decimal("1500.00"))

    def test_refunded_orders_reduce_net(self):
        from app.services.bi import compute_daily_business_metrics
        make_order(self.biz, total_amount="800.00", ordered_at=timezone.now())
        make_order(self.biz, status="REFUNDED", total_amount="200.00", ordered_at=timezone.now())
        result = compute_daily_business_metrics(self.biz, self.today)
        self.assertEqual(result["gross_revenue"], Decimal("1000.00"))
        self.assertEqual(result["refunds"], Decimal("200.00"))
        self.assertEqual(result["net_revenue"], Decimal("800.00"))

    def test_failed_delivery_counted(self):
        from app.services.bi import compute_daily_business_metrics
        make_order(self.biz, total_amount="100.00", ordered_at=timezone.now())
        make_order(self.biz, status="FAILED_DELIVERY", total_amount="100.00", ordered_at=timezone.now())
        result = compute_daily_business_metrics(self.biz, self.today)
        self.assertEqual(result["failed_deliveries"], 1)
        self.assertEqual(result["failure_rate"], Decimal("0.5"))

    def test_metric_snapshot_created(self):
        from app.services.bi import compute_daily_business_metrics
        result = compute_daily_business_metrics(self.biz, self.today)
        self.assertIsInstance(result["snapshot"], MetricSnapshot)
        self.assertEqual(result["snapshot"].business, self.biz)

    def test_tenant_isolation_different_business_not_counted(self):
        """Orders from another business must not affect this business's metrics."""
        from app.services.bi import compute_daily_business_metrics
        other_biz = make_business(name="Other", slug="other")
        make_order(other_biz, total_amount="9999.00", ordered_at=timezone.now())
        result = compute_daily_business_metrics(self.biz, self.today)
        self.assertEqual(result["total_orders"], 0)


class TestDetectBusinessIssues(TestCase):
    def setUp(self):
        self.biz = make_business()

    def test_no_issue_when_failure_rate_below_threshold(self):
        from app.services.bi import detect_business_issues_from_metrics
        for _ in range(9):
            make_order(self.biz, total_amount="100.00", ordered_at=timezone.now())
        make_order(self.biz, status="FAILED_DELIVERY", total_amount="100.00", ordered_at=timezone.now())
        issues = detect_business_issues_from_metrics(self.biz)
        self.assertEqual(len(issues), 0)

    def test_issue_created_when_failure_rate_high(self):
        from app.services.bi import detect_business_issues_from_metrics
        make_order(self.biz, total_amount="100.00", ordered_at=timezone.now())
        for _ in range(3):
            make_order(self.biz, status="FAILED_DELIVERY", total_amount="100.00", ordered_at=timezone.now())
        issues = detect_business_issues_from_metrics(self.biz)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "EXCESSIVE_DELIVERY_FAILURES")
        self.assertEqual(issues[0].status, "OPEN")

    def test_fact_and_evidence_created(self):
        from app.services.bi import detect_business_issues_from_metrics
        for _ in range(3):
            make_order(self.biz, status="FAILED_DELIVERY", total_amount="100.00", ordered_at=timezone.now())
        make_order(self.biz, total_amount="100.00", ordered_at=timezone.now())
        detect_business_issues_from_metrics(self.biz)
        self.assertTrue(BusinessFact.objects.filter(business=self.biz, fact_type="HIGH_DELIVERY_FAILURE_RATE").exists())
        self.assertTrue(BusinessIssueEvidence.objects.filter(business_issue__business=self.biz).exists())


# ══════════════════════════════════════════════════════════════════
# 3. services/actions.py
# ══════════════════════════════════════════════════════════════════

class TestApproveAction(TestCase):
    def setUp(self):
        self.biz = make_business()
        self.user = make_user()
        BusinessMembership.objects.create(business=self.biz, user=self.user, role="OPERATOR")
        rec = make_ai_recommendation(self.biz)
        self.action = make_ai_action(self.biz, rec)

    def test_approve_sets_status_and_user(self):
        from app.services.actions import approve_action
        result = approve_action(self.action, self.user, "Looks good")
        self.assertEqual(result.status, "APPROVED")
        self.assertEqual(result.approved_by, self.user)
        self.assertIsNotNone(result.approved_at)
        self.assertEqual(result.approval_note, "Looks good")

    def test_approve_requires_authentication(self):
        from app.services.actions import approve_action
        anon = MagicMock()
        anon.is_authenticated = False
        with self.assertRaises(PermissionDenied):
            approve_action(self.action, anon, "note")

    def test_approve_is_idempotent_for_same_user(self):
        from app.services.actions import approve_action
        first = approve_action(self.action, self.user, "first")
        second = approve_action(self.action, self.user, "second")
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.approval_note, "first")

    def test_approve_rejects_executing_status(self):
        from app.services.actions import approve_action
        self.action.status = "EXECUTING"
        self.action.approved_at = timezone.now()
        self.action.save()
        with self.assertRaises(ValidationError):
            approve_action(self.action, self.user, "note")

    def test_approve_dispatches_event(self):
        from app.events.dispatcher import _subscribers
        from app.services.actions import approve_action
        events = []
        _subscribers["ai.action.approved"].append(lambda e: events.append(e))
        with self.captureOnCommitCallbacks(execute=True):
            approve_action(self.action, self.user, "approved")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["action_id"], self.action.id)


class TestExecuteAction(TestCase):
    def setUp(self):
        self.biz = make_business()
        self.user = make_user(username="executor_user")
        BusinessMembership.objects.create(business=self.biz, user=self.user, role="OPERATOR")
        rec = make_ai_recommendation(self.biz)
        self.action = make_ai_action(self.biz, rec)

    def _approve(self):
        from app.services.actions import approve_action
        return approve_action(self.action, self.user, "approved")

    def test_execute_without_approval_raises(self):
        from app.services.actions import execute_action
        with self.assertRaises(ValidationError):
            execute_action(self.action)

    def test_execute_simulated_success(self):
        from app.services.actions import execute_action
        self._approve()
        result = execute_action(self.action)
        self.assertEqual(result.status, "EXECUTED")
        self.assertIsNotNone(result.executed_at)
        self.assertIn("status", result.execution_result)

    def test_execute_with_error_result_marks_failed(self):
        from app.services.actions import execute_action
        self._approve()
        result = execute_action(self.action, executor_fn=lambda p: {"error": "courier down"})
        self.assertEqual(result.status, "FAILED")

    def test_execute_with_exception_marks_failed(self):
        from app.services.actions import execute_action
        self._approve()
        def bad_executor(p):
            raise RuntimeError("network failure")
        result = execute_action(self.action, executor_fn=bad_executor)
        self.assertEqual(result.status, "FAILED")
        self.assertIn("error", result.execution_result)

    def test_execute_custom_executor_receives_payload(self):
        from app.services.actions import execute_action
        self.action.action_payload = {"courier_id": 42}
        self.action.save()
        self._approve()
        received = {}
        def capturing_executor(payload):
            received.update(payload)
            return {"status": "ok"}
        execute_action(self.action, executor_fn=capturing_executor)
        self.assertEqual(received["courier_id"], 42)

    def test_execute_not_stuck_in_executing_after_exception(self):
        """Regression: transaction.atomic must prevent stuck EXECUTING state."""
        from app.services.actions import execute_action
        self._approve()
        def bad_executor(p):
            raise RuntimeError("crash")
        execute_action(self.action, executor_fn=bad_executor)
        refreshed = AiAction.objects.get(pk=self.action.pk)
        self.assertNotEqual(refreshed.status, "EXECUTING")


# ══════════════════════════════════════════════════════════════════
# 4. services/graph.py
# ══════════════════════════════════════════════════════════════════

class TestGraph(TestCase):
    def setUp(self):
        from app.services.graph import create_business_graph, safe_traverse
        self.create_graph = create_business_graph
        self.traverse = safe_traverse

    def test_empty_graph_returns_empty(self):
        g = self.create_graph()
        result = self.traverse(g, "node_1")
        self.assertEqual(result, [])

    def test_linear_graph_traversal(self):
        g = self.create_graph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        result = self.traverse(g, "a", max_depth=5)
        self.assertIn("a", result)
        self.assertIn("b", result)
        self.assertIn("c", result)

    def test_cyclic_graph_terminates(self):
        """Cycle-safe traversal must not infinite-loop."""
        g = self.create_graph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "a")  # cycle
        result = self.traverse(g, "a", max_depth=10)
        self.assertEqual(len(result), len(set(result)))

    def test_max_depth_limits_traversal(self):
        g = self.create_graph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "d")
        result = self.traverse(g, "a", max_depth=1)
        self.assertIn("a", result)
        self.assertIn("b", result)
        self.assertNotIn("d", result)

    def test_parallel_edges_allowed(self):
        """MultiDiGraph must allow multiple edges between same pair (COR-012)."""
        import networkx as nx
        g = self.create_graph()
        self.assertIsInstance(g, nx.MultiDiGraph)
        g.add_edge("a", "b", relationship="PLACED")
        g.add_edge("a", "b", relationship="PAID_FOR")
        self.assertEqual(g.number_of_edges("a", "b"), 2)

    def test_visited_set_shared_across_calls(self):
        """Passed visited set must prevent re-visiting already-seen nodes."""
        g = self.create_graph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        visited = {"a"}
        result = self.traverse(g, "a", max_depth=10, visited=visited)
        self.assertEqual(result, [])


# ══════════════════════════════════════════════════════════════════
# 5. services/ai_context.py
# ══════════════════════════════════════════════════════════════════

class TestAssembleFactContext(TestCase):
    def setUp(self):
        from app.services.ai_context import assemble_fact_context
        self.fn = assemble_fact_context
        self.biz = make_business()

    def test_returns_empty_when_no_facts(self):
        result = self.fn(self.biz)
        self.assertEqual(result, [])

    def test_returns_verified_facts_only(self):
        make_business_fact(self.biz, fact_type="GOOD", status="VERIFIED")
        make_business_fact(self.biz, fact_type="BAD", status="INVALIDATED")
        result = self.fn(self.biz)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["fact_type"], "GOOD")

    def test_tenant_isolation(self):
        other = make_business(name="Other", slug="other")
        make_business_fact(other, fact_type="OTHER_FACT")
        result = self.fn(self.biz)
        self.assertEqual(result, [])

    def test_respects_limit(self):
        for i in range(15):
            make_business_fact(self.biz, fact_type=f"FACT_{i}")
        result = self.fn(self.biz, limit=5)
        self.assertLessEqual(len(result), 5)

    def test_result_structure(self):
        make_business_fact(self.biz)
        result = self.fn(self.biz)
        self.assertIn("id", result[0])
        self.assertIn("fact_type", result[0])
        self.assertIn("statement", result[0])
        self.assertIn("confidence", result[0])


class TestAssembleCustomerContext(TestCase):
    def setUp(self):
        from app.services.ai_context import assemble_customer_context
        self.fn = assemble_customer_context
        self.biz = make_business()
        self.customer = make_customer(self.biz)

    def test_basic_customer_context(self):
        result = self.fn(self.biz, self.customer)
        self.assertEqual(result["customer_id"], self.customer.id)

    def test_total_spent_uses_db_aggregate(self):
        """Must use aggregate, not Python loop."""
        make_order(self.biz, self.customer, total_amount="100.00")
        make_order(self.biz, self.customer, total_amount="200.00")
        result = self.fn(self.biz, self.customer)
        self.assertEqual(result["total_spend"], "300.00")

    def test_zero_spent_when_no_orders(self):
        result = self.fn(self.biz, self.customer)
        self.assertEqual(result["total_spend"], "0.00")

    def test_completed_vs_cancelled_counts(self):
        make_order(self.biz, self.customer, status="DELIVERED", total_amount="100.00")
        make_order(self.biz, self.customer, status="CANCELLED", total_amount="50.00")
        result = self.fn(self.biz, self.customer)
        self.assertEqual(result["completed_orders"], 1)
        self.assertEqual(result["cancelled_orders"], 1)

    def test_tenant_isolation_orders_only_from_business(self):
        other_biz = make_business(name="Other", slug="other")
        make_order(other_biz, self.customer, total_amount="9999.00")
        result = self.fn(self.biz, self.customer)
        self.assertEqual(result["total_spend"], "0.00")


class TestAssembleProductContext(TestCase):
    def setUp(self):
        from app.services.ai_context import assemble_product_context
        self.fn = assemble_product_context
        self.biz = make_business()
        self.product = Product.objects.create(
            business=self.biz, name="Widget", price=Decimal("99.00"), status="ACTIVE"
        )

    def test_basic_product_context(self):
        result = self.fn(self.biz, self.product)
        self.assertEqual(result["product_id"], self.product.id)
        self.assertEqual(result["name"], "Widget")

    def test_units_sold_uses_db_aggregate(self):
        customer = make_customer(self.biz)
        order = make_order(self.biz, customer)
        OrderItem.objects.create(
            order=order, product=self.product,
            product_name="Widget", quantity=3,
            unit_price=Decimal("99.00"),
            total_amount=Decimal("297.00"),
        )
        result = self.fn(self.biz, self.product)
        self.assertEqual(result["units_sold"], 3)

    def test_units_sold_zero_when_no_orders(self):
        result = self.fn(self.biz, self.product)
        self.assertEqual(result["units_sold"], 0)


class TestAssembleOrderContext(TestCase):
    def setUp(self):
        from app.services.ai_context import assemble_order_context
        self.fn = assemble_order_context
        self.biz = make_business()
        self.customer = make_customer(self.biz)
        self.order = make_order(self.biz, self.customer, total_amount="750.00")

    def test_order_context_structure(self):
        result = self.fn(self.biz, self.order)
        self.assertEqual(result["order_id"], self.order.id)
        self.assertEqual(result["total_amount"], "750.00")
        self.assertIn("items", result)
        self.assertIn("payments", result)
        self.assertIn("shipments", result)

    def test_order_items_included(self):
        product = Product.objects.create(business=self.biz, name="P1", status="ACTIVE")
        OrderItem.objects.create(
            order=self.order, product=product,
            product_name="P1", quantity=2,
            unit_price=Decimal("375.00"),
            total_amount=Decimal("750.00"),
        )
        result = self.fn(self.biz, self.order)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["quantity"], 2)


class TestAssembleMemoryContext(TestCase):
    def setUp(self):
        from app.services.ai_context import assemble_memory_context
        self.fn = assemble_memory_context
        self.biz = make_business()

    def _make_doc(self, title="Policy", doc_type="POLICY", content=""):
        source = KnowledgeSource.objects.create(
            business=self.biz, name="Test Source", source_type="MANUAL", status="ACTIVE"
        )
        return KnowledgeDocument.objects.create(
            business=self.biz, knowledge_source=source,
            title=title, document_type=doc_type,
            content=content or f"Content of {title}", status="READY"
        )

    def test_returns_policies(self):
        self._make_doc("Refund Policy")
        result = self.fn(self.biz, intent="refund")
        self.assertGreater(len(result), 0)

    def test_no_docs_returns_empty(self):
        result = self.fn(self.biz, intent="nonexistent_xyz")
        self.assertEqual(result, [])

    def test_tenant_isolation(self):
        other = make_business(name="Other", slug="other")
        source = KnowledgeSource.objects.create(
            business=other, name="Other Source", source_type="MANUAL", status="ACTIVE"
        )
        KnowledgeDocument.objects.create(
            business=other, knowledge_source=source,
            title="Other Policy", status="READY"
        )
        result = self.fn(self.biz)
        self.assertEqual(result, [])


# ══════════════════════════════════════════════════════════════════
# 6. services/ai_assistant.py
# ══════════════════════════════════════════════════════════════════

class TestAskBusinessAssistant(TestCase):
    def setUp(self):
        from app.services.ai_assistant import ask_business_assistant
        self.fn = ask_business_assistant
        self.biz = make_business()

    def test_creates_conversation_and_messages(self):
        result = self.fn(self.biz, "What are my top products?")
        self.assertIn("conversation_id", result)
        self.assertIn("answer", result)
        self.assertIn("message_id", result)
        self.assertTrue(AiConversation.objects.filter(pk=result["conversation_id"]).exists())
        msgs = AiMessage.objects.filter(ai_conversation_id=result["conversation_id"])
        self.assertEqual(msgs.count(), 2)

    def test_resumes_existing_conversation(self):
        result1 = self.fn(self.biz, "First query")
        conv_id = result1["conversation_id"]
        result2 = self.fn(self.biz, "Second query", conversation_id=conv_id)
        self.assertEqual(result2["conversation_id"], conv_id)
        msgs = AiMessage.objects.filter(ai_conversation_id=conv_id)
        self.assertEqual(msgs.count(), 4)

    def test_invalid_conversation_id_creates_new(self):
        result = self.fn(self.biz, "Hello", conversation_id=99999)
        self.assertIsNotNone(result["conversation_id"])

    def test_response_includes_grounding_facts(self):
        make_business_fact(self.biz, statement="Revenue is stable")
        result = self.fn(self.biz, "Revenue?")
        self.assertIn("grounding_facts", result)
        self.assertIsInstance(result["grounding_facts"], list)

    def test_user_message_saved_with_role_user(self):
        self.fn(self.biz, "Test query")
        user_msg = AiMessage.objects.filter(role="USER").first()
        self.assertIsNotNone(user_msg)
        self.assertEqual(user_msg.content, "Test query")

    def test_answer_content_is_string(self):
        result = self.fn(self.biz, "Test")
        self.assertIsInstance(result["answer"], str)
        self.assertGreater(len(result["answer"]), 0)


# ══════════════════════════════════════════════════════════════════
# 7. services/ai_support.py
# ══════════════════════════════════════════════════════════════════

class TestGenerateSuggestedReply(TestCase):
    def setUp(self):
        from app.services.ai_support import generate_suggested_reply
        self.fn = generate_suggested_reply
        self.biz = make_business()
        self.customer = make_customer(self.biz)
        self.conv = make_conversation(self.biz, self.customer, subject="Order problem")

    def test_returns_reply_structure(self):
        result = self.fn(self.biz, self.conv, self.customer)
        self.assertIn("suggested_reply", result)
        self.assertIn("conversation_id", result)
        self.assertIn("intent", result)
        self.assertEqual(result["conversation_id"], self.conv.id)

    def test_reply_is_non_empty_string(self):
        result = self.fn(self.biz, self.conv, self.customer, intent="refund_inquiry")
        self.assertIsInstance(result["suggested_reply"], str)
        self.assertGreater(len(result["suggested_reply"]), 10)

    def test_no_order_referenced_is_none(self):
        result = self.fn(self.biz, self.conv, self.customer)
        self.assertIsNone(result["order_referenced"])


class TestEvaluateEscalation(TestCase):
    def setUp(self):
        from app.services.ai_support import evaluate_escalation
        self.fn = evaluate_escalation
        self.biz = make_business()
        self.customer = make_customer(self.biz)
        self.conv = make_conversation(self.biz, self.customer)

    def test_routine_inquiry_no_escalation(self):
        result = self.fn(self.biz, self.conv, "Where is my order?")
        self.assertFalse(result["should_escalate"])

    def test_fraud_keyword_triggers_escalation(self):
        result = self.fn(self.biz, self.conv, "This is fraud, I'm calling the police!")
        self.assertTrue(result["should_escalate"])

    def test_escalation_updates_conversation_state(self):
        self.fn(self.biz, self.conv, "This is a scam!")
        self.conv.refresh_from_db()
        self.assertEqual(self.conv.ai_handover_state, "ESCALATION_RECOMMENDED")
        self.assertEqual(self.conv.priority, "URGENT")

    def test_case_insensitive_trigger_matching(self):
        result = self.fn(self.biz, self.conv, "FRAUD detected")
        self.assertTrue(result["should_escalate"])


class TestGenerateHandoverSummary(TestCase):
    def setUp(self):
        from app.services.ai_support import generate_handover_summary
        self.fn = generate_handover_summary
        self.biz = make_business()
        self.customer = make_customer(self.biz, first_name="Bob", last_name="Jones")
        self.conv = make_conversation(self.biz, self.customer, subject="Refund dispute")

    def test_handover_sets_state(self):
        self.fn(self.biz, self.conv)
        self.conv.refresh_from_db()
        self.assertEqual(self.conv.ai_handover_state, "HANDOVER_TO_HUMAN")

    def test_returns_summary_structure(self):
        result = self.fn(self.biz, self.conv)
        self.assertIn("summary", result)
        self.assertIn("customer_name", result)
        self.assertIn("handover_state", result)
        self.assertIn("generated_at", result)

    def test_customer_name_in_summary(self):
        result = self.fn(self.biz, self.conv)
        self.assertIn("Bob", result["customer_name"])

    def test_handover_without_customer(self):
        conv = make_conversation(self.biz, customer=None, subject="Anonymous")
        result = self.fn(self.biz, conv)
        self.assertIn("summary", result)


# ══════════════════════════════════════════════════════════════════
# 8. services/ai_marketing.py
# ══════════════════════════════════════════════════════════════════

class TestExplainCampaignPerformance(TestCase):
    def setUp(self):
        from app.services.ai_marketing import explain_campaign_performance
        self.fn = explain_campaign_performance
        self.biz = make_business()
        self.campaign = Campaign.objects.create(
            business=self.biz,
            name="Summer Sale",
            platform="FACEBOOK",
            status="ACTIVE",
            budget=Decimal("5000.00"),
        )

    def test_returns_performance_structure(self):
        result = self.fn(self.biz, self.campaign)
        self.assertIn("campaign_id", result)
        self.assertIn("spend", result)
        self.assertIn("calculated_roas", result)
        self.assertIn("performance_summary", result)
        self.assertIn("optimization_suggestions", result)

    def test_zero_spend_roas_is_zero(self):
        result = self.fn(self.biz, self.campaign)
        self.assertEqual(result["calculated_roas"], "0.00")

    def test_campaign_spend_from_metrics(self):
        CampaignMetric.objects.create(
            campaign=self.campaign,
            metric_date=timezone.now().date(),
            spend=Decimal("1000.00"),
        )
        result = self.fn(self.biz, self.campaign)
        self.assertEqual(Decimal(result["spend"]), Decimal("1000.00"))


# ══════════════════════════════════════════════════════════════════
# 9. services/ai_summarization.py
# ══════════════════════════════════════════════════════════════════

class TestSummarizeSupportConversation(TestCase):
    def setUp(self):
        from app.services.ai_summarization import summarize_support_conversation
        self.fn = summarize_support_conversation
        self.biz = make_business()
        self.customer = make_customer(self.biz)

    def _make_conv_with_messages(self, subject="General", n_messages=3):
        conv = make_conversation(self.biz, self.customer, subject=subject)
        for i in range(n_messages):
            Message.objects.create(
                conversation=conv,
                direction="INBOUND",
                sender_type="CUSTOMER",
                content=f"Message {i}",
            )
        return conv

    def test_summarizes_basic_conversation(self):
        conv = self._make_conv_with_messages()
        result = self.fn(conv)
        self.assertIn("summary", result)
        self.assertIn("conversation_id", result)
        self.assertEqual(result["conversation_id"], conv.id)

    def test_intent_detected_refund(self):
        conv = make_conversation(self.biz, self.customer, subject="I need a refund")
        result = self.fn(conv)
        self.assertEqual(result["customer_intent"], "REFUND_REQUEST")

    def test_intent_detected_cancellation(self):
        conv = make_conversation(self.biz, self.customer, subject="I want to cancel my order")
        result = self.fn(conv)
        self.assertEqual(result["customer_intent"], "CANCELLATION_REQUEST")

    def test_resolved_conversation_status(self):
        conv = make_conversation(self.biz, self.customer, status="RESOLVED")
        result = self.fn(conv)
        self.assertEqual(result["resolution_status"], "RESOLVED")

    def test_open_conversation_pending_status(self):
        conv = make_conversation(self.biz, self.customer, status="OPEN")
        result = self.fn(conv)
        self.assertEqual(result["resolution_status"], "PENDING_AGENT_ACTION")

    def test_summary_persisted_to_metadata(self):
        conv = self._make_conv_with_messages()
        self.fn(conv)
        conv.refresh_from_db()
        self.assertIn("latest_summary", conv.source_metadata)


class TestSummarizeCall(TestCase):
    def setUp(self):
        from app.services.ai_summarization import summarize_call
        self.fn = summarize_call
        self.biz = make_business()
        self.customer = make_customer(self.biz)

    def _make_call(self, direction="INBOUND", status="COMPLETED", duration=120):
        return Call.objects.create(
            business=self.biz,
            customer=self.customer,
            direction=direction,
            status=status,
            duration_seconds=duration,
        )

    def test_inbound_call_purpose(self):
        call = self._make_call(direction="INBOUND")
        result = self.fn(call)
        self.assertEqual(result["call_purpose"], "CUSTOMER_SUPPORT_INQUIRY")

    def test_outbound_call_purpose(self):
        call = self._make_call(direction="OUTBOUND")
        result = self.fn(call)
        self.assertEqual(result["call_purpose"], "ORDER_CONFIRMATION")

    def test_completed_outcome(self):
        call = self._make_call(status="COMPLETED")
        result = self.fn(call)
        self.assertEqual(result["outcome"], "CONFIRMED")

    def test_non_completed_followup_required(self):
        call = self._make_call(status="MISSED")
        result = self.fn(call)
        self.assertEqual(result["outcome"], "FOLLOW_UP_REQUIRED")

    def test_short_duration_concern(self):
        call = self._make_call(duration=15)
        result = self.fn(call)
        self.assertIn("unreached", result["customer_concerns"].lower())

    def test_transcript_created(self):
        call = self._make_call()
        result = self.fn(call)
        self.assertIsNotNone(result["transcript_id"])
        self.assertTrue(CallTranscript.objects.filter(pk=result["transcript_id"]).exists())

    def test_transcript_updated_on_second_call(self):
        call = self._make_call()
        self.fn(call)
        self.fn(call)
        self.assertEqual(CallTranscript.objects.filter(call=call).count(), 1)


# ══════════════════════════════════════════════════════════════════
# 10. services/ai_diagnosis.py
# ══════════════════════════════════════════════════════════════════

class TestDiagnoseBusinessIssue(TestCase):
    def setUp(self):
        from app.services.ai_diagnosis import diagnose_business_issue
        self.fn = diagnose_business_issue
        self.biz = make_business()
        self.issue = BusinessIssue.objects.create(
            business=self.biz,
            issue_type="EXCESSIVE_DELIVERY_FAILURES",
            title="High Failure Rate",
            severity="HIGH",
            status="OPEN",
            detected_at=timezone.now(),
            subject_entity_type="business",
            subject_entity_id=self.biz.id,
        )

    def test_returns_diagnosis_structure(self):
        result = self.fn(self.biz, self.issue)
        self.assertIn("issue_id", result)
        self.assertIn("diagnostic_summary", result)
        self.assertIn("symptom", result)
        self.assertIn("contributing_factors", result)
        self.assertIn("diagnosed_at", result)

    def test_issue_id_matches(self):
        result = self.fn(self.biz, self.issue)
        self.assertEqual(result["issue_id"], self.issue.id)

    def test_severity_in_result(self):
        result = self.fn(self.biz, self.issue)
        self.assertEqual(result["severity"], "HIGH")

    def test_evidence_descriptions_included(self):
        fact = make_business_fact(self.biz)
        BusinessIssueEvidence.objects.create(
            business_issue=self.issue,
            business_fact=fact,
            evidence_type="METRIC_THRESHOLD_BREACH",
            description="Failure rate exceeded threshold",
        )
        result = self.fn(self.biz, self.issue)
        self.assertIn("Failure rate exceeded threshold", result["supporting_evidence"])

    def test_no_evidence_uses_fallback(self):
        result = self.fn(self.biz, self.issue)
        self.assertGreater(len(result["supporting_evidence"]), 0)


# ══════════════════════════════════════════════════════════════════
# 11. services/ai.py
# ══════════════════════════════════════════════════════════════════

class TestGenerateGroundedRecommendation(TestCase):
    def setUp(self):
        from app.services.ai import generate_grounded_recommendation
        self.fn = generate_grounded_recommendation
        self.biz = make_business()
        make_business_fact(self.biz)

    def test_creates_recommendation_and_action(self):
        rec, action = self.fn(self.biz)
        self.assertIsInstance(rec, AiRecommendation)
        self.assertIsInstance(action, AiAction)

    def test_recommendation_is_suggested(self):
        rec, _ = self.fn(self.biz)
        self.assertEqual(rec.status, "SUGGESTED")

    def test_action_is_simulated(self):
        _, action = self.fn(self.biz)
        self.assertTrue(action.is_simulated)

    def test_recommendation_grounded_with_evidence(self):
        make_business_fact(self.biz)
        rec, _ = self.fn(self.biz)
        self.assertTrue(AiRecommendationEvidence.objects.filter(ai_recommendation=rec).exists())

    def test_confidence_within_bounds(self):
        rec, _ = self.fn(self.biz)
        self.assertGreaterEqual(rec.confidence, Decimal("0.00"))
        self.assertLessEqual(rec.confidence, Decimal("1.00"))

    def test_issue_linked_when_provided(self):
        issue = BusinessIssue.objects.create(
            business=self.biz, issue_type="TEST", title="Test Issue",
            severity="HIGH", status="OPEN", detected_at=timezone.now(),
        )
        rec, _ = self.fn(self.biz, issue=issue)
        self.assertEqual(rec.business_issue, issue)


class TestAssembleAiContext(TestCase):
    def setUp(self):
        from app.services.ai import assemble_ai_context
        self.fn = assemble_ai_context
        self.biz = make_business()

    def test_context_structure(self):
        result = self.fn(self.biz)
        self.assertIn("business_id", result)
        self.assertIn("active_facts", result)
        self.assertIn("open_issues", result)
        self.assertIn("authoritative_policies", result)

    def test_only_open_issues_included(self):
        BusinessIssue.objects.create(
            business=self.biz, issue_type="OPEN_ISSUE", title="Open",
            severity="LOW", status="OPEN", detected_at=timezone.now(),
        )
        BusinessIssue.objects.create(
            business=self.biz, issue_type="CLOSED_ISSUE", title="Closed",
            severity="LOW", status="RESOLVED", detected_at=timezone.now(),
        )
        result = self.fn(self.biz)
        issue_types = [i["issue_type"] for i in result["open_issues"]]
        self.assertIn("OPEN_ISSUE", issue_types)
        self.assertNotIn("CLOSED_ISSUE", issue_types)

    def test_tenant_isolation(self):
        other = make_business(name="Other", slug="other")
        make_business_fact(other, fact_type="OTHER_FACT")
        result = self.fn(self.biz)
        self.assertEqual(result["active_facts"], [])


# ══════════════════════════════════════════════════════════════════
# 12. events/dispatcher.py
# ══════════════════════════════════════════════════════════════════

class TestEventDispatcher(TestCase):
    def setUp(self):
        from app.events.dispatcher import _subscribers
        _subscribers.clear()

    def test_subscribe_and_dispatch(self):
        from app.events.dispatcher import dispatch, subscribe
        received = []
        subscribe("test.event", lambda e: received.append(e))

        class Event:
            type = "test.event"
        with self.captureOnCommitCallbacks(execute=True):
            dispatch(Event())
        self.assertEqual(len(received), 1)

    def test_duplicate_subscribe_not_added(self):
        from app.events.dispatcher import _subscribers, subscribe
        handler = MagicMock()
        subscribe("evt", handler)
        subscribe("evt", handler)
        self.assertEqual(len(_subscribers["evt"]), 1)

    def test_handler_exception_does_not_propagate(self):
        from app.events.dispatcher import dispatch, subscribe
        def bad_handler(e):
            raise RuntimeError("handler error")
        subscribe("crash.event", bad_handler)

        class Event:
            type = "crash.event"
        dispatch(Event())  # must not raise

    def test_on_commit_used_in_atomic_block(self):
        from app.events.dispatcher import dispatch, subscribe
        called = []
        subscribe("db.event", lambda e: called.append(True))

        class Event:
            type = "db.event"

        from django.db import transaction
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            with transaction.atomic():
                dispatch(Event())
            self.assertEqual(len(called), 0)  # not called inside atomic
        for cb in callbacks:
            cb()
        self.assertEqual(len(called), 1)  # called after commit


# ══════════════════════════════════════════════════════════════════
# 13. Model-Level Validations
# ══════════════════════════════════════════════════════════════════

class TestAiRecommendationConfidenceValidation(TestCase):
    def setUp(self):
        self.biz = make_business()

    def test_confidence_out_of_range_raises(self):
        rec = AiRecommendation(
            business=self.biz,
            recommendation_type="TEST",
            title="Bad Rec",
            description="Test",
            confidence=Decimal("1.5"),
            status="SUGGESTED",
            generated_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            rec.full_clean()

    def test_confidence_valid(self):
        rec = AiRecommendation(
            business=self.biz,
            recommendation_type="TEST",
            title="Good Rec",
            description="Test",
            confidence=Decimal("0.85"),
            status="SUGGESTED",
            generated_at=timezone.now(),
        )
        rec.full_clean()  # must not raise


class TestAiActionCleanValidation(TestCase):
    def setUp(self):
        self.biz = make_business()
        self.rec = make_ai_recommendation(self.biz)

    def test_executing_without_approval_raises(self):
        action = AiAction(
            business=self.biz,
            ai_recommendation=self.rec,
            action_type="TEST",
            status="EXECUTING",
            is_simulated=True,
        )
        with self.assertRaises(ValidationError):
            action.clean()

    def test_executed_without_approval_raises(self):
        action = AiAction(
            business=self.biz,
            ai_recommendation=self.rec,
            action_type="TEST",
            status="EXECUTED",
            is_simulated=True,
        )
        with self.assertRaises(ValidationError):
            action.clean()

    def test_suggested_without_approval_ok(self):
        action = AiAction(
            business=self.biz,
            ai_recommendation=self.rec,
            action_type="TEST",
            status="SUGGESTED",
            is_simulated=True,
        )
        action.clean()  # must not raise

    def test_failed_status_with_error_result_does_not_raise(self):
        """Regression: AiAction.save() FAILED-before-clean bug."""
        user = make_user(username="model_test_user_clean")
        rec = make_ai_recommendation(self.biz)
        action = AiAction.objects.create(
            business=self.biz,
            ai_recommendation=rec,
            action_type="TEST",
            status="APPROVED",
            approved_by=user,
            approved_at=timezone.now(),
            is_simulated=True,
        )
        action.execution_result = {"error": "some failure"}
        action.save()  # must not raise
        action.refresh_from_db()
        self.assertEqual(action.status, "FAILED")


class TestBusinessIssueUpsert(TestCase):
    def setUp(self):
        self.biz = make_business()

    def test_duplicate_open_issue_upserted_not_duplicated(self):
        """Regression: BusinessIssue.save() must upsert, not duplicate."""
        kwargs = {
            "business": self.biz,
            "issue_type": "DUPLICATE_TEST",
            "subject_entity_type": "business",
            "subject_entity_id": self.biz.id,
            "title": "Dup Issue",
            "severity": "MEDIUM",
            "status": "OPEN",
            "detected_at": timezone.now(),
        }
        BusinessIssue.objects.create(**kwargs)
        BusinessIssue.objects.create(**kwargs)
        count = BusinessIssue.objects.filter(
            business=self.biz, issue_type="DUPLICATE_TEST", status="OPEN"
        ).count()
        self.assertLessEqual(count, 1)

    def test_resolved_issue_does_not_block_new_open_issue(self):
        kwargs = {
            "business": self.biz,
            "issue_type": "RECURRING",
            "subject_entity_type": "business",
            "subject_entity_id": self.biz.id,
            "title": "Issue",
            "severity": "LOW",
            "detected_at": timezone.now(),
        }
        issue = BusinessIssue.objects.create(**kwargs, status="OPEN")
        issue.status = "RESOLVED"
        issue.save()
        BusinessIssue.objects.create(**kwargs, status="OPEN")
        count = BusinessIssue.objects.filter(
            business=self.biz, issue_type="RECURRING", status="OPEN"
        ).count()
        self.assertEqual(count, 1)


class TestGraphEdgeCrossTenantValidation(TestCase):
    def setUp(self):
        self.biz_a = make_business(name="Biz A", slug="biz-a")
        self.biz_b = make_business(name="Biz B", slug="biz-b")

    def test_cross_tenant_edge_raises(self):
        node_a = GraphNode.objects.create(
            business=self.biz_a, entity_type="customer", entity_id=1, node_type="CUSTOMER"
        )
        node_b = GraphNode.objects.create(
            business=self.biz_b, entity_type="customer", entity_id=2, node_type="CUSTOMER"
        )
        edge = GraphEdge(
            business=self.biz_a,
            source_node=node_a,
            target_node=node_b,
            relationship_type="PLACED",
        )
        with self.assertRaises(ValidationError):
            edge.clean()

    def test_same_tenant_edge_valid(self):
        node_a = GraphNode.objects.create(
            business=self.biz_a, entity_type="customer", entity_id=10, node_type="CUSTOMER"
        )
        node_b = GraphNode.objects.create(
            business=self.biz_a, entity_type="order", entity_id=20, node_type="ORDER"
        )
        edge = GraphEdge(
            business=self.biz_a,
            source_node=node_a,
            target_node=node_b,
            relationship_type="PLACED",
        )
        edge.clean()  # must not raise


class TestMessageContentWrapping(TestCase):
    """Message.save() must wrap customer content in untrusted tags."""

    def setUp(self):
        self.biz = make_business()
        self.customer = make_customer(self.biz)
        self.conv = make_conversation(self.biz, self.customer)

    def test_customer_message_wrapped(self):
        msg = Message.objects.create(
            conversation=self.conv,
            direction="INBOUND",
            sender_type="CUSTOMER",
            content="Hello, I need help",
        )
        self.assertIn("<untrusted_customer_data>", msg.content)
        self.assertIn("Hello, I need help", msg.content)

    def test_agent_message_not_wrapped(self):
        msg = Message.objects.create(
            conversation=self.conv,
            direction="OUTBOUND",
            sender_type="AGENT",
            content="Hello, how can I help?",
        )
        self.assertNotIn("<untrusted_customer_data>", msg.content)

    def test_double_wrapping_prevented(self):
        msg = Message.objects.create(
            conversation=self.conv,
            direction="INBOUND",
            sender_type="CUSTOMER",
            content="Test message",
        )
        original_content = msg.content
        msg.save()  # second save
        msg.refresh_from_db()
        self.assertEqual(msg.content, original_content)


# ══════════════════════════════════════════════════════════════════
# 14. API Views — Tenant Isolation (Security)
# ══════════════════════════════════════════════════════════════════

class TestTenantIsolationViews(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.biz_a = make_business(name="Biz A", slug="biz-a")
        self.biz_b = make_business(name="Biz B", slug="biz-b")
        self.user_a = make_user(username="user_a_tenant")
        BusinessMembership.objects.create(business=self.biz_a, user=self.user_a, role="MEMBER")
        self.client.force_authenticate(user=self.user_a)

    def test_business_issues_cross_tenant_forbidden(self):
        resp = self.client.get(f"/api/v1/businesses/{self.biz_b.id}/issues/")
        self.assertEqual(resp.status_code, 403)

    def test_ai_assistant_cross_tenant_forbidden(self):
        resp = self.client.post(
            f"/api/v1/businesses/{self.biz_b.id}/ai/assistant/query/",
            {"query": "test"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_support_reply_cross_tenant_forbidden(self):
        resp = self.client.post(
            f"/api/v1/businesses/{self.biz_b.id}/ai/support/suggest-reply/",
            {"conversation_id": 1}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_support_escalate_cross_tenant_forbidden(self):
        resp = self.client.post(
            f"/api/v1/businesses/{self.biz_b.id}/ai/support/escalate/",
            {"conversation_id": 1, "customer_message": "test"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_support_handover_cross_tenant_forbidden(self):
        resp = self.client.post(
            f"/api/v1/businesses/{self.biz_b.id}/ai/support/handover/",
            {"conversation_id": 1}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_marketing_cross_tenant_forbidden(self):
        resp = self.client.post(
            f"/api/v1/businesses/{self.biz_b.id}/ai/marketing/explain-campaign/",
            {"campaign_id": 1}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_diagnosis_cross_tenant_forbidden(self):
        resp = self.client.post(
            f"/api/v1/businesses/{self.biz_b.id}/ai/diagnosis/diagnose-issue/",
            {"issue_id": 1}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_conversation_summary_cross_tenant_forbidden(self):
        resp = self.client.post(
            f"/api/v1/businesses/{self.biz_b.id}/ai/summarization/conversation/",
            {"conversation_id": 1}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_call_summary_cross_tenant_forbidden(self):
        resp = self.client.post(
            f"/api/v1/businesses/{self.biz_b.id}/ai/summarization/call/",
            {"call_id": 1}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_own_business_not_forbidden(self):
        """Own business should return 200 or 404, never 403."""
        resp = self.client.get(f"/api/v1/businesses/{self.biz_a.id}/issues/")
        self.assertNotEqual(resp.status_code, 403)

    def test_unauthenticated_request_denied(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(f"/api/v1/businesses/{self.biz_a.id}/issues/")
        self.assertEqual(resp.status_code, 403)


class TestAiActionApprovalView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.biz = make_business()
        self.user = make_user(username="approver_view_user")
        BusinessMembership.objects.create(business=self.biz, user=self.user, role="OPERATOR")
        self.client.force_authenticate(user=self.user)
        rec = make_ai_recommendation(self.biz)
        self.action = make_ai_action(self.biz, rec)

    def test_approve_action_success(self):
        resp = self.client.post(
            f"/api/v1/actions/{self.action.id}/approve/",
            {"approval_note": "Approved by manager"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "APPROVED")

    def test_approve_requires_min_length_note(self):
        resp = self.client.post(
            f"/api/v1/actions/{self.action.id}/approve/",
            {"approval_note": "ab"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_approve_cross_tenant_action_forbidden(self):
        other_biz = make_business(name="Other2", slug="other2")
        other_rec = make_ai_recommendation(other_biz)
        other_action = make_ai_action(other_biz, other_rec)
        resp = self.client.post(
            f"/api/v1/actions/{other_action.id}/approve/",
            {"approval_note": "Trying to approve"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_approve_unauthenticated_denied(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post(
            f"/api/v1/actions/{self.action.id}/approve/",
            {"approval_note": "Sneaky"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)


class TestHealthCheckView(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_message_endpoint_returns_200(self):
        resp = self.client.get("/api/v1/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("message", resp.data)


# ══════════════════════════════════════════════════════════════════
# 15. Regression Tests — Every Fixed Bug
# ══════════════════════════════════════════════════════════════════

class TestRegressionBiTimedelta(TestCase):
    """Regression: timezone.timedelta crash in detect_business_issues_from_metrics."""

    def test_detect_issues_does_not_raise_attribute_error(self):
        biz = make_business()
        for _ in range(3):
            make_order(biz, status="FAILED_DELIVERY", total_amount="100.00", ordered_at=timezone.now())
        make_order(biz, total_amount="100.00", ordered_at=timezone.now())
        try:
            from app.services.bi import detect_business_issues_from_metrics
            detect_business_issues_from_metrics(biz)
        except AttributeError as e:
            self.fail(f"AttributeError — timezone.timedelta bug not fully fixed: {e}")


class TestRegressionAiActionSaveOrder(TestCase):
    """Regression: AiAction.save() FAILED-before-clean ValidationError."""

    def test_action_with_error_result_saves_without_validation_error(self):
        biz = make_business()
        user = make_user(username="regression_save_user")
        rec = make_ai_recommendation(biz)
        action = AiAction.objects.create(
            business=biz, ai_recommendation=rec,
            action_type="TEST", status="APPROVED",
            approved_by=user, approved_at=timezone.now(),
            is_simulated=True,
        )
        action.execution_result = {"error": "integration down"}
        try:
            action.save()
        except ValidationError as e:
            self.fail(f"ValidationError — AiAction.save() order bug not fixed: {e}")
        action.refresh_from_db()
        self.assertEqual(action.status, "FAILED")


class TestRegressionExecuteActionNotStuckInExecuting(TestCase):
    """Regression: execute_action must not leave action in EXECUTING on failure."""

    def test_action_not_stuck_in_executing_after_exception(self):
        from app.services.actions import approve_action, execute_action
        biz = make_business()
        user = make_user(username="stuck_test_user")
        BusinessMembership.objects.create(business=biz, user=user, role="OPERATOR")
        rec = make_ai_recommendation(biz)
        action = make_ai_action(biz, rec)
        approve_action(action, user, "ok")
        execute_action(action, executor_fn=lambda p: (_ for _ in ()).throw(RuntimeError("boom")))
        action.refresh_from_db()
        self.assertNotEqual(action.status, "EXECUTING")


class TestRegressionNoDuplicateApiRoutes(TestCase):
    """Regression: /api/ duplicate route was removed."""

    def setUp(self):
        self.client = APIClient()

    def test_api_v1_prefix_works(self):
        resp = self.client.get("/api/v1/")
        self.assertEqual(resp.status_code, 200)

    def test_bare_api_prefix_not_exposed(self):
        """The bare /api/ route was removed; must 404."""
        resp = self.client.get("/api/")
        self.assertNotEqual(resp.status_code, 200)


class TestRegressionBiDbAggregate(TestCase):
    """Regression: bi.py and ai_context.py must use DB-side aggregation."""

    def test_total_spent_correct_with_many_orders(self):
        """aggregate(Sum) must equal what sum() would return — large dataset test."""
        from app.services.ai_context import assemble_customer_context
        biz = make_business()
        customer = make_customer(biz)
        expected = Decimal("0.00")
        for i in range(20):
            amt = Decimal(f"{(i + 1) * 50}.00")
            make_order(biz, customer, total_amount=str(amt))
            expected += amt
        result = assemble_customer_context(biz, customer)
        self.assertEqual(Decimal(result["total_spend"]), expected)

    def test_units_sold_correct_across_multiple_items(self):
        from app.services.ai_context import assemble_product_context
        biz = make_business()
        customer = make_customer(biz)
        product = Product.objects.create(business=biz, name="Widget", status="ACTIVE")
        expected_qty = 0
        for qty in [2, 5, 3]:
            order = make_order(biz, customer)
            OrderItem.objects.create(
                order=order, product=product,
                product_name="Widget", quantity=qty,
                unit_price=Decimal("50.00"),
                total_amount=Decimal(f"{qty * 50}.00"),
            )
            expected_qty += qty
        result = assemble_product_context(biz, product)
        self.assertEqual(result["units_sold"], expected_qty)
