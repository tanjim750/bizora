"""BG-06 and BG-05: malformed input is a 400 `{code, detail}` and large requests are capped, never a 500."""

from datetime import datetime, timezone

from django.test import TestCase

from app import models
from app.business_graph import project_business_graph
from app.business_graph.api import MAX_QUERY_LIMIT, MAX_TRAVERSAL_DEPTH, MAX_TRAVERSAL_NODES
from app.tests.bi_graph_helpers import client_for, graph_url, make_member

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


class GraphInputValidationTests(TestCase):
    def setUp(self):
        self.business = models.Business.objects.create(
            name="Validation shop", slug="validation-shop", currency="BDT", created_at=T0, updated_at=T0)
        common = {"business": self.business, "created_at": T0, "updated_at": T0}
        self.customer = models.Customer.objects.create(first_name="Rina", last_name="Das", display_name="Rina Das", **common)
        self.order = models.Order.objects.create(customer=self.customer, status="PAID", currency="BDT",
                                                  total_amount=10, ordered_at=T0, **common)
        models.BusinessRelationship.objects.create(
            business=self.business, source_entity_type="CUSTOMER", source_entity_id=self.customer.pk,
            relationship_type="PLACED_ORDER", target_entity_type="ORDER", target_entity_id=self.order.pk,
            rule_key="bi.relationship.customer_order.v1", relationship_source="DETERMINISTIC",
            created_at=T0, updated_at=T0)
        project_business_graph(business_id=self.business.pk)
        self.owner = client_for(make_member(self.business, "OWNER"))

    def url(self, tail):
        return graph_url(self.business.pk, tail)

    @property
    def root(self):
        return f"root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}"

    @property
    def pair(self):
        return (f"start_entity_type=CUSTOMER&start_entity_id={self.customer.pk}"
                f"&end_entity_type=ORDER&end_entity_id={self.order.pk}")

    def assert_400(self, response, label):
        self.assertEqual(response.status_code, 400, (label, response.content))
        self.assertEqual(response.json()["code"], "INVALID_DATA", (label, response.content))

    def test_traversal_numbers(self):
        for extra in ("max_depth=abc", "max_depth=2.5", "max_depth=-1", f"max_depth={MAX_TRAVERSAL_DEPTH + 1}",
                      "max_nodes=0", "max_nodes=-3", "max_nodes=x", f"max_nodes={MAX_TRAVERSAL_NODES + 1}"):
            with self.subTest(extra=extra):
                self.assert_400(self.owner.get(self.url(f"traversal/?{self.root}&{extra}")), extra)

    def test_path_search_numbers(self):
        for extra in ("max_depth=abc", "max_depth=0", "max_depth=-2", f"max_depth={MAX_TRAVERSAL_DEPTH + 1}"):
            with self.subTest(extra=extra):
                self.assert_400(self.owner.get(self.url(f"paths/?{self.pair}&{extra}")), extra)
        self.assert_400(self.owner.get(self.url("paths/?start_entity_type=CUSTOMER&start_entity_id=x"
                                                "&end_entity_type=ORDER&end_entity_id=1")), "ids")

    def test_query_numbers(self):
        for extra in ("limit=-5", "limit=0", "limit=abc", f"limit={MAX_QUERY_LIMIT + 1}", "entity_id=abc",
                      "entity_id=0", "entity_id=1.5"):
            with self.subTest(extra=extra):
                self.assert_400(self.owner.get(self.url(f"query/?{extra}")), extra)

    def test_caps_are_inclusive_and_defaults_still_work(self):
        for tail in (f"traversal/?{self.root}&max_depth={MAX_TRAVERSAL_DEPTH}&max_nodes={MAX_TRAVERSAL_NODES}",
                     f"traversal/?{self.root}&max_depth=0", f"traversal/?{self.root}",
                     f"paths/?{self.pair}&max_depth={MAX_TRAVERSAL_DEPTH}", f"paths/?{self.pair}",
                     f"query/?limit={MAX_QUERY_LIMIT}", "query/", f"query/?entity_type=CUSTOMER&entity_id={self.customer.pk}"):
            with self.subTest(tail=tail):
                self.assertEqual(self.owner.get(self.url(tail)).status_code, 200, tail)

    def test_datetime_filters(self):
        endpoints = (f"traversal/?{self.root}", "query/", f"journeys/customer/{self.customer.pk}/",
                     f"journeys/order/{self.order.pk}/")
        for endpoint in endpoints:
            sep = "&" if "?" in endpoint else "?"
            for name in ("time_from", "time_to", "valid_at"):
                for bad in ("garbage", "2026-13-45T00:00:00Z", "2026-10-01T00:00:00", "2026-10-01"):
                    with self.subTest(endpoint=endpoint, name=name, bad=bad):
                        self.assert_400(self.owner.get(self.url(f"{endpoint}{sep}{name}={bad}")), f"{name}={bad}")
            with self.subTest(endpoint=endpoint, valid=True):
                ok = self.owner.get(self.url(f"{endpoint}{sep}time_from=2026-01-01T00:00:00%2B00:00&time_to=2027-01-01T00:00:00Z"))
                self.assertEqual(ok.status_code, 200, ok.content)

    def test_snapshot_bodies(self):
        for body in ([1], "text", {"root_entity_id": "abc", "snapshot_type": "CUSTOMER"},
                     {"root_entity_id": 1.5, "snapshot_type": "CUSTOMER"}, {"root_entity_id": True, "snapshot_type": "CUSTOMER"},
                     {"root_entity_id": 0, "snapshot_type": "CUSTOMER"}, {"snapshot_type": 5}, {"snapshot_type": ["BUSINESS"]},
                     {"name": ["x"]}, {"filters": {"time_from": "2026-10-01T00:00:00"}},
                     {"filters": {"valid_at": "garbage"}}):
            with self.subTest(body=body):
                self.assert_400(self.owner.post(self.url("snapshots/"), body), body)
        self.assertEqual(models.GraphSnapshot.objects.count(), 0)
        good = self.owner.post(self.url("snapshots/"), {"snapshot_type": "CUSTOMER", "root_entity_id": self.customer.pk})
        self.assertEqual(good.status_code, 201, good.content)
        as_text = self.owner.post(self.url("snapshots/"), {"snapshot_type": "CUSTOMER", "root_entity_id": str(self.customer.pk)})
        self.assertEqual(as_text.status_code, 201, as_text.content)

    def test_rebuild_body(self):
        self.assert_400(self.owner.post(self.url("rebuild/"), [1]), "list body")
        self.assertEqual(self.owner.post(self.url("rebuild/"), {}).status_code, 200)
        self.assertEqual(self.owner.post(self.url("rebuild/"), {"clean": True}).status_code, 200)
