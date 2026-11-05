"""Regressions for the second review of the AI and memory branch."""

import datetime
from decimal import Decimal
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from app.models import (
    AiAction,
    AiRecommendation,
    Business,
    BusinessFact,
    BusinessMembership,
    Call,
    CallTranscript,
    Campaign,
    Conversation,
    Customer,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeEmbedding,
    KnowledgeSource,
    Order,
    Payment,
    Refund,
)
from app.services.actions import execute_action
from app.services.ai_marketing import explain_campaign_performance
from app.services.ai_summarization import summarize_call
from app.services.bi import compute_daily_business_metrics, detect_business_issues_from_metrics
from app.services.domain_memory import (
    ReturnRefundPolicyData,
    set_business_policy,
    set_return_refund_policy,
    set_support_knowledge,
)
from app.services.hybrid_retrieval import vector_search


class MemoryAndMetricRegressionTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="Review", slug="review", timezone="UTC")
        self.customer = Customer.objects.create(business=self.business, display_name="Customer")
        self.now = timezone.now()

    def test_support_endpoint_uses_active_structured_policies(self):
        set_business_policy(self.business, "REFUND", "Refund rules", "ACTIVE_POLICY_SENTINEL")
        retired = set_business_policy(self.business, "REFUND", "Retired rules", "RETIRED_POLICY_SENTINEL")
        retired.is_active = False
        retired.save(update_fields=["is_active"])
        set_return_refund_policy(self.business, ReturnRefundPolicyData(
            return_window_days=11, eligible_conditions=["sealed"], non_returnable_conditions=["opened"],
            refund_methods=["bank"], replacement_allowed=False, cancellation_cutoff_hours=3,
        ))
        for index in range(12):
            set_support_knowledge(self.business, "SUPPORT", f"Question {index}", "General support answer")
        other = Business.objects.create(name="Other", slug="other")
        set_business_policy(other, "REFUND", "Other rules", "OTHER_POLICY_SENTINEL")
        conversation = Conversation.objects.create(
            business=self.business, customer=self.customer, channel="CHAT", started_at=self.now,
        )
        user = get_user_model().objects.create_user(username="policy-reader")
        BusinessMembership.objects.create(business=self.business, user=user, role="MEMBER")
        client = APIClient()
        client.force_authenticate(user)

        with patch.object(Business, "execute_llm_with_timeout", return_value={"content": "Draft reply"}) as gateway:
            response = client.post(
                f"/api/v1/businesses/{self.business.id}/ai/support/suggest-reply/",
                {"conversation_id": conversation.id, "intent": "refund_inquiry"}, format="json",
            )

        self.assertEqual(response.status_code, 200)
        prompt = gateway.call_args.kwargs["prompt"]
        self.assertIn("ACTIVE_POLICY_SENTINEL", prompt)
        self.assertIn('"return_window_days": 11', prompt)
        self.assertIn('"refund_methods": ["bank"]', prompt)
        self.assertNotIn("RETIRED_POLICY_SENTINEL", prompt)
        self.assertNotIn("OTHER_POLICY_SENTINEL", prompt)
        self.assertIn("Refund rules", response.data["applied_policies"])

    def test_completed_partial_refunds_reduce_daily_and_campaign_revenue(self):
        order = Order.objects.create(
            business=self.business, customer=self.customer, total_amount=100, status="DELIVERED",
            ordered_at=self.now, source_metadata={"utm_campaign": "review-campaign"},
        )
        payment = Payment.objects.create(business=self.business, order=order, amount=100, status="COMPLETED")
        Refund.objects.create(payment=payment, order=order, amount=15, status="COMPLETED", refunded_at=self.now)
        # Some providers only supply the payment-to-order link.
        Refund.objects.create(payment=payment, amount=5, status="COMPLETED", refunded_at=self.now)
        Refund.objects.create(payment=payment, order=order, amount=30, status="PENDING")
        other = Business.objects.create(name="Other", slug="other")
        other_order = Order.objects.create(business=other, total_amount=500, ordered_at=self.now)
        other_payment = Payment.objects.create(business=other, order=other_order, amount=500)
        Refund.objects.create(payment=other_payment, order=other_order, amount=500, status="COMPLETED")

        daily = compute_daily_business_metrics(self.business, self.now.date())
        self.assertEqual(daily["refunds"], Decimal(20))
        self.assertEqual(daily["net_revenue"], Decimal(80))
        campaign = Campaign.objects.create(business=self.business, name="review-campaign", platform="META")
        explanation = explain_campaign_performance(self.business, campaign)
        self.assertEqual(Decimal(explanation["net_revenue"]), Decimal(80))

    def test_refunds_follow_the_original_order_date_cohort(self):
        yesterday = self.now - datetime.timedelta(days=1)
        order = Order.objects.create(business=self.business, total_amount=100, ordered_at=yesterday)
        payment = Payment.objects.create(business=self.business, order=order, amount=100)
        Refund.objects.create(payment=payment, order=order, amount=20, status="COMPLETED", refunded_at=self.now)
        self.assertEqual(compute_daily_business_metrics(self.business, yesterday.date())["net_revenue"], Decimal(80))
        self.assertEqual(compute_daily_business_metrics(self.business, self.now.date())["refunds"], Decimal(0))

    def test_daily_failure_facts_keep_each_period_and_refresh_recalculations(self):
        previous = self.now - datetime.timedelta(days=1)
        for when, failures in ((previous, 1), (self.now, 5)):
            for index in range(5):
                Order.objects.create(
                    business=self.business, total_amount=100, ordered_at=when,
                    status="FAILED_DELIVERY" if index < failures else "DELIVERED",
                )
            detect_business_issues_from_metrics(self.business, when.date())

        facts = BusinessFact.all_objects.filter(business=self.business, fact_type="HIGH_DELIVERY_FAILURE_RATE")
        self.assertEqual(facts.count(), 2)
        older = facts.get(statement__contains=previous.date().isoformat())
        current = facts.get(statement__contains=self.now.date().isoformat())
        self.assertEqual(older.value, Decimal("0.2"))
        self.assertEqual(current.value, Decimal(1))
        Order.objects.create(business=self.business, total_amount=100, ordered_at=self.now, status="DELIVERED")
        issues = detect_business_issues_from_metrics(self.business, self.now.date())
        current.refresh_from_db()
        older.refresh_from_db()
        self.assertEqual(current.value, Decimal("0.833333"))
        self.assertEqual(older.value, Decimal("0.2"))
        self.assertEqual(facts.count(), 2)
        self.assertIn("83.3%", issues[0].description)
        latest_evidence = issues[0].businessissueevidence_set.order_by("-id").first()
        self.assertEqual(latest_evidence.business_fact_id, current.id)
        self.assertEqual(latest_evidence.metric_snapshot.metadata["failure_rate"], "0.8333")

    def test_completed_call_without_transcript_has_unknown_outcome(self):
        call = Call.objects.create(business=self.business, direction="OUTBOUND", status="COMPLETED", duration_seconds=60)
        result = summarize_call(call)
        self.assertEqual(result["outcome"], "UNKNOWN")
        self.assertEqual(result["call_purpose"], "UNKNOWN")
        self.assertIsNone(result["transcript_id"])
        self.assertFalse(CallTranscript.objects.filter(call=call).exists())

    def test_legacy_generated_placeholder_is_not_treated_as_a_transcript(self):
        call = Call.objects.create(business=self.business, direction="OUTBOUND", status="COMPLETED")
        CallTranscript.objects.create(
            call=call, transcript=f"Call transcript for OUTBOUND call {call.id}", provider="BIZORA_AUDIO_AI",
        )
        self.assertEqual(summarize_call(call)["outcome"], "UNKNOWN")

    def test_new_daily_calculation_retires_the_old_unscoped_fact(self):
        legacy = BusinessFact.objects.create(
            business=self.business, fact_type="HIGH_DELIVERY_FAILURE_RATE", subject_entity_type="business",
            subject_entity_id=self.business.id, statement="Old failure rate", value=Decimal("0.2"), detected_at=self.now,
        )
        Order.objects.create(business=self.business, ordered_at=self.now, status="FAILED_DELIVERY")
        detect_business_issues_from_metrics(self.business, self.now.date())
        legacy.refresh_from_db()
        self.assertEqual(legacy.status, "INVALIDATED")
        self.assertFalse(BusinessFact.objects.filter(pk=legacy.pk).exists())

    def test_corrected_daily_metrics_invalidate_a_no_longer_true_fact(self):
        order = Order.objects.create(business=self.business, ordered_at=self.now, status="FAILED_DELIVERY")
        detect_business_issues_from_metrics(self.business, self.now.date())
        fact = BusinessFact.objects.get(business=self.business, fact_type="HIGH_DELIVERY_FAILURE_RATE")
        order.status = "DELIVERED"
        order.save(update_fields=["status"])
        self.assertEqual(detect_business_issues_from_metrics(self.business, self.now.date()), [])
        fact.refresh_from_db()
        self.assertEqual(fact.status, "INVALIDATED")
        self.assertFalse(BusinessFact.objects.filter(pk=fact.pk).exists())

    def test_call_completion_or_keyword_does_not_prove_order_outcome(self):
        call = Call.objects.create(business=self.business, direction="OUTBOUND", status="COMPLETED")
        transcript = CallTranscript.objects.create(call=call, transcript="Please do not confirm my order.", provider="ASR")
        result = summarize_call(call)
        self.assertEqual(result["outcome"], "FOLLOW_UP_REQUIRED")
        transcript.refresh_from_db()
        self.assertEqual(transcript.transcript, "Please do not confirm my order.")
        self.assertEqual(transcript.provider, "ASR")

    @skipUnless(connection.vendor == "postgresql", "requires PostgreSQL pgvector")
    def test_postgres_retrieves_metadata_without_a_current_flag(self):
        source = KnowledgeSource.objects.create(business=self.business, name="Rules", source_type="POLICY_FILE")
        document = KnowledgeDocument.objects.create(business=self.business, knowledge_source=source, title="Rules", content="Rules")
        expected = []
        for index, metadata in enumerate((None, {}, {"category": "DELIVERY"}, {"is_current": True}, {"is_current": False})):
            chunk = KnowledgeChunk.objects.create(
                business=self.business, knowledge_document=document, chunk_index=index, content="Rules", metadata=metadata,
            )
            KnowledgeEmbedding.objects.create(
                business=self.business, knowledge_chunk=chunk, model="test-model-4d", dimensions=4, embedding=[1, 0, 0, 0],
            )
            if metadata is None or metadata.get("is_current") is not False:
                expected.append(chunk.id)

        results = vector_search(self.business, [1, 0, 0, 0], top_k=10, model_name="test-model-4d")
        self.assertCountEqual([item.chunk_id for item in results], expected)


class ExecutorTransactionRegressionTests(TransactionTestCase):
    def test_default_simulated_flag_does_not_allow_executor_inside_a_transaction(self):
        business = Business.objects.create(name="Executor", slug="executor")
        recommendation = AiRecommendation.objects.create(
            business=business, recommendation_type="REVIEW", title="Review", description="Review", generated_at=timezone.now(),
        )
        action = AiAction.objects.create(
            business=business, ai_recommendation=recommendation, action_type="REVIEW",
            status="APPROVED", approved_at=timezone.now(),
        )
        calls = []
        with transaction.atomic(), self.assertRaises(ValidationError):
            execute_action(action, executor_fn=lambda payload: calls.append(payload) or {"status": "success"})
        action.refresh_from_db()
        self.assertEqual(action.status, "APPROVED")
        self.assertEqual(calls, [])
