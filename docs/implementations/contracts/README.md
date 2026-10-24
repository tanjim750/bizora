# Bizora domain contracts v1

These are process-local adapters and authenticated canonical HTTP interfaces, not live providers.
Executable definitions: `app/domains/boundaries.py`, `contracts.py`, `merge.py`,
`mock_transport.py`, `catalog.py`. Examples: [examples.json](examples.json).

## Common external-owner envelope

`boundaries.exchange(business, actor, owner, capability, payload, request_id, adapter=None)`
accepts an already authenticated Django user. Membership is always checked. Merge preparation
requires MANAGER/OWNER. Outbound preparation also runs the existing OPERATOR-or-higher service.
A client cannot choose an adapter class, business context, credentials or merge acknowledgement.

Input to an adapter (all six fields required):

```json
{"version":"bizora.domain.v1","business_id":42,"owner":"Monitoring",
 "capability":"freshness","request_id":"freshness-orders-1","payload":{"resource":"orders"}}
```

Output must echo version, business_id, owner, capability and request_id exactly, and add:

- `status`: required `AVAILABLE`, `UNAVAILABLE` or `REJECTED`.
- `simulated`: required boolean, always true for a fixture adapter.
- `result`: required object for AVAILABLE; null is used for unavailable. Optional `reason` explains unavailability.
- Result shape per owner is listed below. Extra output fields are additive within v1.
  Recognized nested `business_id` and typed `entity_type`/`entity_id` references are checked.
  Owner-specific opaque content/provenance remains the adapter owner's responsibility; this
  is not automatic verification of every analytical claim or arbitrary embedded identifier.

With no configured adapter, the boundary returns explicit UNAVAILABLE. Timeouts/connection failures become UNAVAILABLE without
exposing exception details. Wrong version/scope/request identity raises `CONTRACT_MISMATCH`;
invalid fields/schema/provenance raise `INVALID_CONTRACT` or a more specific validation code.
HTTP error shape is `{code, detail}`; validation 400, permission 403, inaccessible business 404.
Transport unavailability is a successful contract response with `status=UNAVAILABLE`, not a fake result.

Every required payload string is nonempty, at most 2000 characters. IDs are positive integers,
not booleans. Request ID is nonempty text, max 180. JSON must be finite; result nesting is bounded
at 20 levels and arrays at 1000 entries. Return cursors/continuations in additive fields for larger
owner results; callers must not infer that a partial owner result is a complete analysis.

## Seven owner schemas

| Owner / HTTP slug | Capability | Required caller payload | Required AVAILABLE result fields | Absent behavior |
| --- | --- | --- | --- | --- |
| Integrations / `integrations` | `prepare_operation` | `operation`, `entity_type`, `entity_id` | `request` object; `execution` exactly `NOT_EXECUTED` | No third-party transport or provider success |
| Business Intelligence / `bi` | `entity_context` | `entity_type`, `entity_id` | `facts`, `metrics`, `issues`, `evidence` arrays | No local analytics/attribution/issue generation |
| Business Graph / `graph` | `entity_context` | `entity_type`, `entity_id` | `nodes`, `edges` arrays | No graph construction/full traversal |
| AI Intelligence / `ai` | `entity_context` | `entity_type`, `entity_id` | `recommendations`, `answers`, `evidence` arrays | No locally generated advice, answers or summaries |
| Business Memory / `memory` | `policy_context` | `query` | `policies` array | No inferred business policy |
| Configuration / `configuration` | `policy` | `policy_key` | `policy` object | No invented SLA/routing/escalation threshold |
| Monitoring / `monitoring` | `freshness` | `resource` | `freshness` object | No invented sync/health/freshness result |

Optional input context can include canonical typed entity references; those are tenant-validated.
Array item contents, policy schemas, analytical dimensions, timestamps and provenance need an owner-
approved additive schema before production use. v1 deliberately validates the shared transport envelope
and minimum result containers; it is not a replacement for all downstream domain models.
Integrations is stricter: caller keys are exactly the three above; operation/type must match
`SHIPMENT_SUBMIT|SHIPMENT_CANCEL` / `SHIPMENT`, `CALL_INITIATE` / `CALL`, or
`MESSAGE_SEND` / `MESSAGE`. The local service replaces caller input with the canonical prepared
request before calling an adapter, preserving ownership, connection and state validation.

HTTP seam: `POST /api/businesses/{id}/contracts/{owner-slug}/{capability}/` with
`{"request_id":"stable-client-id","payload":{...}}`. Session writes require CSRF; Basic auth is
supported for localhost/HTTPS. Direct HTTP `prepare_merge` is forbidden; use the merge endpoint.

Owner reads are side-effect-free by this contract. `request_id` is a correlation/replay token;
this layer does not persist a delivery/execution receipt. Adapters must preserve read semantics,
and must not execute business/provider actions through this read/preparation interface.

## Team-lead adapter wiring

Implement `exchange(envelope: dict) -> dict`. Configure trusted server-side dotted class paths:

```python
BIZORA_DOMAIN_ADAPTERS = {
    "Business Intelligence": "your_bi.adapters.EntityContextAdapter",
    "Monitoring": "your_monitoring.adapters.FreshnessAdapter",
}
```

