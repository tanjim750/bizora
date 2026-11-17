"""BGA-07: Node first_seen_at must use domain timestamps (occurred_at, sent_at,
paid_at, submitted_at, converted_at, visitor first_seen_at) rather than ingest time,
ensuring chronological journey timeline ordering.
"""

from datetime import datetime, timedelta, timezone
from django.test import TestCase

from app import models
from app.business_graph import project_business_graph
from app.business_graph.journeys import build_customer_journey
from app.business_graph.projection import project_entity_node

T_NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
T_YESTERDAY = T_NOW - timedelta(days=1)
T_LAST_WEEK = T_NOW - timedelta(days=7)


class EntityTimestampsJourneyOrderTests(TestCase):
    def setUp(self):
        self.business = models.Business.objects.create(
            name="Timeline Shop",
            slug="timeline-shop",
            currency="BDT",
            created_at=T_NOW,
            updated_at=T_NOW,
        )
        common = {"business": self.business, "created_at": T_NOW, "updated_at": T_NOW}
        self.customer = models.Customer.objects.create(
            first_name="Farhan", last_name="Ahmed", display_name="Farhan Ahmed", **common
        )
        # Order placed yesterday, created/ingested today
        self.order = models.Order.objects.create(
            customer=self.customer,
            status="PAID",
            currency="BDT",
            total_amount=120,
            ordered_at=T_YESTERDAY,
            **common,
        )
        # Website session and event occurred last week, created/ingested today
        self.visitor = models.WebsiteVisitor.objects.create(
            business=self.business,
            first_seen_at=T_LAST_WEEK,
            created_at=T_NOW,
            updated_at=T_NOW,
        )
        self.session = models.WebsiteSession.objects.create(
            business=self.business,
            visitor=self.visitor,
            started_at=T_LAST_WEEK,
            created_at=T_NOW,
        )
        self.event = models.WebsiteEvent.objects.create(
            session=self.session,
            visitor=self.visitor,
            event_type="PAGE_VIEW",
            occurred_at=T_LAST_WEEK,
            created_at=T_NOW,
        )
        # Relationships: Customer -> Order and Customer -> WebsiteSession
        models.BusinessRelationship.objects.create(
            business=self.business,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer.pk,
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order.pk,
            rule_key="bi.relationship.customer_order.v1",
            relationship_source="DETERMINISTIC",
            created_at=T_NOW,
            updated_at=T_NOW,
        )
        models.BusinessRelationship.objects.create(
            business=self.business,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer.pk,
            relationship_type="HAS_SESSION",
            target_entity_type="WEBSITE_SESSION",
            target_entity_id=self.session.pk,
            rule_key="bi.relationship.customer_session.v1",
            relationship_source="DETERMINISTIC",
            created_at=T_NOW,
            updated_at=T_NOW,
        )
        models.BusinessRelationship.objects.create(
            business=self.business,
            source_entity_type="WEBSITE_SESSION",
            source_entity_id=self.session.pk,
            relationship_type="HAS_EVENT",
            target_entity_type="WEBSITE_EVENT",
            target_entity_id=self.event.pk,
            rule_key="bi.relationship.session_event.v1",
            relationship_source="DETERMINISTIC",
            created_at=T_NOW,
            updated_at=T_NOW,
        )

    def test_node_first_seen_at_uses_domain_timestamps(self):
        """WebsiteEvent node must use occurred_at as first_seen_at, not created_at."""
        event_node, _ = project_entity_node(
            business_id=self.business.pk,
            entity_type="WEBSITE_EVENT",
            entity_id=self.event.pk,
        )
        self.assertEqual(event_node.first_seen_at, T_LAST_WEEK)

    def test_event_occurred_last_week_sorts_before_yesterday_order_in_journey(self):
        """Journey timeline must sort event with last week's occurred_at before yesterday's order."""
        project_business_graph(business_id=self.business.pk)
        journey = build_customer_journey(
            business_id=self.business.pk,
            customer_id=self.customer.pk,
        )
        timeline = journey.timeline
        event_indices = [i for i, ev in enumerate(timeline) if ev.entity_type == "WEBSITE_EVENT"]
        order_indices = [i for i, ev in enumerate(timeline) if ev.entity_type == "ORDER"]

        self.assertTrue(len(event_indices) > 0, "WebsiteEvent must be present in journey timeline")
        self.assertTrue(len(order_indices) > 0, "Order must be present in journey timeline")

        # Event from last week must come BEFORE order from yesterday
        self.assertLess(
            event_indices[0],
            order_indices[0],
            f"Event at index {event_indices[0]} should sort before Order at index {order_indices[0]}",
        )
