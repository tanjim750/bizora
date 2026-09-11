import unittest
from decimal import Decimal
import pytz
import networkx as nx
from django.test import TestCase, TransactionTestCase
from django.db import transaction, IntegrityError
from django.utils import timezone
from app.events.dispatcher import subscribe, dispatch
from app.models import (
    Business,
    Order,
    BusinessFact,
    BusinessIssue,
    AiRecommendation,
    AiRecommendationEvidence,
    AiAction,
    VectorField,
)


class EventMock:
    def __init__(self, name, payload=None):
        self.name = name
        self.payload = payload or {}


class P1RegressionTests(TestCase):
    """
    Automated regression tests asserting correct/reliable behavior for P1 issues.
    Running these against the current unfixed code demonstrates reproduction of the bugs.
    """

    def test_cor_001_event_dispatcher_fires_before_transaction_commit(self):
        """
        COR-001: Event dispatcher currently dispatches synchronously inside active transaction blocks
        instead of deferring to transaction.on_commit(). If the transaction rolls back, the event has already fired.
        Expected failure: AssertionError: Event handler ran despite transaction rollback
        """
        handler_executed = []

        def test_handler(event):
            handler_executed.append(event.payload)

        subscribe("test.transaction.event", test_handler)

        try:
            with transaction.atomic():
                # Dispatched inside uncommitted transaction
                dispatch(EventMock("test.transaction.event", {"order_id": 999}))
                # Simulate transaction rollback
                raise RuntimeError("Simulated database failure during checkout")
        except RuntimeError:
            pass

        # Desired behavior: Handler should NOT have run because the transaction rolled back.
        # Defect: Handler ran synchronously before commit!
        self.assertEqual(
            len(handler_executed),
            0,
            "COR-001 Defect: Event handler executed immediately inside uncommitted transaction that rolled back!"
        )

    def test_cor_002_event_dispatcher_aborts_subsequent_handlers_on_exception(self):
        """
        COR-002: A failing subscriber aborts the dispatcher loop, preventing remaining subscribers from executing.
        Expected failure: AssertionError: Second subscriber was not executed after first subscriber raised exception
        """
        execution_order = []

        def failing_handler(event):
            execution_order.append("failing")
            raise ValueError("Subscriber crash")

        def successful_handler(event):
            execution_order.append("successful")

        subscribe("test.crash.event", failing_handler)
        subscribe("test.crash.event", successful_handler)

        with self.captureOnCommitCallbacks(execute=True):
            dispatch(EventMock("test.crash.event", {"data": 123}))

        # Desired behavior: Dispatcher should isolate subscriber exceptions and execute all handlers.
        # Defect: Failing handler aborted loop before successful handler could run.
        self.assertIn(
            "successful",
            execution_order,
            "COR-002 Defect: Dispatcher crashed on first handler; subsequent subscribers were not executed!"
        )

    def test_cor_003_hand_rolled_vector_field_lacks_conversion_methods(self):
        """
        COR-003: Hand-rolled VectorField stub lacks to_python and get_prep_value conversion methods.
        Expected failure: AssertionError: VectorField has no to_python method
        """
        field = VectorField()
        # In official pgvector.django.VectorField, to_python parses vector strings into lists of floats.
        self.assertTrue(
            hasattr(field, 'to_python') and callable(getattr(field, 'to_python')),
            "COR-003 Defect: VectorField is a stub lacking to_python deserialization"
        )
        result = field.to_python("[0.1, 0.2]")
        self.assertEqual(result, [0.1, 0.2])

    def test_cor_004_net_revenue_formula_includes_refunds(self):
        """
        COR-004: Revenue calculations that do not deduct refunds inflate financial metrics.
        Expected failure: AssertionError: Net revenue (1000.0) includes refunded amount (300.0)
        """
        gross_order_total = Decimal("1000.00")
        refunded_amount = Decimal("300.00")
        
        from app.services.analytics import calculate_net_revenue
        current_calculated_revenue = calculate_net_revenue(gross_order_total, refunded_amount)
        
        # Deterministic BI Net Revenue rule: Gross Total - Refunds
        expected_net_revenue = gross_order_total - refunded_amount
        
        self.assertEqual(
            current_calculated_revenue,
            expected_net_revenue,
            f"COR-004 Defect: Revenue calculation ({current_calculated_revenue}) fails to deduct refunds ({refunded_amount})!"
        )

    def test_cor_005_campaign_attribution_exceeds_order_total(self):
        """
        COR-005: Multi-platform campaign attribution without collision capping exceeds 100% of order value.
        Expected failure: AssertionError: Total attributed revenue exceeds actual order total
        """
        order_total = Decimal("100.00")
        meta_attributed = Decimal("100.00")
        google_attributed = Decimal("100.00")
        
        from app.services.analytics import cap_campaign_attributions
        raw_attributions = {"meta": meta_attributed, "google": google_attributed}
        capped_attributions = cap_campaign_attributions(raw_attributions, order_total)
        total_attributed = sum(capped_attributions.values())

        # Desired invariant: Sum of attributed revenue across platforms <= order total
        self.assertLessEqual(
            total_attributed,
            order_total,
            f"COR-005 Defect: Attributed revenue ({total_attributed}) exceeds order total ({order_total}) due to attribution collision!"
        )

    def test_cor_006_timezone_boundary_shifts_daily_sales(self):
        """
        COR-006: Aggregating orders by UTC date trunc shifts Bangladesh evening orders (UTC+6) into previous day.
        Expected failure: AssertionError: UTC date does not match Dhaka business operational date
        """
        dhaka_tz = pytz.timezone("Asia/Dhaka")
        utc_tz = pytz.UTC
        
        late_night_dhaka = dhaka_tz.localize(timezone.datetime(2026, 9, 12, 2, 30, 0))
        late_night_utc = late_night_dhaka.astimezone(utc_tz)
        from app.services.analytics import to_business_date
        aggregated_date = to_business_date(late_night_utc, "Asia/Dhaka")

        self.assertEqual(
            aggregated_date,
            late_night_dhaka.date(),
            f"COR-006 Defect: Order placed on {late_night_dhaka.date()} in Dhaka is aggregated as {aggregated_date} in UTC!"
        )

    def test_cor_007_duplicate_active_business_issues_allowed(self):
        """
        COR-007: BusinessIssue lacks composite unique constraint on (business, issue_type, subject_entity_type, subject_entity_id),
        allowing duplicate active issues for the exact same problem.
        Expected failure: AssertionError: Database allowed inserting duplicate active BusinessIssue records
        """
        now = timezone.now()
        biz = Business.objects.create(name="Issue Biz", slug="issue-biz", created_at=now, updated_at=now)
        
        # First active issue
        issue1 = BusinessIssue.objects.create(
            business=biz,
            issue_type="HIGH_DELIVERY_FAILURE",
            subject_entity_type="courier",
            subject_entity_id=10,
            title="High delivery failure",
            status="OPEN",
            detected_at=now,
            created_at=now,
            updated_at=now,
        )
        
        # Second active issue for identical entity and type
        issue2 = BusinessIssue.objects.create(
            business=biz,
            issue_type="HIGH_DELIVERY_FAILURE",
            subject_entity_type="courier",
            subject_entity_id=10,
            title="High delivery failure",
            status="OPEN",
            detected_at=now,
            created_at=now,
            updated_at=now,
        )
        
        # Desired invariant: An entity cannot have multiple OPEN issues of the same type simultaneously
        active_count = BusinessIssue.objects.filter(
            business=biz,
            issue_type="HIGH_DELIVERY_FAILURE",
            subject_entity_type="courier",
            subject_entity_id=10,
            status="OPEN"
        ).count()
        
        self.assertEqual(
            active_count,
            1,
            f"COR-007 Defect: Duplicate active BusinessIssue records ({active_count}) exist for the same entity!"
        )

    def test_cor_008_evidence_allows_all_foreign_keys_null(self):
        """
        COR-008: AiRecommendationEvidence allows saving records where every single evidence foreign key is NULL.
        Expected failure: AssertionError: Database allowed ghost evidence with all FKs NULL
        """
        now = timezone.now()
        biz = Business.objects.create(name="Rec Biz", slug="rec-biz", created_at=now, updated_at=now)
        rec = AiRecommendation.objects.create(
            business=biz,
            title="Test Rec",
            description="Desc",
            recommendation_type="CAMPAIGN",
            generated_at=now,
            created_at=now,
            updated_at=now,
        )
        
        # Creating evidence with ALL foreign keys NULL
        evidence = AiRecommendationEvidence.objects.create(
            ai_recommendation=rec,
            evidence_type="UNGROUNDED",
            business_fact=None,
            business_issue=None,
            metric_snapshot=None,
            business_relationship=None,
            graph_node=None,
            graph_edge=None,
            knowledge_chunk=None,
            created_at=now,
        )
        
        # Desired invariant: At least one evidence FK must be non-null
        has_fk = any([
            evidence.business_fact_id,
            evidence.business_issue_id,
            evidence.metric_snapshot_id,
            evidence.business_relationship_id,
            evidence.graph_node_id,
            evidence.graph_edge_id,
            evidence.knowledge_chunk_id,
        ])
        self.assertTrue(
            has_fk,
            "COR-008 Defect: Ghost evidence permitted! AiRecommendationEvidence has all evidence FKs NULL"
        )

    def test_cor_009_stale_and_invalid_facts_retrieved_without_filters(self):
        """
        COR-009: Fact retrieval query without freshness filters retrieves expired and invalidated facts.
        Expected failure: AssertionError: Expired fact was returned in active facts query
        """
        now = timezone.now()
        biz = Business.objects.create(name="Fact Biz", slug="fact-biz", created_at=now, updated_at=now)
        
        # Expired fact from 3 months ago (valid_to is in the past)
        expired_fact = BusinessFact.objects.create(
            business=biz,
            fact_type="SURGE",
            statement="Delivery delay during storm",
            status="VERIFIED",
            valid_from=now - timezone.timedelta(days=90),
            valid_to=now - timezone.timedelta(days=60),
            detected_at=now - timezone.timedelta(days=90),
            created_at=now,
            updated_at=now,
        )
        
        # Naive retrieval query currently in place without freshness filter
        retrieved_facts = BusinessFact.objects.filter(business=biz)
        
        # Desired invariant: AI context retrieval must exclude expired facts
        for fact in retrieved_facts:
            self.assertGreaterEqual(
                fact.valid_to,
                now,
                f"COR-009 Defect: Expired fact '{fact.statement}' (expired at {fact.valid_to}) was retrieved for AI context!"
            )

    def test_cor_010_unhandled_llm_timeout_crashes_worker(self):
        """
        COR-010: LLM client call without timeout and circuit breaker causes unhandled exception.
        Expected failure: AssertionError: LLM client does not provide timeout protection
        """
        import socket
        def mock_hanging_llm_call():
            raise socket.timeout("The read operation timed out after 30 seconds")

        with self.assertRaises(socket.timeout):
            mock_hanging_llm_call()
        
        resilient_service_exists = hasattr(Business, 'execute_llm_with_timeout')
        self.assertTrue(
            resilient_service_exists,
            "COR-010 Defect: No resilient LLM wrapper with timeout/circuit breaker exists in codebase"
        )

    def test_cor_011_silent_execution_failure_missing_failed_status(self):
        """
        COR-011: AiAction has no transition validation to FAILED status when provider returns an error.
        Expected failure: AssertionError: Action status not updated to FAILED on execution error
        """
        now = timezone.now()
        biz = Business.objects.create(name="Action Biz", slug="action-biz", created_at=now, updated_at=now)
        rec = AiRecommendation.objects.create(
            business=biz,
            title="Rec",
            description="Desc",
            recommendation_type="COURIER",
            generated_at=now,
            created_at=now,
            updated_at=now,
        )
        action = AiAction.objects.create(
            business=biz,
            ai_recommendation=rec,
            action_type="REASSIGN_COURIER",
            status="APPROVED",
            approved_at=now,
            created_at=now,
            updated_at=now,
        )
        
        api_error_response = {"error": "External courier provider 503 Service Unavailable"}
        action.execution_result = api_error_response
        action.executed_at = now
        action.save()
        
        self.assertEqual(
            action.status,
            "FAILED",
            f"COR-011 Defect: Action status is '{action.status}' instead of 'FAILED' despite external execution failure!"
        )

    def test_cor_012_digraph_clobbers_parallel_edges(self):
        """
        COR-012: Using networkx.DiGraph instead of MultiDiGraph clobbers parallel relationship edges between identical nodes.
        Expected failure: AssertionError: Edge count is 1 instead of 2 (first edge overwritten)
        """
        from app.services.graph import create_business_graph
        G = create_business_graph()
        G.add_edge("Customer:1", "Order:100", relationship="PLACED", timestamp="2026-09-11 10:00")
        G.add_edge("Customer:1", "Order:100", relationship="PAID_FOR", timestamp="2026-09-11 10:05")
        
        self.assertEqual(
            G.number_of_edges(),
            2,
            f"COR-012 Defect: nx.DiGraph clobbered parallel relationship! Total edges: {G.number_of_edges()}"
        )
