"""Mounting and tenant-access tests for the Business Intelligence and Business Graph HTTP APIs (BI-01, BI-02, BG-02, BG-07)."""

from django.test import SimpleTestCase, TestCase
from django.urls import resolve
from django.utils import timezone

from app import models
from app.tests.bi_graph_helpers import client_for, graph_url, intelligence_url, make_member, make_user

READ_TAILS = (
    ("intelligence", "metrics/"),
    ("intelligence", "facts/"),
    ("intelligence", "issues/"),
    ("graph", "query/"),
    ("graph", "snapshots/"),
)
WRITE_CALLS = (
    ("intelligence", "pipeline/run/", {}),
    ("intelligence", "facts/", {"statement": "Fact", "fact_type": "GENERAL", "rule_key": "rule.access"}),
    ("intelligence", "issues/", {"issue_type": "ACCESS_TEST", "title": "Issue", "rule_key": "rule.access"}),
    ("graph", "rebuild/", {}),
    ("graph", "snapshots/", {"snapshot_type": "BUSINESS"}),
)


def url(module, business_id, tail):
    return (intelligence_url if module == "intelligence" else graph_url)(business_id, tail)


class BiGraphRouteMountTests(SimpleTestCase):
    def test_every_route_is_mounted_under_the_business(self):
        for module, tail, name in (
            ("intelligence", "metrics/", "intelligence-metrics"),
            ("intelligence", "metrics/bi.metric.revenue_net.v1/snapshots/", "intelligence-metric-snapshots"),
            ("intelligence", "facts/", "intelligence-facts"),
            ("intelligence", "facts/5/", "intelligence-fact-detail"),
            ("intelligence", "issues/", "intelligence-issues"),
            ("intelligence", "issues/5/", "intelligence-issue-detail"),
            ("intelligence", "pipeline/run/", "intelligence-pipeline-run"),
            ("graph", "traversal/", "graph-traversal"),
            ("graph", "paths/", "graph-paths"),
            ("graph", "query/", "graph-query"),
            ("graph", "journeys/customer/5/", "graph-customer-journey"),
            ("graph", "journeys/order/5/", "graph-order-journey"),
            ("graph", "journeys/product/5/", "graph-product-journey"),
            ("graph", "journeys/campaign/5/", "graph-campaign-journey"),
            ("graph", "snapshots/", "graph-snapshots"),
            ("graph", "snapshots/5/", "graph-snapshot-detail"),
            ("graph", "rebuild/", "graph-rebuild"),
        ):
            for prefix in ("/api", "/api/v1"):
                with self.subTest(path=f"{prefix}/{module}/{tail}"):
                    match = resolve(f"{prefix}/businesses/7/{module}/{tail}")
                    self.assertEqual(match.url_name, name)
                    self.assertEqual(match.kwargs["business_id"], 7)


class BiGraphAccessTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.business = models.Business.objects.create(name="Scoped", slug="scoped", currency="BDT", created_at=now, updated_at=now)
        self.other = models.Business.objects.create(name="Other", slug="other", currency="BDT", created_at=now, updated_at=now)
        self.other_customer = models.Customer.objects.create(
            business=self.other, first_name="Foreign", last_name="Buyer", display_name="Foreign Buyer", created_at=now, updated_at=now
        )

    def test_any_member_role_can_read(self):
        for role in ("VIEWER", "OPERATOR", "MANAGER", "OWNER"):
            client = client_for(make_member(self.business, role))
            for module, tail in READ_TAILS:
                with self.subTest(role=role, path=f"{module}/{tail}"):
                    self.assertEqual(client.get(url(module, self.business.pk, tail)).status_code, 200)

    def test_only_owner_and_manager_can_write_or_run_pipelines(self):
        for role, allowed in (("VIEWER", False), ("OPERATOR", False), ("MANAGER", True), ("OWNER", True)):
            client = client_for(make_member(self.business, role))
            for module, tail, payload in WRITE_CALLS:
                with self.subTest(role=role, path=f"{module}/{tail}"):
                    response = client.post(url(module, self.business.pk, tail), payload)
                    if allowed:
                        self.assertIn(response.status_code, (200, 201), response.content)
                    else:
                        self.assertEqual(response.status_code, 403)
                        self.assertEqual(response.json()["code"], "FORBIDDEN")

    def test_anonymous_callers_are_rejected_everywhere(self):
        client = client_for()
        for module, tail in READ_TAILS:
            with self.subTest(path=f"{module}/{tail}"):
                self.assertIn(client.get(url(module, self.business.pk, tail)).status_code, (401, 403))
        for module, tail, payload in WRITE_CALLS:
            with self.subTest(path=f"{module}/{tail}"):
                self.assertIn(client.post(url(module, self.business.pk, tail), payload).status_code, (401, 403))

    def test_non_members_and_other_business_members_are_denied_without_leaking_ids(self):
        outsider = make_user()
        foreign_member = make_member(self.other, "OWNER")
        inactive = make_member(self.business, "OWNER", is_active=False)
        for who, user in (("outsider", outsider), ("foreign member", foreign_member), ("inactive member", inactive)):
            client = client_for(user)
            for module, tail in READ_TAILS:
                with self.subTest(who=who, path=f"{module}/{tail}"):
                    response = client.get(url(module, self.business.pk, tail))
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(set(response.json()), {"code", "detail"})
                    self.assertNotIn(str(self.business.pk), response.json()["detail"])
            for module, tail, payload in WRITE_CALLS:
                with self.subTest(who=who, path=f"{module}/{tail}"):
                    self.assertEqual(client.post(url(module, self.business.pk, tail), payload).status_code, 403)

    def test_missing_business_looks_the_same_as_a_foreign_business(self):
        client = client_for(make_member(self.other, "OWNER"))
        foreign = client.get(intelligence_url(self.business.pk, "facts/"))
        missing = client.get(intelligence_url(987654, "facts/"))
        self.assertEqual(foreign.status_code, missing.status_code)
        self.assertEqual(foreign.json(), missing.json())

    def test_superuser_reaches_existing_businesses_only(self):
        client = client_for(make_user(is_superuser=True, is_staff=True))
        self.assertEqual(client.get(intelligence_url(self.business.pk, "facts/")).status_code, 200)
        self.assertEqual(client.get(graph_url(987654, "query/")).status_code, 404)

    def test_foreign_entities_do_not_leak_the_owning_business(self):
        client = client_for(make_member(self.business, "OWNER"))
        foreign = client.get(graph_url(self.business.pk, f"journeys/customer/{self.other_customer.pk}/"))
        missing = client.get(graph_url(self.business.pk, "journeys/customer/987654/"))
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.status_code, missing.status_code)
        self.assertEqual(foreign.json()["code"], "NOT_FOUND")
        self.assertNotIn(str(self.other.pk), foreign.content.decode().replace(str(self.other_customer.pk), ""))

        traversal = client.get(
            graph_url(self.business.pk, f"traversal/?root_entity_type=CUSTOMER&root_entity_id={self.other_customer.pk}")
        )
        self.assertIn(traversal.status_code, (400, 404))
        self.assertNotIn("belongs to business", traversal.content.decode())
