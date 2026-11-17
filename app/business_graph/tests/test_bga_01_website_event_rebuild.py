from django.test import TestCase
from django.utils import timezone

from app import models
from app.business_graph import rebuild_business_graph


class WebsiteEventRebuildIdempotencyTests(TestCase):
    def setUp(self):
        super().setUp()
        self.now = timezone.now()
        self.biz = models.Business.objects.create(
            name="Alpha Retail",
            slug="alpha-retail",
            currency="USD",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )

        self.visitor = models.WebsiteVisitor.objects.create(
            business=self.biz,
            visitor_key="visitor-101",
            first_seen_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        self.session = models.WebsiteSession.objects.create(
            business=self.biz,
            visitor=self.visitor,
            started_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        # WebsiteEvent with NO product (product=None)
        self.event = models.WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            event_type="PAGE_VIEW",
            page_url="https://example.com/home",
            occurred_at=self.now,
            product=None,
        )

        # Relationship linking session -> event
        self.rel = models.BusinessRelationship.objects.create(
            business=self.biz,
            source_entity_type="WEBSITE_SESSION",
            source_entity_id=self.session.pk,
            relationship_type="HAS_EVENT",
            target_entity_type="WEBSITE_EVENT",
            target_entity_id=self.event.pk,
            rule_key="session_event",
            relationship_source="DIRECT",
            confidence=1.0,
            created_at=self.now,
            updated_at=self.now,
        )

    def test_non_clean_rebuild_does_not_prune_or_churn_website_event_without_product(self):
        """Card BGA-01: Event without product: two rebuilds give identical ids, nodes_pruned == 0."""
        # First rebuild (initial projection)
        summary1 = rebuild_business_graph(business_id=self.biz.pk, clean=False)
        self.assertEqual(summary1.nodes_pruned, 0)

        # Find the node ID of the WEBSITE_EVENT node
        event_node_1 = models.GraphNode.objects.get(
            business_id=self.biz.pk,
            entity_type="WEBSITE_EVENT",
            entity_id=self.event.pk,
        )
        self.assertIsNotNone(event_node_1)

        # Second rebuild (reconciliation rebuild)
        summary2 = rebuild_business_graph(business_id=self.biz.pk, clean=False)

        # Invariant: non-clean rebuild must not prune valid event nodes
        self.assertEqual(
            summary2.nodes_pruned,
            0,
            f"Expected nodes_pruned == 0 on second rebuild, got {summary2.nodes_pruned}",
        )
        self.assertEqual(
            summary2.edges_pruned,
            0,
            f"Expected edges_pruned == 0 on second rebuild, got {summary2.edges_pruned}",
        )

        event_node_2 = models.GraphNode.objects.get(
            business_id=self.biz.pk,
            entity_type="WEBSITE_EVENT",
            entity_id=self.event.pk,
        )
        self.assertEqual(
            event_node_1.id,
            event_node_2.id,
            f"Node ID churned across rebuilds: was {event_node_1.id}, became {event_node_2.id}",
        )
