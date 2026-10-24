"""Explicit allowlist of owned resources. No arbitrary Django model CRUD."""
from app import models as m

# resource -> (model, business lookup, source identifier)
RESOURCES = {
    'product-images': (m.ProductImage, 'product__business_id', 'url'),
    'products': (m.Product, 'business_id', None),
    'product-references': (m.ProductExternalReference, 'product__business_id', 'external_product_id'),
    'customer-references': (m.CustomerExternalReference, 'customer__business_id', 'external_customer_id'),
    'variants': (m.ProductVariant, 'product__business_id', None),
    'customers': (m.Customer, 'business_id', None),
    'contacts': (m.CustomerContact, 'customer__business_id', None),
    'tags': (m.CustomerTag, 'customer__business_id', None),
    'orders': (m.Order, 'business_id', 'external_order_id'),
    'payments': (m.Payment, 'business_id', 'external_payment_id'),
    'refunds': (m.Refund, 'payment__business_id', 'external_refund_id'),
    'conversations': (m.Conversation, 'business_id', 'external_conversation_id'),
    'participants': (m.ConversationParticipant, 'conversation__business_id', None),
    'messages': (m.Message, 'conversation__business_id', 'external_message_id'),
    'attachments': (m.MessageAttachment, 'message__conversation__business_id', None),
    'notes': (m.ConversationNote, 'conversation__business_id', None),
    'campaigns': (m.Campaign, 'business_id', 'external_campaign_id'),
    'campaign-metrics': (m.CampaignMetric, 'campaign__business_id', None),
    'conversions': (m.CampaignConversion, 'campaign__business_id', 'external_conversion_id'),
    'ad-accounts': (m.AdAccount, 'business_id', 'external_account_id'),
    'ad-sets': (m.CampaignAdSet, 'campaign__business_id', 'external_id'),
    'creatives': (m.CampaignCreative, 'business_id', 'external_id'),
    'ads': (m.CampaignAd, 'ad_set__campaign__business_id', 'external_id'),
    'visitors': (m.WebsiteVisitor, 'business_id', 'visitor_key'),
    'sessions': (m.WebsiteSession, 'business_id', 'external_session_id'),
    'website-events': (m.WebsiteEvent, 'session__business_id', None),
    'shipments': (m.Shipment, 'business_id', 'external_shipment_id'),
    'shipment-events': (m.ShipmentEvent, 'shipment__business_id', None),
    'calls': (m.Call, 'business_id', 'external_call_id'),
    'call-events': (m.CallEvent, 'call__business_id', None),
    'transcripts': (m.CallTranscript, 'call__business_id', None),
    'callbacks': (m.CallbackRequest, 'business_id', None),
}


def resource(name):
    from .common import require
    require(name in RESOURCES, 'NOT_FOUND', 'Unknown resource.')
    return RESOURCES[name]


def scoped(name, business):
    model, lookup, _ = resource(name)
    return model.objects.filter(**{lookup: business.pk})


# Canonical field names are the provider-independent input contract. Provider adapters
# translate their raw schemas before calling ingest; raw schemas never enter queries.
READ_ONLY = {'id', 'business', 'created_at', 'updated_at', 'total_amount', 'subtotal',
             'normalized_value', 'ai_handover_state', 'last_message_at', 'resolved_at',
             'author_type', 'author_id', 'is_ai_generated', 'is_verified'}
NESTED = {'products': {'variants', 'external_reference', 'deduplication'},
          'customers': {'contacts', 'tags', 'external_reference'}, 'orders': {'items'},
          'messages': {'attachments'}}
