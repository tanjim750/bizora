"""Explicit conservative transition policy. No arbitrary status overwrite."""
TRANSITIONS = {
 'orders': {
  'PENDING': {'CONFIRMED', 'CANCELLED'}, 'CONFIRMED': {'PROCESSING', 'CANCELLED'},
  'PROCESSING': {'SHIPPED', 'CANCELLED'}, 'SHIPPED': {'DELIVERED', 'RETURNED'},
  'DELIVERED': {'RETURNED', 'REFUNDED'}, 'RETURNED': {'REFUNDED'}, 'CANCELLED': set(), 'REFUNDED': set()},
 'payments': {'PENDING': {'AUTHORIZED', 'PAID', 'FAILED', 'CANCELLED'},
              'AUTHORIZED': {'PAID', 'FAILED', 'CANCELLED'}, 'PAID': set(),
              'FAILED': set(), 'CANCELLED': set(), 'PARTIALLY_REFUNDED': set(), 'REFUNDED': set()},
 'conversations': {'OPEN': {'PENDING', 'RESOLVED', 'CLOSED'}, 'PENDING': {'OPEN', 'RESOLVED', 'CLOSED'},
                   'RESOLVED': {'OPEN', 'CLOSED'}, 'CLOSED': {'OPEN'}},
 'shipments': {'PENDING': {'SUBMITTED', 'CANCELLED'}, 'SUBMITTED': {'PICKED_UP', 'CANCELLED'},
               'PICKED_UP': {'IN_TRANSIT', 'RETURNING'}, 'IN_TRANSIT': {'OUT_FOR_DELIVERY', 'FAILED', 'RETURNING'},
               'OUT_FOR_DELIVERY': {'DELIVERED', 'FAILED', 'RETURNING'},
               'FAILED': {'OUT_FOR_DELIVERY', 'RETURNING'}, 'RETURNING': {'RETURNED'},
               'DELIVERED': set(), 'RETURNED': set(), 'CANCELLED': set()},
 'calls': {'INITIATED': {'RINGING', 'FAILED', 'CANCELLED'},
           'RINGING': {'ANSWERED', 'MISSED', 'BUSY', 'FAILED', 'CANCELLED'},
           'ANSWERED': {'COMPLETED', 'FAILED'}, 'COMPLETED': set(), 'MISSED': set(),
           'BUSY': set(), 'FAILED': set(), 'CANCELLED': set()},
 'messages': {'PENDING': {'SENT', 'FAILED'}, 'SENT': {'DELIVERED', 'FAILED'},
              'DELIVERED': set(), 'FAILED': set()},
 'customers': {'ACTIVE': {'INACTIVE', 'BLOCKED'}, 'INACTIVE': {'ACTIVE', 'BLOCKED'}, 'BLOCKED': {'ACTIVE'}},
 'products': {'ACTIVE': {'INACTIVE', 'ARCHIVED'}, 'INACTIVE': {'ACTIVE', 'ARCHIVED'}, 'ARCHIVED': {'ACTIVE'}},
 'variants': {'ACTIVE': {'INACTIVE', 'ARCHIVED'}, 'INACTIVE': {'ACTIVE', 'ARCHIVED'}, 'ARCHIVED': {'ACTIVE'}},
 'campaigns': {'ACTIVE': {'PAUSED', 'COMPLETED'}, 'PAUSED': {'ACTIVE', 'COMPLETED'}, 'COMPLETED': set()},
 'callbacks': {'PENDING': {'COMPLETED', 'CANCELLED'}, 'COMPLETED': set(), 'CANCELLED': set()},
}

# Explicit adapter aliases are deliberately small; unknown values fail closed.
ALIASES = {'orders': {'ON-HOLD': 'PENDING'}, 'payments': {'SUCCEEDED': 'PAID'},
           'calls': {'CANCELED': 'CANCELLED'}, 'shipments': {'CANCELED': 'CANCELLED'}}
