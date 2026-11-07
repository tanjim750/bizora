from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from app.models import Product, ProductExternalReference


def confirm_product(connection, result):
    return result.entity_type == 'PRODUCT' and ProductExternalReference.objects.filter(
        product_id=result.canonical_id, product__business_id=connection.business_id,
        integration_connection=connection, external_product_id=result.external_id).exists()


@transaction.atomic
def persist_product(connection, external_id, attributes, source_at, confirmed_at):
    """Validate a canonical product input and preserve monotonic source updates."""
    name = attributes.get('name')
    sku = attributes.get('sku')
    if not isinstance(name, str) or not name.strip() or len(name) > 255:
        raise ValidationError('A product name of at most 255 characters is required.')
    if sku is not None and (not isinstance(sku, str) or len(sku) > 150):
        raise ValidationError('Invalid product SKU.')
    if not isinstance(external_id, str) or not 0 < len(external_id) <= 255:
        raise ValidationError('A stable external product identifier is required.')
    price = attributes.get('price')
    if price is not None:
        try:
            price = Decimal(str(price))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError('Invalid product price.') from exc
        if not price.is_finite() or price < 0:
            raise ValidationError('Product price must be finite and nonnegative.')
    reference = ProductExternalReference.objects.select_related('product').filter(
        integration_connection=connection, external_product_id=external_id).first()
    if reference:
        product = reference.product
        if product.business_id != connection.business_id:
            raise ValidationError('External mapping crosses business boundaries.')
        prior = (reference.source_metadata or {}).get('source_at')
        if prior and parse_datetime(prior) and source_at <= parse_datetime(prior):
            return product, False
    else:
        product = Product(business_id=connection.business_id, created_at=confirmed_at, updated_at=confirmed_at)
    product.name, product.sku, product.price = name.strip(), sku, price
    product.currency = connection.business.currency
    product.updated_at = confirmed_at
    optional = [field for field in ('sku', 'price') if getattr(product, field) is None]
    product.full_clean(exclude=['description', 'category', 'inventory_quantity', 'image_url', 'source_metadata', *optional],
                       validate_unique=False, validate_constraints=False)
    product.save()
    metadata = {'source_at': source_at.isoformat(), 'is_mock': connection.is_mock}
    if reference:
        reference.source_metadata, reference.updated_at = metadata, confirmed_at
        reference.save(update_fields=['source_metadata', 'updated_at'])
    else:
        ProductExternalReference.objects.create(product=product, integration_connection=connection,
            external_product_id=external_id, external_sku=sku, source_metadata=metadata,
            created_at=confirmed_at, updated_at=confirmed_at)
    return product, True
