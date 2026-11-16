"""Regression test for BGA-16:
Labels: PRODUCT_VARIANT reads title (field is name); customer without display_name -> "Customer #N"; no truncation to 255.
"""
from django.test import TestCase

from app import models
from app.business_graph import projection


class NodeLabelsVariantNameTruncationTests(TestCase):
    def setUp(self):
        self.business = models.Business.objects.create(
            name="Label Test Business",
        )

    def test_variant_with_name_shows_name_as_node_label(self):
        product = models.Product.objects.create(
            business=self.business,
            name="Sample Product",
        )
        variant = models.ProductVariant.objects.create(
            product=product,
            name="Sapphire Blue / XL",
            sku="SKU-BLU-XL",
        )

        node, _ = projection.project_entity_node(
            business_id=self.business.pk,
            entity_type="PRODUCT_VARIANT",
            entity_id=variant.pk,
        )
        self.assertIsNotNone(node)
        self.assertEqual(node.label, "Sapphire Blue / XL")

    def test_customer_without_display_name_composes_first_and_last_name(self):
        customer = models.Customer.objects.create(
            business=self.business,
            first_name="Rahim",
            last_name="Khan",
            display_name=None,
        )

        node, _ = projection.project_entity_node(
            business_id=self.business.pk,
            entity_type="CUSTOMER",
            entity_id=customer.pk,
        )
        self.assertIsNotNone(node)
        self.assertEqual(node.label, "Rahim Khan")

    def test_node_label_truncated_to_255_chars(self):
        long_name = "X" * 300
        product = models.Product.objects.create(
            business=self.business,
            name=long_name,
        )

        node, _ = projection.project_entity_node(
            business_id=self.business.pk,
            entity_type="PRODUCT",
            entity_id=product.pk,
        )
        self.assertIsNotNone(node)
        self.assertEqual(len(node.label), 255)
        self.assertEqual(node.label, "X" * 255)
