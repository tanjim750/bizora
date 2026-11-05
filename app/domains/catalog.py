"""Source-aware product intake assessment; shared SKU alone never proves identity."""
from app import models as m
from .common import authorize, ensure_owned, related, require, external_identifier

def assess_product(business, actor, payload, connection=None):
    authorize(actor, business, write=True)
    if connection is not None:
        ensure_owned(connection,business)
    require(isinstance(payload, dict), 'INVALID_DATA', 'Product payload must be an object.')
    ref = payload.get('external_reference', {})
    require(isinstance(ref, dict), 'INVALID_DATA', 'External reference must be an object.')
    external_id = external_identifier(ref['external_product_id']) if 'external_product_id' in ref else ''
    review = payload.get('deduplication')
    if review is not None:
        require(isinstance(review, dict) and set(review) == {'decision', 'reason'} and (review['decision'] == 'CREATE_DISTINCT') and isinstance(review['reason'], str) and review['reason'].strip(), 'INVALID_REVIEW', 'Distinct-product review requires decision CREATE_DISTINCT and an evidence reason.')
        authorize(actor, business, manager=True)
    if connection and external_id:
        mapped = m.ProductExternalReference.objects.filter(integration_connection=connection, external_product_id=external_id, external_variant_id__isnull=True).first()
        if mapped:
            ensure_owned(mapped, business)
        links = m.IdentityLink.objects.filter(status='ACTIVE', canonical_identity__business=business, canonical_identity__status='ACTIVE', canonical_identity__entity_type='PRODUCT', external_identity__business=business, external_identity__integration_connection=connection, external_identity__entity_type='PRODUCT', external_identity__external_id=external_id)
        ids = set(links.values_list('canonical_identity__entity_id', flat=True))
        require(len(ids) <= 1 and (not mapped or not ids or ids == {mapped.product_id}), 'IDENTITY_CONFLICT', 'Source reference and reviewed identity links contradict each other.')
        if mapped or ids:
            require(review is None, 'IDENTITY_CONFLICT', 'An authoritative source mapping already exists; it cannot create a distinct product.')
            product = related(m.Product, mapped.product_id if mapped else ids.pop(), business)
            return {'decision': 'REUSE', 'product_id': product.pk, 'rule': 'SOURCE_PRODUCT_REFERENCE' if mapped else 'REVIEWED_IDENTITY_LINK'}
    sku = payload.get('sku')
    require(sku is None or isinstance(sku, str), 'INVALID_IDENTIFIER', 'SKU must be text.')
    sku = sku.strip() if sku else None
    candidates = list(m.Product.objects.filter(business=business, sku=sku).values_list('pk', flat=True)) if sku else []
    if review is not None:
        return {'decision': 'CREATE', 'rule': 'AUTHORIZED_DISTINCT_PRODUCT', 'candidate_ids': candidates, 'reason': review['reason']}
    return {'decision': 'REVIEW' if candidates else 'CREATE', 'rule': 'SHARED_SKU_REVIEW' if candidates else 'NO_DETERMINISTIC_MATCH', 'candidate_ids': candidates}
