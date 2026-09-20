"""Endpoint matrix for the complete AI Intelligence API surface."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from app.models import (
    AiAction,
    Business,
    BusinessMembership,
    BusinessFact,
    BusinessIssue,
    Call,
    Campaign,
    Conversation,
    Customer,
    Order,
)
from app.services.ai import generate_grounded_recommendation


class AiEndpointMatrixTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        now = timezone.now()
        self.business = Business.objects.create(name="Matrix A", slug="matrix-a")
        self.other = Business.objects.create(name="Matrix B", slug="matrix-b")
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="matrix-user", password="pass1234")
        self.user.business_id = self.business.id  # legacy compatibility path
        self.user.save()
        self.client.force_authenticate(self.user)
        self.customer = Customer.objects.create(business=self.business, display_name="Matrix Customer")
        self.conversation = Conversation.objects.create(
            business=self.business, customer=self.customer, channel="CHAT", started_at=now
        )
        self.order = Order.objects.create(
            business=self.business, customer=self.customer, order_number="M-1", ordered_at=now
        )
        self.campaign = Campaign.objects.create(
            business=self.business, name="Matrix Campaign", platform="META", budget=Decimal("100")
        )
        self.call = Call.objects.create(
            business=self.business, customer=self.customer, direction="INBOUND", status="MISSED"
        )
        self.issue = BusinessIssue.objects.create(
            business=self.business, issue_type="MATRIX", title="Matrix issue", detected_at=now
        )
        BusinessFact.objects.create(
            business=self.business, fact_type="MATRIX", statement="Verified matrix fact", detected_at=now
        )
        self.recommendation, self.action = generate_grounded_recommendation(self.business, self.issue)

    def test_public_health_route(self):
        response = APIClient().get("/api/v1/")
        self.assertEqual(response.status_code, 200)

    def test_persisted_membership_and_role_permissions(self):
        member = get_user_model().objects.create_user(username="matrix-member", password="pass1234")
        BusinessMembership.objects.create(business=self.business, user=member, role="MEMBER")
        client = APIClient()
        client.force_authenticate(member)
        self.assertEqual(
            client.post(f"/api/v1/businesses/{self.business.id}/ai/assistant/query/", {"query": "x"}, format="json").status_code,
            200,
        )
        self.assertEqual(
            client.post(f"/api/v1/actions/{self.action.id}/approve/", {"approval_note": "no"}, format="json").status_code,
            403,
        )
        operator = get_user_model().objects.create_user(username="matrix-operator", password="pass1234")
        BusinessMembership.objects.create(business=self.business, user=operator, role="OPERATOR")
        client.force_authenticate(operator)
        self.assertEqual(
            client.post(f"/api/v1/actions/{self.action.id}/approve/", {"approval_note": "yes"}, format="json").status_code,
            200,
        )

    def test_every_business_route_requires_authentication(self):
        self.client.force_authenticate(user=None)
        routes = [
            f"/api/v1/businesses/{self.business.id}/issues/",
            f"/api/v1/businesses/{self.business.id}/ai/assistant/query/",
            f"/api/v1/businesses/{self.business.id}/ai/support/suggest-reply/",
            f"/api/v1/businesses/{self.business.id}/ai/support/escalate/",
            f"/api/v1/businesses/{self.business.id}/ai/support/handover/",
            f"/api/v1/businesses/{self.business.id}/ai/support/resume/",
            f"/api/v1/businesses/{self.business.id}/ai/marketing/explain-campaign/",
            f"/api/v1/businesses/{self.business.id}/ai/diagnosis/diagnose-issue/",
            f"/api/v1/businesses/{self.business.id}/ai/summarization/conversation/",
            f"/api/v1/businesses/{self.business.id}/ai/summarization/call/",
            f"/api/v1/businesses/{self.business.id}/ai/recommendations/",
            f"/api/v1/businesses/{self.business.id}/ai/actions/",
        ]
        for route in routes:
            response = self.client.get(route)
            self.assertIn(response.status_code, {401, 403}, route)

    def test_every_business_route_rejects_other_tenant(self):
        routes = [
            ("get", f"/api/v1/businesses/{self.other.id}/issues/", {}),
            ("post", f"/api/v1/businesses/{self.other.id}/ai/assistant/query/", {"query": "x"}),
            ("post", f"/api/v1/businesses/{self.other.id}/ai/support/suggest-reply/", {"conversation_id": 1}),
            ("post", f"/api/v1/businesses/{self.other.id}/ai/support/escalate/", {"conversation_id": 1, "customer_message": "x"}),
            ("post", f"/api/v1/businesses/{self.other.id}/ai/support/handover/", {"conversation_id": 1}),
            ("post", f"/api/v1/businesses/{self.other.id}/ai/support/resume/", {"conversation_id": 1}),
            ("post", f"/api/v1/businesses/{self.other.id}/ai/marketing/explain-campaign/", {"campaign_id": 1}),
            ("post", f"/api/v1/businesses/{self.other.id}/ai/diagnosis/diagnose-issue/", {"issue_id": 1}),
            ("post", f"/api/v1/businesses/{self.other.id}/ai/summarization/conversation/", {"conversation_id": 1}),
            ("post", f"/api/v1/businesses/{self.other.id}/ai/summarization/call/", {"call_id": 1}),
            ("get", f"/api/v1/businesses/{self.other.id}/ai/recommendations/", {}),
            ("get", f"/api/v1/businesses/{self.other.id}/ai/actions/", {}),
        ]
        for method, route, payload in routes:
            response = getattr(self.client, method)(route, payload, format="json")
            self.assertEqual(response.status_code, 403, route)

    def test_all_business_routes_accept_valid_or_domain_not_found_requests(self):
        cases = [
            ("get", f"/api/v1/businesses/{self.business.id}/issues/", {}),
            ("post", f"/api/v1/businesses/{self.business.id}/ai/assistant/query/", {"query": "What is known?"}),
            ("post", f"/api/v1/businesses/{self.business.id}/ai/support/suggest-reply/", {"conversation_id": self.conversation.id}),
            ("post", f"/api/v1/businesses/{self.business.id}/ai/support/escalate/", {"conversation_id": self.conversation.id, "customer_message": "hello"}),
            ("post", f"/api/v1/businesses/{self.business.id}/ai/support/handover/", {"conversation_id": self.conversation.id}),
            ("post", f"/api/v1/businesses/{self.business.id}/ai/support/resume/", {"conversation_id": self.conversation.id}),
            ("post", f"/api/v1/businesses/{self.business.id}/ai/marketing/explain-campaign/", {"campaign_id": self.campaign.id}),
            ("post", f"/api/v1/businesses/{self.business.id}/ai/diagnosis/diagnose-issue/", {"issue_id": self.issue.id}),
            ("post", f"/api/v1/businesses/{self.business.id}/ai/summarization/conversation/", {"conversation_id": self.conversation.id}),
            ("post", f"/api/v1/businesses/{self.business.id}/ai/summarization/call/", {"call_id": self.call.id}),
            ("get", f"/api/v1/businesses/{self.business.id}/ai/recommendations/", {}),
            ("get", f"/api/v1/businesses/{self.business.id}/ai/actions/", {}),
        ]
        for method, route, payload in cases:
            response = getattr(self.client, method)(route, payload, format="json")
            self.assertIn(response.status_code, {200, 404}, route)

    def test_action_routes_cover_approval_rejection_execution_and_conflicts(self):
        approve = self.client.post(
            f"/api/v1/actions/{self.action.id}/approve/", {"approval_note": "approved"}, format="json"
        )
        self.assertEqual(approve.status_code, 200)
        repeat = self.client.post(
            f"/api/v1/actions/{self.action.id}/approve/", {"approval_note": "repeat"}, format="json"
        )
        self.assertEqual(repeat.status_code, 200)
        executed = self.client.post(f"/api/v1/actions/{self.action.id}/execute/", {}, format="json")
        self.assertEqual(executed.status_code, 200)
        conflict = self.client.post(f"/api/v1/actions/{self.action.id}/reject/", {"approval_note": "late"}, format="json")
        self.assertEqual(conflict.status_code, 409)

        rejected_rec, rejected_action = generate_grounded_recommendation(self.business, self.issue)
        rejected = self.client.post(
            f"/api/v1/actions/{rejected_action.id}/reject/", {"approval_note": "not now"}, format="json"
        )
        self.assertEqual(rejected.status_code, 200)

    def test_post_endpoints_reject_missing_and_invalid_payloads(self):
        cases = [
            f"/api/v1/businesses/{self.business.id}/ai/assistant/query/",
            f"/api/v1/businesses/{self.business.id}/ai/support/suggest-reply/",
            f"/api/v1/businesses/{self.business.id}/ai/support/escalate/",
            f"/api/v1/businesses/{self.business.id}/ai/support/handover/",
            f"/api/v1/businesses/{self.business.id}/ai/support/resume/",
            f"/api/v1/businesses/{self.business.id}/ai/marketing/explain-campaign/",
            f"/api/v1/businesses/{self.business.id}/ai/diagnosis/diagnose-issue/",
            f"/api/v1/businesses/{self.business.id}/ai/summarization/conversation/",
            f"/api/v1/businesses/{self.business.id}/ai/summarization/call/",
        ]
        for route in cases:
            response = self.client.post(route, {}, format="json")
            self.assertEqual(response.status_code, 400, route)
        self.assertEqual(self.client.post("/api/v1/actions/999999/approve/", {}, format="json").status_code, 404)
        self.assertEqual(self.client.post("/api/v1/actions/999999/reject/", {}, format="json").status_code, 404)
        self.assertEqual(self.client.post("/api/v1/actions/999999/execute/", {}, format="json").status_code, 404)

    def test_method_not_allowed_matrix(self):
        self.assertEqual(self.client.get(f"/api/v1/businesses/{self.business.id}/ai/assistant/query/").status_code, 405)
        self.assertEqual(self.client.post(f"/api/v1/businesses/{self.business.id}/ai/actions/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.post(f"/api/v1/businesses/{self.business.id}/ai/recommendations/", {}, format="json").status_code, 405)
