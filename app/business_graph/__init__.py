"""Business Graph domain: canonical graph nodes, relationship edges, and journey projections."""

from . import projection
from .projection import (
    GraphCrossBusinessError,
    GraphScopeError,
    GraphValidationError,
    ProjectionSummary,
    SUPPORTED_ENTITY_MODELS,
    SUPPORTED_RELATIONSHIP_RULES,
    VALID_RELATIONSHIP_SOURCES,
    project_business_graph,
    project_entity_node,
    project_relationship_edge,
)

__all__ = [
    "GraphCrossBusinessError",
    "GraphScopeError",
    "GraphValidationError",
    "ProjectionSummary",
    "SUPPORTED_ENTITY_MODELS",
    "SUPPORTED_RELATIONSHIP_RULES",
    "VALID_RELATIONSHIP_SOURCES",
    "project_business_graph",
    "project_entity_node",
    "project_relationship_edge",
    "projection",
]
