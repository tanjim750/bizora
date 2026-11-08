"""BI §1: canonical references, evidence, tenant isolation and safe replay."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from unittest.mock import patch

from django.db.models import Q
from django.db.utils import IntegrityError
from django.test import TestCase

from app import models
from app.business_intelligence import (
    RelationshipConflictError,
    RelationshipRebuildResult,
    RelationshipValidationError,
    rebuild_relationships,
)


T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
T1 = T0 + timedelta(days=1)
T2 = T0 + timedelta(days=2)
T3 = T0 + timedelta(days=3)
OWNER = "business_intelligence.relationships"


class RelationshipTests(TestCase):
    """Use persisted source records and the public service, mocking only its clock."""

    def setUp(self):
        self.business = models.Business.objects.create(
            name="Fixture shop", slug="fixture-shop", created_at=T0, updated_at=T0,
        )
        self.other = models.Business.objects.create(
            name="Other shop", slug="other-shop", created_at=T0, updated_at=T0,
        )
        self.sequence = 0

    def make(self, model, **values):
        """Explicit, small fixture defaults; never synthesize analytical outputs."""
        self.sequence += 1
        defaults = {
            models.Product: {"name": "Fixture product"},
            models.OrderItem: {
                "product_name": "Fixture line", "unit_price": Decimal("20.00"),
                "total_amount": Decimal("20.00"),
            },
            models.Payment: {"amount": Decimal("20.00")},
            models.Shipment: {"provider": "fixture-courier"},
            models.Conversation: {"channel": "CHAT", "started_at": T0},
            models.ConversationParticipant: {"participant_type": "CUSTOMER"},
            models.Message: {"direction": "INBOUND", "sender_type": "CUSTOMER"},
            models.Call: {"direction": "INBOUND", "status": "COMPLETED"},
            models.Campaign: {"name": "Fixture campaign", "platform": "META"},
            models.CampaignConversion: {"conversion_type": "PURCHASE", "converted_at": T0},
            models.WebsiteVisitor: {"visitor_key": f"visitor-{self.sequence}", "first_seen_at": T0},
            models.WebsiteSession: {"started_at": T0},
            models.WebsiteEvent: {"event_type": "PURCHASE", "occurred_at": T0},
            models.IntegrationSource: {
                "key": f"fixture-{self.sequence}", "name": "Fixture source", "category": "TEST",
            },
        }.get(model, {}).copy()
        fields = {field.name for field in model._meta.fields}
        if "business" in fields:
            defaults["business"] = self.business
        for field in ("created_at", "updated_at"):
            if field in fields:
                defaults[field] = T0
        defaults.update(values)
        return model.objects.create(**defaults)

    def full_graph(self):
        """One source path for each of the 23 supported directional relationships."""
        customer = self.make(models.Customer)
        product = self.make(models.Product)
        variant = self.make(models.ProductVariant, product=product)
        order = self.make(models.Order, customer=customer)
        item = self.make(models.OrderItem, order=order, product=product, product_variant=variant)
        payment = self.make(models.Payment, order=order, customer=customer)
        shipment = self.make(models.Shipment, order=order, customer=customer)
        conversation = self.make(models.Conversation, customer=customer)
        participant = self.make(
            models.ConversationParticipant, conversation=conversation, customer=customer,
        )
        message = self.make(models.Message, conversation=conversation, customer=customer)
        call = self.make(models.Call, customer=customer, conversation=conversation, order=order)
        visitor = self.make(models.WebsiteVisitor, customer=customer)
        session = self.make(models.WebsiteSession, visitor=visitor, customer=customer)
        event = self.make(
            models.WebsiteEvent, session=session, visitor=visitor, customer=customer,
            product=product, order=order,
        )
        campaign = self.make(models.Campaign)
        conversion = self.make(
            models.CampaignConversion, campaign=campaign, customer=customer, order=order,
            website_session_id=session.pk, attribution_type="PLATFORM_REPORTED",
        )
        return locals()

    def rebuild(self, at=T1):
        with patch("app.business_intelligence.relationships.timezone.now", return_value=at):
            return rebuild_relationships(business_id=self.business.pk)

    def rows(self):
        return list(models.BusinessRelationship.objects.order_by("pk").values())

    def edge(self, name, source, target):
        return models.BusinessRelationship.objects.get(
            business=self.business, rule_key=f"bi.relationship.{name}.v1",
            source_entity_id=source.pk, target_entity_id=target.pk,
        )

    def seed_edge(self, **values):
        defaults = dict(
            business=self.business, source_entity_type="CUSTOMER", source_entity_id=9001,
            relationship_type="PLACED_ORDER", target_entity_type="ORDER", target_entity_id=9002,
            relationship_source="DETERMINISTIC", rule_key="bi.relationship.customer_order.v1",
            confidence=Decimal("1"), metadata={"service": OWNER, "evidence": []},
            valid_from=T0, valid_to=None, created_at=T0, updated_at=T0,
        )
        defaults.update(values)
        row = models.BusinessRelationship.objects.create(**defaults)
        models.BusinessRelationship.objects.filter(pk=row.pk).update(
            created_at=defaults["created_at"], updated_at=defaults["updated_at"]
        )
        row.refresh_from_db()
        return row

    def test_every_supported_rule_has_an_exact_direction_and_canonical_endpoint(self):
        g = self.full_graph()
        result = self.rebuild()
        expected = [
            ("customer_order", "CUSTOMER", "customer", "PLACED_ORDER", "ORDER", "order"),
            ("order_product", "ORDER", "order", "CONTAINS_PRODUCT", "PRODUCT", "product"),
            ("order_variant", "ORDER", "order", "CONTAINS_VARIANT", "PRODUCT_VARIANT", "variant"),
            ("order_payment", "ORDER", "order", "HAS_PAYMENT", "PAYMENT", "payment"),
            ("order_shipment", "ORDER", "order", "HAS_SHIPMENT", "SHIPMENT", "shipment"),
            ("customer_conversation", "CUSTOMER", "customer", "HAS_CONVERSATION", "CONVERSATION", "conversation"),
            ("customer_message", "CUSTOMER", "customer", "HAS_MESSAGE", "MESSAGE", "message"),
            ("conversation_message", "CONVERSATION", "conversation", "HAS_MESSAGE", "MESSAGE", "message"),
            ("customer_call", "CUSTOMER", "customer", "HAS_CALL", "CALL", "call"),
            ("conversation_call", "CONVERSATION", "conversation", "HAS_CALL", "CALL", "call"),
            ("order_call", "ORDER", "order", "HAS_CALL", "CALL", "call"),
            ("customer_visitor", "CUSTOMER", "customer", "HAS_VISITOR", "WEBSITE_VISITOR", "visitor"),
            ("visitor_session", "WEBSITE_VISITOR", "visitor", "HAS_SESSION", "WEBSITE_SESSION", "session"),
            ("customer_session", "CUSTOMER", "customer", "HAS_SESSION", "WEBSITE_SESSION", "session"),
            ("session_event", "WEBSITE_SESSION", "session", "HAS_EVENT", "WEBSITE_EVENT", "event"),
            ("customer_event", "CUSTOMER", "customer", "HAS_WEBSITE_EVENT", "WEBSITE_EVENT", "event"),
            ("event_product", "WEBSITE_EVENT", "event", "REFERENCES_PRODUCT", "PRODUCT", "product"),
            ("event_order", "WEBSITE_EVENT", "event", "REFERENCES_ORDER", "ORDER", "order"),
            ("session_order", "WEBSITE_SESSION", "session", "REFERENCES_ORDER", "ORDER", "order"),
            ("campaign_conversion", "CAMPAIGN", "campaign", "HAS_REPORTED_CONVERSION", "CAMPAIGN_CONVERSION", "conversion"),
            ("campaign_customer", "CAMPAIGN", "campaign", "REPORTED_CUSTOMER", "CUSTOMER", "customer"),
            ("campaign_order", "CAMPAIGN", "campaign", "REPORTED_ORDER", "ORDER", "order"),
            ("campaign_session", "CAMPAIGN", "campaign", "REPORTED_SESSION", "WEBSITE_SESSION", "session"),
        ]
        actual = set(models.BusinessRelationship.objects.values_list(
            "rule_key", "source_entity_type", "source_entity_id", "relationship_type",
            "target_entity_type", "target_entity_id",
        ))
        self.assertEqual(actual, {
            (f"bi.relationship.{name}.v1", st, g[s].pk, rel, tt, g[t].pk)
            for name, st, s, rel, tt, t in expected
        })
        self.assertEqual(result, RelationshipRebuildResult(created=23))
        for row in models.BusinessRelationship.objects.all():
            self.assertEqual(row.business_id, self.business.pk)
            self.assertEqual(row.confidence, Decimal("1.0000"))
            self.assertEqual(row.relationship_source, "DETERMINISTIC")
            self.assertEqual(row.metadata["service"], OWNER)
            self.assertTrue(row.metadata["evidence"])
            self.assertIsNone(row.valid_to)
            self.assertEqual((row.valid_from, row.created_at, row.updated_at), (T1, T1, T1))

    def test_replay_preserves_every_row_id_timestamp_and_metadata(self):
        g = self.full_graph()
        canonical = {type(row): [] for row in g.values() if isinstance(row, models.models.Model)}
        for model in canonical:
            canonical[model] = list(model.objects.order_by("pk").values())
        self.rebuild()
        before = self.rows()
        self.assertEqual(self.rebuild(T2), RelationshipRebuildResult(unchanged=23))
        self.assertEqual(self.rows(), before)
        for model, values in canonical.items():
            self.assertEqual(list(model.objects.order_by("pk").values()), values)

    def test_duplicate_source_paths_aggregate_sorted_evidence_without_duplicate_edges(self):
        g = self.full_graph()
        item = self.make(models.OrderItem, order=g["order"], product=g["product"], product_variant=g["variant"])
        participant = self.make(models.ConversationParticipant, conversation=g["conversation"], customer=g["customer"])
        event = self.make(models.WebsiteEvent, session=g["session"], visitor=g["visitor"], order=g["order"])
        conversion = self.make(
            models.CampaignConversion, campaign=g["campaign"], customer=g["customer"],
            order=g["order"], website_session_id=g["session"].pk,
        )
        self.assertEqual(self.rebuild().created, 26)
        checks = [
            ("order_product", g["order"], g["product"], "ORDER_ITEM", {g["item"].pk, item.pk}),
            ("customer_conversation", g["customer"], g["conversation"], "CONVERSATION_PARTICIPANT", {g["participant"].pk, participant.pk}),
            ("session_order", g["session"], g["order"], "WEBSITE_EVENT", {g["event"].pk, event.pk}),
            ("campaign_order", g["campaign"], g["order"], "CAMPAIGN_CONVERSION", {g["conversion"].pk, conversion.pk}),
        ]
        for name, source, target, entity_type, ids in checks:
            with self.subTest(rule=name):
                evidence = self.edge(name, source, target).metadata["evidence"]
                self.assertEqual({ref["entity_id"] for ref in evidence if ref["entity_type"] == entity_type}, ids)
                serialized = [json.dumps(ref, sort_keys=True) for ref in evidence]
                self.assertEqual(serialized, sorted(set(serialized)))
        evidence = self.edge("session_order", g["session"], g["order"]).metadata["evidence"]
        self.assertEqual(sum(ref["entity_type"] == "WEBSITE_SESSION" for ref in evidence), 1)
        before = self.rows()
        self.assertEqual(self.rebuild(T2).unchanged, 26)
        self.assertEqual(self.rows(), before)

    def test_evidence_changes_update_one_row_and_keep_its_original_valid_from(self):
        customer = self.make(models.Customer)
        order = self.make(models.Order, customer=customer)
        product = self.make(models.Product)
        first = self.make(models.OrderItem, order=order, product=product)
        self.rebuild()
        row = self.edge("order_product", order, product)
        second = self.make(models.OrderItem, order=order, product=product)
        self.assertEqual(self.rebuild(T2), RelationshipRebuildResult(updated=1, unchanged=1))
        row.refresh_from_db()
        self.assertEqual((row.valid_from, row.created_at, row.updated_at), (T1, T1, T2))
        self.assertEqual(row.metadata["evidence"], [
            {"entity_type": "ORDER_ITEM", "entity_id": item.pk,
             "fields": ["order_id", "product_id", "product_variant_id"]}
            for item in sorted([first, second], key=lambda item: json.dumps({"entity_type": "ORDER_ITEM", "entity_id": item.pk, "fields": ["order_id", "product_id", "product_variant_id"]}, sort_keys=True))
        ])

    def test_variant_only_item_derives_product_with_parent_evidence(self):
        order = self.make(models.Order)
        product = self.make(models.Product)
        variant = self.make(models.ProductVariant, product=product)
        item = self.make(models.OrderItem, order=order, product_variant=variant)
        self.assertEqual(self.rebuild().created, 2)
        for name, target in [("order_product", product), ("order_variant", variant)]:
            evidence = self.edge(name, order, target).metadata["evidence"]
            self.assertIn({"entity_type": "PRODUCT_VARIANT", "entity_id": variant.pk, "fields": ["product_id"]}, evidence)
            self.assertIn({"entity_type": "ORDER_ITEM", "entity_id": item.pk, "fields": ["order_id", "product_id", "product_variant_id"]}, evidence)

    def test_variant_and_explicit_product_disagreement_rejects_entire_rebuild(self):
        order = self.make(models.Order, customer=self.make(models.Customer))
        product = self.make(models.Product)
        variant = self.make(models.ProductVariant, product=self.make(models.Product))
        self.make(models.OrderItem, order=order, product=product, product_variant=variant)
        with self.assertRaises(RelationshipValidationError):
            self.rebuild()
        self.assertEqual(self.rows(), [])

    def test_event_visitor_must_match_session_visitor(self):
        session = self.make(models.WebsiteSession, visitor=self.make(models.WebsiteVisitor))
        self.make(models.WebsiteEvent, session=session, visitor=self.make(models.WebsiteVisitor))
        with self.assertRaises(RelationshipValidationError):
            self.rebuild()
        self.assertEqual(self.rows(), [])

    def test_explicit_session_and_event_customers_do_not_merge_visitor_identity(self):
        visitor_customer = self.make(models.Customer)
        session_customer = self.make(models.Customer)
        event_customer = self.make(models.Customer)
        visitor = self.make(models.WebsiteVisitor, customer=visitor_customer)
        session = self.make(models.WebsiteSession, visitor=visitor, customer=session_customer)
        event = self.make(models.WebsiteEvent, session=session, visitor=visitor, customer=event_customer)
        self.rebuild()
        self.edge("customer_visitor", visitor_customer, visitor)
        self.edge("customer_session", session_customer, session)
        self.edge("customer_event", event_customer, event)
        self.assertEqual(models.BusinessRelationship.objects.filter(source_entity_type="CUSTOMER").count(), 3)

    def test_null_customer_references_never_inherit_parent_customer(self):
        customer = self.make(models.Customer)
        conversation = self.make(models.Conversation, customer=customer)
        message = self.make(models.Message, conversation=conversation)
        visitor = self.make(models.WebsiteVisitor, customer=customer)
        session = self.make(models.WebsiteSession, visitor=visitor)
        event = self.make(models.WebsiteEvent, session=session, visitor=visitor)
        self.rebuild()
        for rule, target in [("customer_message", message), ("customer_session", session), ("customer_event", event)]:
            self.assertFalse(models.BusinessRelationship.objects.filter(rule_key=f"bi.relationship.{rule}.v1", target_entity_id=target.pk).exists())
        self.edge("conversation_message", conversation, message)
        self.edge("visitor_session", visitor, session)

    def test_nullable_links_and_matching_utm_names_phones_do_not_create_inferred_edges(self):
        customer = self.make(models.Customer, display_name="Same Name", source_metadata={"phone": "01000000000"})
        self.make(models.CustomerContact, customer=customer, contact_type="PHONE", value="01000000000")
        self.make(models.Order, source_metadata={"customer_name": "Same Name", "phone": "01000000000"})
        self.make(models.OrderItem, order=self.make(models.Order), product_name="Fixture product")
        self.make(models.Payment)
        self.make(models.Call, caller_number="01000000000")
        campaign = self.make(models.Campaign, name="same-campaign", external_campaign_id="123")
        visitor = self.make(models.WebsiteVisitor)
        session = self.make(models.WebsiteSession, visitor=visitor, utm_campaign=campaign.name, utm_source="META", source_metadata={"campaign_id": campaign.pk})
        self.assertEqual(self.rebuild().created, 1)
        self.edge("visitor_session", visitor, session)

    def test_pending_and_failed_payments_have_neutral_reference_links(self):
        order = self.make(models.Order)
        payments = [self.make(models.Payment, order=order, status=status) for status in ("PENDING", "FAILED")]
        self.assertEqual(self.rebuild().created, 2)
        self.assertEqual(set(models.BusinessRelationship.objects.values_list("relationship_type", flat=True)), {"HAS_PAYMENT"})
        for payment in payments:
            row = self.edge("order_payment", order, payment)
            self.assertEqual(row.confidence, Decimal("1"))
            self.assertEqual(row.metadata["evidence"], [{"entity_type": "PAYMENT", "entity_id": payment.pk, "fields": ["order_id"]}])

    def test_campaign_edges_keep_reported_platform_provenance_without_copying_payload(self):
        g = self.full_graph()
        integration = self.make(models.IntegrationConnection, integration_source=self.make(models.IntegrationSource))
        models.Campaign.objects.filter(pk=g["campaign"].pk).update(integration_connection=integration, platform="META")
        models.CampaignConversion.objects.filter(pk=g["conversion"].pk).update(metadata={"private_payload": "DO_NOT_COPY"})
        self.rebuild()
        for name, target in [("campaign_conversion", g["conversion"]), ("campaign_customer", g["customer"]), ("campaign_order", g["order"]), ("campaign_session", g["session"])]:
            row = self.edge(name, g["campaign"], target)
            self.assertEqual(row.metadata["evidence"], [{
                "entity_type": "CAMPAIGN_CONVERSION", "entity_id": g["conversion"].pk,
                "fields": ["campaign_id", "customer_id", "order_id", "website_session_id"],
                "provenance": "SOURCE_REPORTED", "platform": "META",
                "attribution_type": "PLATFORM_REPORTED", "integration_connection_id": integration.pk,
            }])
            self.assertNotIn("DO_NOT_COPY", json.dumps(row.metadata))
            self.assertIn("REPORTED", row.relationship_type)

    def test_nonexistent_integer_conversion_session_rejects_and_preserves_existing_rows(self):
        g = self.full_graph()
        self.rebuild()
        before = self.rows()
        self.make(models.Order, customer=g["customer"])
        models.CampaignConversion.objects.filter(pk=g["conversion"].pk).update(website_session_id=9999999)
        with self.assertRaisesMessage(RelationshipValidationError, "Missing WebsiteSession"):
            self.rebuild(T2)
        self.assertEqual(self.rows(), before)

    def test_cross_business_references_fail_at_every_canonical_boundary(self):
        g = self.full_graph()
        foreign_customer = self.make(models.Customer, business=self.other)
        foreign_product = self.make(models.Product, business=self.other)
        foreign_variant = self.make(models.ProductVariant, product=foreign_product)
        foreign_order = self.make(models.Order, business=self.other)
        foreign_conversation = self.make(models.Conversation, business=self.other)
        foreign_visitor = self.make(models.WebsiteVisitor, business=self.other)
        foreign_session = self.make(models.WebsiteSession, business=self.other, visitor=foreign_visitor)
        foreign_integration = self.make(models.IntegrationConnection, business=self.other, integration_source=self.make(models.IntegrationSource))
        self.rebuild()
        before = self.rows()
        references = [
            (g["order"], "customer_id", foreign_customer.pk),
            (g["order"], "integration_connection_id", foreign_integration.pk),
            (g["item"], "product_id", foreign_product.pk),
            (g["item"], "product_variant_id", foreign_variant.pk),
            (g["payment"], "order_id", foreign_order.pk),
            (g["payment"], "customer_id", foreign_customer.pk),
            (g["payment"], "integration_connection_id", foreign_integration.pk),
            (g["shipment"], "order_id", foreign_order.pk),
            (g["shipment"], "customer_id", foreign_customer.pk),
            (g["shipment"], "integration_connection_id", foreign_integration.pk),
            (g["conversation"], "customer_id", foreign_customer.pk),
            (g["conversation"], "integration_connection_id", foreign_integration.pk),
            (g["participant"], "customer_id", foreign_customer.pk),
            (g["message"], "customer_id", foreign_customer.pk),
            (g["message"], "integration_connection_id", foreign_integration.pk),
            (g["call"], "customer_id", foreign_customer.pk),
            (g["call"], "order_id", foreign_order.pk),
            (g["call"], "conversation_id", foreign_conversation.pk),
            (g["call"], "integration_connection_id", foreign_integration.pk),
            (g["visitor"], "customer_id", foreign_customer.pk),
            (g["session"], "visitor_id", foreign_visitor.pk),
            (g["session"], "customer_id", foreign_customer.pk),
            (g["session"], "integration_connection_id", foreign_integration.pk),
            (g["event"], "visitor_id", foreign_visitor.pk),
            (g["event"], "customer_id", foreign_customer.pk),
            (g["event"], "product_id", foreign_product.pk),
            (g["event"], "order_id", foreign_order.pk),
            (g["campaign"], "integration_connection_id", foreign_integration.pk),
            (g["conversion"], "customer_id", foreign_customer.pk),
            (g["conversion"], "order_id", foreign_order.pk),
            (g["conversion"], "website_session_id", foreign_session.pk),
        ]
        for row, field, foreign_id in references:
            with self.subTest(model=type(row).__name__, field=field):
                original = getattr(row, field)
                type(row).objects.filter(pk=row.pk).update(**{field: foreign_id})
                try:
                    with self.assertRaises(RelationshipValidationError):
                        self.rebuild(T2)
                    self.assertEqual(self.rows(), before)
                finally:
                    type(row).objects.filter(pk=row.pk).update(**{field: original})

    def test_invalid_foreign_roots_are_not_inspected_when_rebuilding_local_business(self):
        customer = self.make(models.Customer)
        order = self.make(models.Order, customer=customer)
        self.make(models.Order, business=self.other, customer=customer)
        self.assertEqual(self.rebuild(), RelationshipRebuildResult(created=1))
        self.edge("customer_order", customer, order)
        self.assertFalse(models.BusinessRelationship.objects.filter(business=self.other).exists())

    def test_missing_links_invalidate_once_and_revival_reuses_id(self):
        customer = self.make(models.Customer)
        order = self.make(models.Order, customer=customer)
        self.rebuild()
        row = self.edge("customer_order", customer, order)
        row_id = row.pk
        models.Order.objects.filter(pk=order.pk).update(customer=None)
        self.assertEqual(self.rebuild(T2), RelationshipRebuildResult(invalidated=1))
        row.refresh_from_db()
        self.assertEqual((row.valid_from, row.valid_to, row.created_at, row.updated_at), (T1, T2, T1, T2))
        before = self.rows()
        self.assertEqual(self.rebuild(T3), RelationshipRebuildResult())
        self.assertEqual(self.rows(), before)
        models.Order.objects.filter(pk=order.pk).update(customer=customer)
        self.assertEqual(self.rebuild(T3), RelationshipRebuildResult(updated=1))
        row.refresh_from_db()
        self.assertEqual(row.pk, row_id)
        self.assertEqual((row.valid_from, row.valid_to, row.created_at, row.updated_at), (T3, None, T1, T3))

    def test_removed_evidence_does_not_invalidate_edge_with_another_supporting_reference(self):
        customer = self.make(models.Customer)
        conversation = self.make(models.Conversation, customer=customer)
        participant = self.make(models.ConversationParticipant, conversation=conversation, customer=customer)
        self.rebuild()
        row_id = self.edge("customer_conversation", customer, conversation).pk
        participant.delete()
        self.assertEqual(self.rebuild(T2), RelationshipRebuildResult(updated=1))
        row = self.edge("customer_conversation", customer, conversation)
        self.assertEqual(row.pk, row_id)
        self.assertIsNone(row.valid_to)
        self.assertEqual(row.metadata["evidence"], [{"entity_type": "CONVERSATION", "entity_id": conversation.pk, "fields": ["customer_id"]}])

    def test_preserves_manual_unknown_owner_unknown_rule_and_foreign_business_rows(self):
        preserved = [
            self.seed_edge(source_entity_id=8001, relationship_source="MANUAL"),
            self.seed_edge(source_entity_id=8002, metadata={"service": "another-service"}),
            self.seed_edge(source_entity_id=8003, rule_key="bi.relationship.future.v99"),
            self.seed_edge(source_entity_id=8004, metadata=None),
            self.seed_edge(source_entity_id=8005, metadata=[OWNER]),
            self.seed_edge(source_entity_id=8006, business=self.other),
        ]
        before = {row["id"]: row for row in self.rows()}
        stale = self.seed_edge()
        self.assertEqual(self.rebuild(T2), RelationshipRebuildResult(invalidated=1))
        after = {row["id"]: row for row in self.rows()}
        for row in preserved:
            self.assertEqual(after[row.pk], before[row.pk])
        stale.refresh_from_db()
        self.assertEqual(stale.valid_to, T2)

    def test_existing_candidate_owned_elsewhere_fails_without_overwriting(self):
        customer = self.make(models.Customer)
        order = self.make(models.Order, customer=customer)
        ownerships = [
            {"relationship_source": "MANUAL"},
            {"rule_key": "another-rule"},
            {"metadata": {"service": "another-owner"}},
            {"metadata": None},
            {"rule_key": "bi.relationship.order_product.v1"},
        ]
        for ownership in ownerships:
            with self.subTest(ownership=ownership):
                row = self.seed_edge(source_entity_id=customer.pk, target_entity_id=order.pk, **ownership)
                before = self.rows()
                try:
                    with self.assertRaises(RelationshipConflictError):
                        self.rebuild(T2)
                    self.assertEqual(self.rows(), before)
                finally:
                    row.delete()

    def test_tuple_conflict_is_detected_before_any_write_so_no_row_changes(self):
        """The occupied-tuple pre-check runs before the write loop; nothing is written."""
        g = self.full_graph()
        stale = self.seed_edge()
        existing = self.seed_edge(
            source_entity_id=g["customer"].pk, target_entity_id=g["order"].pk,
            confidence=Decimal("0.2500"),
        )
        self.seed_edge(
            source_entity_type="WEBSITE_VISITOR", source_entity_id=g["visitor"].pk,
            relationship_type="HAS_SESSION", target_entity_type="WEBSITE_SESSION",
            target_entity_id=g["session"].pk, relationship_source="MANUAL", rule_key=None,
        )
        before = self.rows()
        with self.assertRaises(RelationshipConflictError):
            self.rebuild(T2)
        self.assertEqual(self.rows(), before)
        stale.refresh_from_db()
        existing.refresh_from_db()
        self.assertIsNone(stale.valid_to)
        self.assertEqual(existing.confidence, Decimal("0.2500"))

    def test_database_failure_during_write_phase_rolls_back_every_write_and_maps_to_conflict(self):
        """Fail after real creates/updates/invalidations were written, then prove rollback."""
        g = self.full_graph()
        stale = self.seed_edge()  # owned, no longer a candidate: would be invalidated
        updatable = self.seed_edge(  # owned candidate with wrong confidence: would be updated
            source_entity_id=g["customer"].pk, target_entity_id=g["order"].pk,
            confidence=Decimal("0.2500"),
        )
        manual = self.seed_edge(source_entity_id=8001, relationship_source="MANUAL")
        before = self.rows()
        BR = models.BusinessRelationship
        # 23 supported candidates, one of which already exists as `updatable`.
        expected_creates = 22
        real_create = BR.objects.create
        real_save = BR.save

        def observe():
            """Read through the open transaction to prove writes really happened."""
            return {
                "total": BR.objects.count(),
                "updatable_confidence": BR.objects.get(pk=updatable.pk).confidence,
                "stale_valid_to": BR.objects.get(pk=stale.pk).valid_to,
            }

        def assert_fully_rolled_back():
            self.assertEqual(self.rows(), before)
            self.assertEqual(BR.objects.count(), len(before))
            stale.refresh_from_db()
            updatable.refresh_from_db()
            manual.refresh_from_db()
            self.assertIsNone(stale.valid_to)
            self.assertEqual(stale.updated_at, T0)
            self.assertEqual(updatable.confidence, Decimal("0.2500"))
            self.assertEqual(updatable.metadata, {"service": OWNER, "evidence": []})
            self.assertEqual((updatable.valid_from, updatable.valid_to, updatable.updated_at), (T0, None, T0))
            self.assertEqual(manual.updated_at, T0)

        def run_failing_rebuild():
            with self.assertRaises(RelationshipConflictError) as raised:
                self.rebuild(T2)
            self.assertIsInstance(raised.exception.__cause__, IntegrityError)
            self.assertIn("constraint conflict", str(raised.exception))

        for fail_at in (3, expected_creates):
            with self.subTest(phase="create", failing_call=fail_at):
                calls, observed = [], {}

                def flaky_create(*args, _calls=calls, _fail_at=fail_at, _observed=observed, **kwargs):
                    _calls.append(kwargs["rule_key"])
                    if len(_calls) == _fail_at:
                        _observed.update(observe())
                        raise IntegrityError("simulated unique tuple race")
                    return real_create(*args, **kwargs)

                with patch.object(BR.objects, "create", side_effect=flaky_create):
                    run_failing_rebuild()
                # The failure was not the first create; earlier creates were really written.
                self.assertEqual(len(calls), fail_at)
                self.assertEqual(observed["total"], len(before) + fail_at - 1)
                if fail_at == expected_creates:
                    # Every other create and the in-place update were written before failing.
                    self.assertEqual(observed["updatable_confidence"], Decimal("1"))
                    self.assertIsNone(observed["stale_valid_to"])
                assert_fully_rolled_back()

        with self.subTest(phase="invalidation"):
            observed = {}

            def flaky_save(instance, *args, **kwargs):
                if kwargs.get("update_fields") == ["valid_to", "updated_at"]:
                    observed.update(observe())
                    raise IntegrityError("simulated failure while expiring a stale link")
                return real_save(instance, *args, **kwargs)

            with patch.object(BR, "save", flaky_save):
                run_failing_rebuild()
            # All creates and the update had been written when invalidation failed.
            self.assertEqual(observed["total"], len(before) + expected_creates)
            self.assertEqual(observed["updatable_confidence"], Decimal("1"))
            self.assertIsNone(observed["stale_valid_to"])
            assert_fully_rolled_back()

        # The same inputs still succeed afterward, so the rollback left no poisoned state.
        self.assertEqual(
            self.rebuild(T2),
            RelationshipRebuildResult(created=expected_creates, updated=1, invalidated=1),
        )
        stale.refresh_from_db()
        self.assertEqual(stale.valid_to, T2)

    def test_children_of_other_business_parents_are_silently_skipped_not_rejected(self):
        """Parent FKs are not validated; the queryset scope excludes such child rows."""
        g = self.full_graph()
        self.assertEqual(self.rebuild(), RelationshipRebuildResult(created=23))
        baseline = self.rows()
        foreign_order = self.make(models.Order, business=self.other)
        foreign_conversation = self.make(models.Conversation, business=self.other)
        foreign_visitor = self.make(models.WebsiteVisitor, business=self.other)
        foreign_session = self.make(models.WebsiteSession, business=self.other, visitor=foreign_visitor)
        foreign_campaign = self.make(models.Campaign, business=self.other)
        # Each child below references only LOCAL entities except for its parent FK.
        children = [
            ("ORDER", foreign_order, lambda: self.make(
                models.OrderItem, order=foreign_order, product=g["product"], product_variant=g["variant"])),
            ("CONVERSATION", foreign_conversation, lambda: self.make(
                models.ConversationParticipant, conversation=foreign_conversation, customer=g["customer"])),
            ("CONVERSATION", foreign_conversation, lambda: self.make(
                models.Message, conversation=foreign_conversation, customer=g["customer"])),
            ("WEBSITE_SESSION", foreign_session, lambda: self.make(
                models.WebsiteEvent, session=foreign_session, visitor=g["visitor"], customer=g["customer"],
                product=g["product"], order=g["order"])),
            ("CAMPAIGN", foreign_campaign, lambda: self.make(
                models.CampaignConversion, campaign=foreign_campaign, customer=g["customer"],
                order=g["order"], website_session_id=g["session"].pk)),
        ]
        for parent_type, parent, build_child in children:
            child = build_child()
            with self.subTest(child=type(child).__name__):
                try:
                    self.assertEqual(self.rebuild(T2), RelationshipRebuildResult(unchanged=23))
                    self.assertEqual(self.rows(), baseline)
                    self.assertFalse(models.BusinessRelationship.objects.filter(
                        Q(source_entity_type=parent_type, source_entity_id=parent.pk)
                        | Q(target_entity_type=parent_type, target_entity_id=parent.pk)
                    ).exists())
                    self.assertFalse(models.BusinessRelationship.objects.filter(
                        business=self.other).exists())
                finally:
                    child.delete()
        # Replaying with the skipped children removed is still the untouched local graph.
        self.assertEqual(self.rebuild(T3), RelationshipRebuildResult(unchanged=23))
        self.assertEqual(self.rows(), baseline)

    def test_owned_confidence_is_repaired_without_resetting_validity(self):
        customer = self.make(models.Customer)
        order = self.make(models.Order, customer=customer)
        self.rebuild()
        row = self.edge("customer_order", customer, order)
        models.BusinessRelationship.objects.filter(pk=row.pk).update(confidence=Decimal("0.5"))
        self.assertEqual(self.rebuild(T2), RelationshipRebuildResult(updated=1))
        row.refresh_from_db()
        self.assertEqual(row.confidence, Decimal("1"))
        self.assertEqual((row.valid_from, row.created_at, row.updated_at), (T1, T1, T2))

    def test_business_id_requires_existing_positive_integer_and_rejects_bool(self):
        self.seed_edge()
        before = self.rows()
        for business_id in (None, True, False, "1", 1.0, Decimal("1"), 0, -1, 99999999):
            with self.subTest(business_id=business_id):
                with self.assertRaises(RelationshipValidationError):
                    rebuild_relationships(business_id=business_id)
                self.assertEqual(self.rows(), before)

    def test_empty_business_is_a_valid_noop(self):
        self.assertEqual(self.rebuild(), RelationshipRebuildResult())
        self.assertEqual(self.rows(), [])
