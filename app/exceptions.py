"""
Domain Exceptions for Business Memory & Knowledge and AI Intelligence.
Strictly enforce architectural invariants, governance gates, and tenant isolation.
"""


class DomainBoundaryViolationError(Exception):
    """
    Raised when raw transactional events, webhook payloads, or live BI calculated metrics
    are inappropriately submitted to Business Memory.
    """


class TenantIsolationError(Exception):
    """
    Raised when an operation lacks a non-null business_id or attempts cross-tenant data access.
    """


class UnapprovedMemoryPromotionError(Exception):
    """
    Raised when an unapproved AI recommendation or suggestion attempts to enter durable Business Memory
    or active retrieval indexes without passing an explicit human approval gate.
    """


class StaleVersionError(Exception):
    """
    Raised when an operation attempts to retrieve, index, or ground on superseded or historical
    versions as active context.
    """


class EmbeddingDimensionMismatchError(Exception):
    """
    Raised when embedding vector dimensions do not match the expected dimensionality of the configured model.
    """
