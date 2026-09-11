"""
Authoritative Business Knowledge Graph Service.
Uses NetworkX MultiDiGraph to preserve parallel multi-relationships between entities,
and provides cycle-safe, depth-bounded graph traversals.
"""

import networkx as nx


def create_business_graph() -> nx.MultiDiGraph:
    """
    COR-012: Returns a directed multigraph (MultiDiGraph) capable of preserving
    multiple parallel directed relationships between identical entity nodes
    (e.g., PLACED, PAID_FOR, RETURNED).
    """
    return nx.MultiDiGraph()


def safe_traverse(
    graph: nx.DiGraph,
    start_node: str,
    max_depth: int = 5,
    visited: set[str] | None = None,
) -> list[str]:
    """
    MOD-005: Cycle-safe, depth-bounded graph traversal algorithm.
    Guarantees each node is visited at most once and traversal terminates
    cleanly on cyclic graphs.
    """
    if visited is None:
        visited = set()

    if start_node in visited or max_depth < 0:
        return []

    visited.add(start_node)
    result = [start_node]

    if max_depth == 0:
        return result

    for neighbor in graph.successors(start_node):
        if neighbor not in visited:
            result.extend(safe_traverse(graph, neighbor, max_depth - 1, visited))

    return result
