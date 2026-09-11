"""
Authoritative Business Intelligence and Analytics Calculations.
Deterministic calculations establish facts and metrics.
AI advisory never silently alters authoritative metrics.
"""
from decimal import Decimal
import datetime
import pytz


def calculate_net_revenue(gross_total: Decimal, refunds: Decimal = Decimal('0.00')) -> Decimal:
    """
    COR-004: Calculates authoritative Net Revenue.
    Rule: Net Revenue = Gross Total - Refunds.
    """
    gross = Decimal(str(gross_total))
    ref = Decimal(str(refunds)) if refunds is not None else Decimal('0.00')
    return max(Decimal('0.00'), gross - ref)