Classes are constructed without arguments; their own domain owns safe configuration, transport,
credentials and bounded timeouts. No such real adapter is shipped or enabled here. Operational
record detail pages consume configured owner context through `operations_ui.owner_context`.
Existing canonical projections still read existing ORM records; no duplicate records are stored.
The final frontend can call the same authenticated contract endpoint directly.

`FixtureAdapter(result, status)` is injected in unit tests; it always marks output simulated.
A configured fixture class additionally requires `BIZORA_ALLOW_FIXTURE_ADAPTERS=True` in isolated
local/test settings. Production must leave this disabled. Never register a fixture as a live provider.

Compatibility: clients must tolerate additive optional fields. Changing/removing required fields,
status semantics or ownership requires a new major contract version. Unknown versions fail closed.
No automatic downgrade silently changes a major version.

## Canonical inbound / outbound integration boundary

`data.ingest(business, actor, resource, data, key, occurred_at=None, connection_id=None)` owns
canonical normalization, relationships, money, deduplication and transactional receipt handling.
Provider adapters own transport/signatures/status mapping and pass an explicit connected source.
The canonical API envelope is `{data, connection_id?, occurred_at?}` with `Idempotency-Key` header.
The authenticated API is not a public provider webhook. Extra fields/server-managed fields fail.

`MockCanonicalTransport.receive` accepts `bizora.ingest.v1` envelopes:
required version/business_id/connection_id/event_id/resource/data; optional offset-aware occurred_at.
It requires an explicitly simulated owned connection. It returns `{version, simulated:true, created,
record}` after real canonical processing. Product/customer raw-provider examples also exist in
`MockCommerceTransport`; `MockMessageTransport` is explicitly simulated outbound acceptance.

Receipts scope the event ID by business/connection, hash the payload, and reject changed reuse.
Replay preserves canonical IDs. A new event ID is not permission to duplicate an external entity.
Older observations cannot overwrite newer canonical state. There is no network or credential use.

`prepare_operation` and `POST operations/{operation}/{id}/prepare/` return `bizora.outbound.v1`,
UNAVAILABLE, NOT_EXECUTED, and an owned canonical `request` containing operation/business_id/
connection_id/entity_type/entity_id/payload. Request data overrides are forbidden. Calls/messages/
shipments must be in preparable states. Preparing is read-only and does not constitute provider
acceptance. Integrations must add durable execution/retry/delivery receipts in its own domain;
this branch provides no guarantee of exactly-once delivery to an external provider.

Product intake preflight: `POST products/assess/` with the canonical envelope returns CREATE,
REUSE or REVIEW. A shared SKU requires review; reviewed source identity links can reuse a canonical
product. `deduplication:{decision:"CREATE_DISTINCT",reason:"review evidence"}` requires a manager.
Existing source mappings cannot be overridden by that flag. SKU is case-sensitive and trimmed.

## Merge preparation, never execution

`merge.plan` / `merge.dry_run`, and
`POST identity/merge-candidates/{candidate_id}/dry-run/` implement `bizora.merge.v1`.
MANAGER/OWNER only. Optional `expected_fingerprint` detects stale reviewed plans. Candidate must
have distinct same-type canonical entities; approval/active state/tenant graph violations appear
as safety errors. The plan enumerates actual ORM foreign keys, known typed polymorphic fields,
canonical identity references and source receipt mappings with model/table/path/count/digest.
Both identities and affected records contribute to the deterministic fingerprint. Arbitrary JSON,
provider metadata and external stores cannot be exhaustively discovered by this ORM inventory.

All seven owners receive `prepare_merge`. Required payload: plan_id, fingerprint,
source_identity_id, target_identity_id; the full inventory also travels with it. AVAILABLE ack:

```json
{"fingerprint":"exact-reviewed-plan-hash","decision":"PREPARED",
 "preserves_relationships":true,"notes":"Owner-reviewed reconciliation plan"}
```

A rejected decision or false preservation flag blocks readiness. Missing adapters remain
WAITING_FOR_OWNERS; unsafe plan is UNSAFE; fixture success is SIMULATED_PREPARED. Real unanimous
acks yield PREPARED_REQUIRES_EXECUTOR_REVIEW, never execution permission. A changed local
inventory during reconciliation is rejected as STALE_PLAN. Ack results are not persisted leases
or atomic cross-service guarantees. Preparing must not mutate owned records.

`identity.execute_merge` still refuses physical consolidation with BI_GRAPH_AI_MERGE_CONTRACT.
A future reviewed executor needs durable/expiring owner acknowledgements, JSON/reference
preservation, transaction/failure/retry semantics, downstream redirects/reprojection and audit
preservation. No rollback, deletion, reparenting or fake MERGED history is performed here.

## Evidence

`app/test_integration_readiness.py`: ExternalBoundaryContractTests, AdapterConfigurationTests,
MergeReadinessTests, SourceContradictionAndMergeRaceTests, ProductIntakeReviewTests,
FinalCorrectnessTests, OwnerUIConnectionTests and UI workflow/security tests.
`app/test_domains.py:PostgresConcurrencyTests` includes concurrent canonical SKU intake.
