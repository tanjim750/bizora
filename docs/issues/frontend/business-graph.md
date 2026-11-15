# Business Graph: frontend issues

Backend counterpart: [`../backend/business-graph.md`](../backend/business-graph.md). Rules: frontend only (`frontend/**`, docs); never change backend code; record backend problems in the backend file; never push.

## Always apply
- Order of operations for a new business: `POST intelligence/pipeline/run/` then `POST graph/rebuild/`; send JSON booleans for `clean`.
- Respect caps: `max_depth` <= 5, `max_nodes` <= 1000, `limit` <= 1000; datetimes must carry a UTC offset.

## Items from the audit

| ID | Sev | Problem | What the frontend does |
|---|---|---|---|
| BGA-03 | high | Truncated traversal returns edges whose endpoint is not in `nodes` (`traverse_graph` appends the edge before the `max_nodes` check); journeys/snapshots reuse it. | Draw only edges whose `source_node_id` and `target_node_id` are in `nodes`; show a 'truncated' badge when `truncated` is true. |
| BGA-10 | medium | Shapes block drawing: traversal/path nodes lack `node_type`, timestamps, `canonical_identity_id`; path edges lack source/target (direction lost); customer/order journeys return no `nodes`/`edges`; product/campaign journeys are summaries only (spec §6, §8). | Do not assume `node_type`, timestamps or edge direction from traversal/path responses; derive labels from `entity_type`; journeys: use timeline only until the backend adds nodes/edges. |
| BGA-11 | medium | (BG-04) Journeys return 400 until `rebuild/` ran; traversal returns 404. | Treat a 400/409 'not projected / graph not built' on journeys as an empty state with a 'Rebuild graph' action for managers. |
| BGA-14 | medium | BUSINESS snapshot stores the whole graph as one JSON blob; no size/count caps; list unpaginated; `name` >255 accepted on SQLite (DataError on PostgreSQL). | Do not request BUSINESS snapshots for large tenants; paginate the list client-side meanwhile. |
| BGA-15 | low | Entity ids above bigint -> OverflowError; `explain=yes` silently false. | Validate ids client-side (positive integer, <= 2^63-1) before calling; send `explain=true`. |
| BGA-17 | low | Three graph implementations disagree: `graph-context/<kind>/<pk>/` uses SESSION/VISITOR vocabulary (`graph-context/session/5/` never finds a node) and `ensure_owned` per edge; `ai_context.assemble_graph_context` has its own BFS (no ordering, `valid_to__gte`); `services/graph.py` `safe_traverse` uses `queue.pop(0)` and nothing connects it to the DB graph. | Use `WEBSITE_SESSION` / `WEBSITE_VISITOR` for the graph endpoints; `graph-context` uses `SESSION` / `VISITOR`. |

## UI-found issues

_(none recorded yet; add rows: ID `FE-<DOMAIN>-NN`, severity, symptom, screen/route, fix.)_
