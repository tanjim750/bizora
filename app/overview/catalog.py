"""Display catalog only. BI owns the definitions, units, calculations and snapshots."""
DOMAINS = ('sales', 'customers', 'marketing', 'website', 'support', 'delivery', 'payments')
METRICS = {
    'sales': ('total_revenue', 'realized_revenue', 'revenue_growth', 'order_count', 'average_order_value',
              'completed_orders', 'cancelled_orders'),
    'payments': ('refunded_revenue', 'successful_payments', 'failed_payments'),
    'customers': ('new_customers', 'repeat_customers', 'repeat_purchase_rate', 'purchase_frequency'),
    'marketing': ('marketing_spend', 'marketing_conversions', 'ctr', 'cpc', 'roas', 'attributable_revenue'),
    'website': ('website_sessions', 'website_visitors', 'website_conversion_rate', 'cart_abandonment_rate',
                'checkout_completion_rate'),
    'support': ('conversation_count', 'unresolved_conversations', 'response_time', 'resolution_time', 'escalations'),
    'delivery': ('delivery_success_rate', 'delivery_failure_rate', 'return_rate', 'average_delivery_time'),
}
CATALOG = {key: domain for domain, keys in METRICS.items() for key in keys}
DEFAULT_KPIS = ['total_revenue', 'realized_revenue', 'order_count', 'new_customers', 'marketing_spend',
                'website_conversion_rate', 'unresolved_conversations', 'delivery_failure_rate', 'refunded_revenue']
CROSS_DOMAIN = {
    'marketing_revenue': ('marketing', 'sales'),
    'marketing_delivery': ('marketing', 'delivery'),
    'website_sales': ('website', 'sales'),
    'product_support': ('sales', 'support'),
    'product_delivery': ('sales', 'delivery'),
    'customer_retention': ('customers',),
    'support_customer_outcome': ('support', 'customers'),
    'courier_revenue': ('delivery', 'sales'),
    'campaign_customer_quality': ('marketing', 'customers'),
}
ENTITY_DOMAINS = {'product': 'sales', 'product_variant': 'sales', 'order': 'sales', 'customer': 'customers',
                  'campaign': 'marketing', 'conversation': 'support', 'shipment': 'delivery', 'courier': 'delivery',
                  'payment': 'payments', 'refund': 'payments', 'website_session': 'website', 'website_visitor': 'website'}
ACTIVE_ISSUES = ('OPEN', 'NEW', 'ACKNOWLEDGED', 'ONGOING', 'IN_PROGRESS')
ISSUE_STATUSES = ACTIVE_ISSUES + ('RESOLVED', 'DISMISSED')
ACTIVE_RECOMMENDATIONS = ('SUGGESTED', 'UNDER_REVIEW', 'APPROVED')
RECOMMENDATION_STATUSES = ACTIVE_RECOMMENDATIONS + ('REJECTED', 'EXECUTED', 'ACTIONED', 'COMPLETED', 'EXPIRED', 'DISMISSED')
SEVERITIES = ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')


def domain_for(metric):
    category = metric.category.lower()
    aliases = {'revenue': 'sales', 'orders': 'sales', 'order': 'sales', 'customer': 'customers', 'payment': 'payments'}
    return aliases.get(category, category) if aliases.get(category, category) in DOMAINS else CATALOG.get(metric.key)
