# Business Intelligence and Business Graph: HTTP contract (state of branch `bi-graph-integration`)

Written 2026-11-10 from the code and from live calls against a worktree server. "Current" means what the branch does today. Rows marked **TARGET** are what the audit says the contract must become (see `AUDIT.md`); the frontend should code against the current shape and tolerate the TARGET shape.

## Base, auth and roles

- Base: `/api/businesses/<business_id>/intelligence/` and `/api/businesses/<business_id>/graph/` (also under `/api/v1/`).
- Through the Next.js proxy: `/api/backend/businesses/<id>/intelligence/...`. The proxy only forwards path segments matching `[a-zA-Z0-9_-]+` and always appends a trailing slash. Metric keys contain dots, so the proxy cannot carry `metrics/<key>/snapshots/` (open problem BIA-01).
- Session login: `POST /api/frontend/login/` (cookie session). Unsafe methods need the CSRF token.
- Anonymous: 403 `{"code":"NOT_AUTHENTICATED"|"FORBIDDEN","detail":...}`.
- Read (GET): any active member of the business (OWNER, MANAGER, OPERATOR, VIEWER). Write / pipeline / rebuild / snapshot create (POST, PATCH): OWNER or MANAGER. Superusers pass the check.
- A non-member always gets the same 403 whether the business exists or not. A caller-supplied `business_id` in query or body is ignored.
- Every error body is `{"code": "...", "detail": "..."}`; validation errors add `"fields": {...}`. Codes in use: `FORBIDDEN`, `NOT_AUTHENTICATED`, `NOT_FOUND`, `INVALID_DATA`, `PIPELINE_FAILED`.

## Business Intelligence

| Method and path | Role | Query / body | 200 body |
|---|---|---|---|
| GET `metrics/` | member | `limit` (1-200, default 50), `offset` | `{total_count, limit, offset, results:[{id, metric_key, name, category, unit, value_type}]}` (42 registry rows after the first pipeline run; the GET is read-only, so an unseeded business lists 0) |
| GET `metrics/<key>/snapshots/` | member | `period_type`, `dimension_type`, `limit`, `offset` | `{metric_key, total_count, limit, offset, results:[{id, value (string), period_type, period_start, period_end, dimension_type, dimension_value}]}`; 404 `NOT_FOUND` for unknown or foreign metric |
| GET `facts/` | member | `status`, `fact_type`, `limit`, `offset` | `{total_count, limit, offset, results:[{id, fact_type, statement, value, value_unit, confidence, status, rule_key, detected_at, evidence}]}`. Default list = VERIFIED facts valid **now**; closed-period facts need `?status=VERIFIED` (BI-06) |
| POST `facts/` | manager | `{statement, fact_type?, value?, value_unit?, rule_key?, evidence?}` | 201/200 `{id, fact_type, statement, status, created}` (upsert on type + rule_key; BI-09) |
| GET / PATCH `facts/<id>/` | member / manager | PATCH `{status, reason}` | detail incl. `valid_from`, `valid_to`; PATCH `{id, status, valid_to, updated_at}` |
| GET `issues/` | member | `status`, `severity`, `issue_type`, `limit`, `offset` | `{total_count, limit, offset, results:[{id, issue_type, title, description, severity, confidence, status, detected_at, resolved_at, metadata}]}` |
| POST `issues/` | manager | `{issue_type, title, description?, severity?, confidence?, rule_key?, fact_ids?, snapshot_ids?}` | 201/200 `{id, issue_type, title, status, created}` |
| GET / PATCH `issues/<id>/` | member / manager | PATCH `{status, notes}` | detail / `{id, status, resolved_at, updated_at}` |
| POST `pipeline/run/` | manager | none | `{business_id, relationships_reconciled:{created,updated,unchanged,invalidated}, quarantined_records, active_facts_count, open_issues_count, status:"COMPLETED"}`; if relationship reconciliation was rolled back: 500 `{code:"PIPELINE_FAILED", detail}`; conflicts 409 `{code:"CONFLICT"}` |

`pipeline/run/` reconciles relationships and seeds the 42-row metric registry. It does NOT compute metric snapshots (BIA-03). Snapshots, per business and period, come from the command `python manage.py run_intelligence --slug <slug> [--from D --to D --period-type T --attribution-model M --lookback-days N]` (default: current UTC month). Facts and issues are not derived automatically (the docs define no rule catalog); they come only from the POST endpoints.

