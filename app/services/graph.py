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
    if start_node not in graph or max_depth < 0:
        return []
    seen = set(visited or ())
    queue = [(start_node, 0)]
    result = []
    while queue:
        node, depth = queue.pop(0)
        if node in seen or depth > max_depth:
            continue
        seen.add(node)
        result.append(node)
        if depth < max_depth:
            queue.extend((neighbor, depth + 1) for neighbor in graph.successors(node))
    return result