Request validation (BI-07): malformed or non-object bodies, non-numeric `value`/`confidence`, `confidence` outside 0..1, non-object `evidence`, missing `statement`/`issue_type`/`title`, non-integer id lists give 400 `{code:"INVALID_DATA", detail, fields}`.

## Business Graph

| Method and path | Role | Query / body | 200 body |
|---|---|---|---|
| GET `traversal/` | member | `root_entity_type`, `root_entity_id` (required); `direction` OUTBOUND/INBOUND/BIDIRECTIONAL, `max_depth` (2, 0..5), `max_nodes` (100, 1..1000); filters below | `{business_id, root_node_id, depth_reached, truncated, node_count, edge_count, nodes:[{id, entity_type, entity_id, label, properties}], edges:[{id, source_node_id, target_node_id, relationship_type, confidence}]}` |
| GET `paths/` | member | `start_entity_type/id`, `end_entity_type/id` (required); `max_depth` (5, 1..5), `direction`, `explain` | `{business_id, paths_found, paths:[{length, nodes:[{id, entity_type, entity_id}], edges:[{id, relationship_type}], explanation?}]}` |
| GET `query/` | member | `entity_type`, `entity_id`, `relationship_type`, `limit` (100, 1..1000), filters | same shape as traversal |
| GET `journeys/customer/<id>/` | member | filters | `{business_id, customer_id, canonical_identity_id, node_count, edge_count, summary, timeline:[{entity_type, entity_id, label, stage, timestamp, properties}]}` |
| GET `journeys/order/<id>/` | member | filters | `{business_id, order_id, status, total_amount, customer_node_id, product_count, payment_count, shipment_count, timeline:[...]}` |
| GET `journeys/product/<id>/`, `journeys/campaign/<id>/` | member | filters | `{business_id, product_id|campaign_id, summary, timeline_length}` (summary only) |
| GET / POST `snapshots/` | member / manager | POST `{snapshot_type, name?, root_entity_type?, root_entity_id?, filters?}` | list is a bare array `[{id, name, snapshot_type, node_count, edge_count, generated_at}]`; POST 201 same row |
| GET `snapshots/<id>/` | member | | adds `filters`, `snapshot_data:{nodes, edges, timeline, summary}` |
| POST `rebuild/` | manager | `{"clean": true|false}` (JSON boolean) | `{business_id, nodes_created, nodes_updated, nodes_pruned, edges_created, edges_updated, edges_pruned, total_nodes, total_edges}` |

Out-of-range or non-integer numbers, malformed or offset-less datetimes, and non-object bodies give 400 `{code:"INVALID_DATA", detail}`; a missing or foreign entity gives 404 `{code:"NOT_FOUND"}`.

Filters (all optional, query string or `filters` object): `min_confidence`, `status`, `channel`, `provider`, `entity_types` (comma list), `relationship_types` (comma list), `time_from`, `time_to`, `valid_at` (ISO datetimes).

Edge types the graph can show (from the 23 BI relationship rules): `PLACED_ORDER, CONTAINS_PRODUCT, CONTAINS_VARIANT, HAS_PAYMENT, HAS_SHIPMENT, HAS_CONVERSATION, HAS_MESSAGE, HAS_CALL, HAS_VISITOR, HAS_SESSION, HAS_EVENT, HAS_WEBSITE_EVENT, REFERENCES_PRODUCT, REFERENCES_ORDER, HAS_REPORTED_CONVERSION, REPORTED_CUSTOMER, REPORTED_ORDER, REPORTED_SESSION`.

Order of operations for a fresh business: `POST intelligence/pipeline/run/` (writes relationships) then `POST graph/rebuild/` (projects nodes and edges). Journeys and traversals return errors until the rebuild has run (BG-04).

Entity types: `CUSTOMER, PRODUCT, PRODUCT_VARIANT, ORDER, PAYMENT, SHIPMENT, CAMPAIGN, CAMPAIGN_CONVERSION, WEBSITE_VISITOR, WEBSITE_SESSION, WEBSITE_EVENT, CONVERSATION, MESSAGE, CALL`.

## Not covered by this contract (UNAVAILABLE in the UI)

No endpoints for relationships, attribution, anomalies or calculation details exist; Overview KPI keys (`total_revenue`, ...) do not match BI registry keys (`bi.metric.<name>.v1`), so Overview KPIs stay UNAVAILABLE until a mapping exists.
