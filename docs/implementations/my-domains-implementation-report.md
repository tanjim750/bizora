# Bizora — implementation and requirements evidence

24 October 2026 · `feat/business-domains` · backend continuation report.

## Outcome and audit scope

**This is a reviewable backend increment, not completion of all 298 documented requirements.**
The [exhaustive audit](my-domains-requirements-audit.md) covers all **298 subfeatures / 31 groups**;
its [JSON inventory](domain-requirements-audit.json) preserves every original name, description,
source line, status, A/B/C classification, implementation symbols and integration-test references.
The exact original filenames are `business-data.md`, `identity-resulation.md` and
`business-oparations.md` under `docs/implementations/features/` (spelling preserved).

Current full-requirement assessment: **149 COMPLETE, 146 PARTIAL, 3 BLOCKED, 0 NOT STARTED**.
A backend reader or an unavailable contract does not complete an operational screen. All
screen-oriented requirements with no frontend remain PARTIAL, even when their APIs work.
No new frontend framework, provider transport, BI calculator or AI engine was introduced.
No requirement is inferred from an unrelated domain's desired feature list.

Categories describe responsibility, not success: **A 223**, **B 69**, **C 6** total rows.
Of unfinished rows, **A 74**, **B 69**, **C 6**. Category C includes three PARTIAL lifecycle
requirements whose missing MERGED outcome depends on the three blocked merge requirements.
Passing tests validate the exercised behavior, not all prose in all requirements. The audit's
per-group integration references are explicitly distinguished from individual acceptance tests.

## Already implemented before this continuation

The baseline full suite contained 131 tests (SQLite 129 pass / 2 PG skips; PostgreSQL 130 pass /
1 local-demo skip). Existing code already provided authenticated membership/roles, source-scoped
replay receipts, canonical intake and lifecycle commands, immutable order snapshots and Decimal
totals, reserved/full/partial refunds, contacts/tags/external references, product images and
variants, conversations/messages/attachments/notes, support assignment/handover, campaign
hierarchy/raw metrics/conversion inputs, visitors/sessions/events, shipments/calls/transcripts,
deterministic exact identity resolution, anonymous purchase recovery, merge review and bounded
operational projections. These systems were extended rather than replaced.

Some previously PARTIAL checklist rows are now assessed COMPLETE because the existing executable
behavior already satisfied their documented canonical contract. That reassessment is not counted
as a newly implemented feature. In particular, source-provided call transcription/summary storage
was already implemented; those Business Data requirements do not require a local AI generator.
The prior report's suggested order amendments, a general scoring engine and automatic callback
execution are not silently promoted into requirements of these three specifications.

## Architecture and source of truth

- Python 3.11.17, Django 4.2.27, DRF 3.15.2, psycopg 3.2.9; pip/`requirements.txt` remains unchanged.
  No frontend application/build system exists. Dockerfile Python 3.12 was not separately tested.
- One Django app owns the runtime ORM in `app/models.py`; unchanged `0001_initial.py` is the baseline.
  `db_diagram.sql` is an alternative design, not an executable replacement schema.
- `app/domains/data.py` owns canonical records; `identity.py` links identities without owning duplicate
  business records; `operations.py` handles authorized commands; `projections.py` composes existing data.
  `contracts.py` reads authoritative external outputs and prepares non-executing requests;
  `queries.py` adds reusable canonical lookup/search.
- DRF routes -> typed envelopes -> membership/role checks -> transactional services -> existing ORM.
  HTTP intake is authenticated operational intake, not a public provider webhook. Integrations must
  translate/signature-check provider payloads before invoking the canonical boundary.
- `BusinessMembership` grants VIEWER reads, OPERATOR canonical/support writes, MANAGER/OWNER identity
  and action review. A Django superuser without membership has no tenant bypass. Basic/session auth
  and session-write CSRF protection are exercised by existing regression tests.
- PostgreSQL business-row locks serialize mutations within one business; DB uniqueness remains the
  final guard. SQLite tests do not validate row locks or multi-writer deployment behavior.
- Receipt keys are business/connection scoped and payload-hashed; replay is idempotent, changed payloads
  under one key fail, stale observations cannot overwrite newer state. Canonical snapshots stay immutable.
- Money is finite nonnegative Decimal with two fractional digits; refunds reserve capacity and derive
  payment refund states. There is no invented FX conversion, revenue recognition or BI attribution.
- Polymorphic entity references and FK ancestry are validated through `common.ensure_owned` at the
  new trust boundaries. Existing independently written data still needs reviewed cleanup/preflight;
  Django foreign keys alone do not prove tenant consistency.
- Persisted evidence must be current and tenant-safe; foreign/expired evidence cannot authorize an AI
  action. No network calls occur in the added services. Provider config/raw metadata/recording URLs
  remain excluded from normal canonical representations.
- Bounded context sections cap at 50 with count/truncation. Paginated resource endpoints provide the
  rest. `safe_records` performs recursive per-record checks; large production datasets need query and
  index profiling. It is correctness-focused, not a benchmarked high-volume graph engine.

সহজ বাংলায়: Business Data হলো মূল রেকর্ডের মালিক—একটি order-এর আরেকটি copy বানানো হয় না।
Identity একই customer-এর বিভিন্ন platform ID-কে প্রমাণসহ যুক্ত করে। Operations সেই মূল রেকর্ড
থেকে inbox, history ও context তৈরি করে। BI/Graph/AI-এর ফল না থাকলে API স্পষ্টভাবে unavailable বলে;
অনুমান করে revenue, identity match বা AI উত্তর তৈরি করে না। Transaction মানে একটি command-এর
সব পরিবর্তন একসঙ্গে সফল হবে, অথবা সব বাতিল হবে।

## New implementation and executable evidence

The continuation adds **64 tests**, taking discovery from 131 to 195, including two additional
real PostgreSQL race tests. The table cites actual implementation symbols and individual tests.

| Capability added or hardened | Implementation | New executable evidence |
| --- | --- | --- |
| Strict scalar/boolean/FK ancestry and source-parent validation; legitimate commerce/payment/courier sources remain independent | [`app/domains/data.py:ingest`](../../app/domains/data.py#L95) | [`app/test_domain_completion.py:CanonicalCompletionTests.test_scalar_and_boolean_shape_validation`](../../app/test_domain_completion.py#L25)<br>[`app/test_domain_completion.py:CanonicalCompletionTests.test_transition_rejects_corrupt_legacy_customer_reference`](../../app/test_domain_completion.py#L15)<br>[`app/test_domain_completion.py:CrossSourceAndQueueContractTests.test_payment_courier_and_call_may_use_different_source_from_commerce`](../../app/test_domain_completion.py#L467) |
| Payment method normalization, inherited payment/refund currency, refund-state ledger enforcement and transition timestamps | [`app/domains/data.py:transition`](../../app/domains/data.py#L430) | [`app/test_domain_completion.py:CanonicalCompletionTests.test_payment_method_normalization`](../../app/test_domain_completion.py#L50)<br>[`app/test_domain_completion.py:CanonicalCompletionTests.test_refund_state_cannot_be_imported_without_ledger`](../../app/test_domain_completion.py#L59)<br>[`app/test_domain_completion.py:CanonicalCompletionTests.test_refund_currency_inherits_payment_currency`](../../app/test_domain_completion.py#L64)<br>[`app/test_domain_completion.py:CanonicalCompletionTests.test_shipment_completion_and_refund_transition_timestamps`](../../app/test_domain_completion.py#L73)<br>[`app/test_domain_completion.py:CanonicalCompletionTests.test_call_answer_and_end_timestamps`](../../app/test_domain_completion.py#L86) |
| Location messages with validated coordinates, primary image URL safety, website performance/experience inputs and conversion/customer continuity | [`app/domains/data.py:ingest`](../../app/domains/data.py#L95) | [`app/test_domain_completion.py:DocumentedRepresentationTests.test_location_message_has_validated_canonical_coordinates`](../../app/test_domain_completion.py#L550)<br>[`app/test_domain_completion.py:CanonicalCompletionTests.test_performance_and_experience_signal_contracts`](../../app/test_domain_completion.py#L94)<br>[`app/test_domain_completion.py:CallbackAndConversionTests.test_primary_product_url_cannot_contain_executable_scheme`](../../app/test_domain_completion.py#L616)<br>[`app/test_domain_completion.py:CallbackAndConversionTests.test_conversion_session_customer_cannot_disagree_with_order`](../../app/test_domain_completion.py#L599) |
| Variant replay/upsert by parent+SKU, nested variant edits, DB uniqueness; optional verified product-SKU matching and review-only candidates | [`app/domains/identity.py:resolve`](../../app/domains/identity.py#L121) | [`app/test_domain_completion.py:ProductDeduplicationTests.test_variant_reobservation_upserts_by_parent_sku`](../../app/test_domain_completion.py#L371)<br>[`app/test_domain_completion.py:ProductDeduplicationTests.test_nested_source_variant_replay_updates_without_duplicates`](../../app/test_domain_completion.py#L378)<br>[`app/test_domain_completion.py:ProductDeduplicationTests.test_verified_sku_rule_is_opt_in_and_rejects_ambiguity`](../../app/test_domain_completion.py#L388)<br>[`app/test_domain_completion.py:ProductDeduplicationTests.test_product_merge_candidates_remain_review_only`](../../app/test_domain_completion.py#L401)<br>[`app/test_domain_completion.py:ProductDeduplicationTests.test_variant_sku_database_constraint`](../../app/test_domain_completion.py#L410) |
| Canonical identity availability lifecycle and invalidation; reviewed external metadata/seen-time enrichment; opaque provider user identifiers | [`app/domains/identity.py:set_status`](../../app/domains/identity.py#L334) | [`app/test_domain_completion.py:IdentityCompletionTests.test_identity_availability_lifecycle_and_history`](../../app/test_domain_completion.py#L128)<br>[`app/test_domain_completion.py:IdentityCompletionTests.test_status_change_cannot_fake_merge_or_bypass_permissions`](../../app/test_domain_completion.py#L140)<br>[`app/test_domain_completion.py:IdentityCompletionTests.test_external_enrichment_tracks_seen_bounds_and_verified_review`](../../app/test_domain_completion.py#L146)<br>[`app/test_domain_completion.py:IdentityCompletionTests.test_provider_user_identifiers_are_preserved_without_contact_matching`](../../app/test_domain_completion.py#L114) |
| Atomic corroboration of independent verified customer identifiers; contradictory/incomplete batches leave no partial links | [`app/domains/identity.py:resolve_many`](../../app/domains/identity.py#L381) | [`app/test_domain_completion.py:IdentityCompletionTests.test_multiple_verified_identifiers_resolve_atomically`](../../app/test_domain_completion.py#L159)<br>[`app/test_domain_completion.py:IdentityCompletionTests.test_contradictory_multi_field_evidence_creates_no_new_links`](../../app/test_domain_completion.py#L167)<br>[`app/test_domain_completion.py:IdentityCompletionTests.test_insufficient_multi_field_evidence_rolls_back_partial_match`](../../app/test_domain_completion.py#L177) |
| Explicit invalid-link scan/review, deterministic conflict severity and filtered identity history | [`app/domains/identity.py:validate_links`](../../app/domains/identity.py#L421) | [`app/test_domain_completion.py:IdentityCompletionTests.test_invalid_link_review_is_idempotent`](../../app/test_domain_completion.py#L183)<br>[`app/test_domain_completion.py:PersistedGraphContractTests.test_identity_history_is_filterable_within_business`](../../app/test_domain_completion.py#L456) |
| Verified login/signup/form journey recovery, chronological original-time customer timeline backfill, known visitor re-observation | [`app/domains/identity.py:link_anonymous`](../../app/domains/identity.py#L190) | [`app/test_domain_completion.py:IdentityCompletionTests.test_login_and_form_recovery_require_verified_matching_identity`](../../app/test_domain_completion.py#L193)<br>[`app/test_domain_completion.py:IdentityCompletionTests.test_login_mismatched_identifier_rejected`](../../app/test_domain_completion.py#L206)<br>[`app/test_domain_completion.py:RecoveredTimelineTests.test_anonymous_activity_recovers_original_customer_timeline_dates`](../../app/test_domain_completion.py#L561)<br>[`app/test_domain_completion.py:RecoveredTimelineTests.test_corrupt_cross_business_session_blocks_backfill_without_mutation`](../../app/test_domain_completion.py#L573)<br>[`app/test_domain_completion.py:CanonicalCompletionTests.test_known_visitor_reobservation_preserves_resolved_identity`](../../app/test_domain_completion.py#L104) |
| Normalized customer contact/tag/source lookup, product source lookup, inbox content search and paginated chronological journey | [`app/domains/queries.py:lookup`](../../app/domains/queries.py#L8) | [`app/test_domain_completion.py:OperationalCompletionTests.test_customer_lookup_by_normalized_contact_tag_and_source`](../../app/test_domain_completion.py#L220)<br>[`app/test_domain_completion.py:OperationalCompletionTests.test_product_source_lookup_does_not_mix_connections`](../../app/test_domain_completion.py#L229)<br>[`app/test_domain_completion.py:OperationalCompletionTests.test_inbox_search_uses_messages_but_not_internal_notes`](../../app/test_domain_completion.py#L235)<br>[`app/test_domain_completion.py:OperationalCompletionTests.test_journey_is_chronological_across_sessions_and_paginated`](../../app/test_domain_completion.py#L274) |
| Canonical support/customer/order/message context, audited conversation priority and scheduled callback foundation without initiating a call | [`app/domains/projections.py:support_context`](../../app/domains/projections.py#L143) | [`app/test_domain_completion.py:OperationalCompletionTests.test_support_context_composes_canonical_data_and_explicit_fallbacks`](../../app/test_domain_completion.py#L244)<br>[`app/test_domain_completion.py:OperationalCompletionTests.test_context_rejects_unrelated_order_even_inside_same_business`](../../app/test_domain_completion.py#L257)<br>[`app/test_domain_completion.py:OperationalCompletionTests.test_priority_command_validated_authorized_and_audited`](../../app/test_domain_completion.py#L264)<br>[`app/test_domain_completion.py:CallbackAndConversionTests.test_requested_callback_can_be_scheduled_without_starting_a_call`](../../app/test_domain_completion.py#L586) |
| Current verified evidence/action approval, unsafe generic-reference filtering and future relationship exclusion | [`app/domains/contracts.py:recommendation_supported`](../../app/domains/contracts.py#L32) | [`app/test_domain_completion.py:ExternalContractTests.test_expired_fact_cannot_approve_action_or_surface_recommendation`](../../app/test_domain_completion.py#L311)<br>[`app/test_domain_completion.py:ExternalContractTests.test_mixed_foreign_evidence_cannot_leak_or_approve`](../../app/test_domain_completion.py#L317)<br>[`app/test_domain_completion.py:ExternalContractTests.test_foreign_generic_entity_in_fact_is_filtered`](../../app/test_domain_completion.py#L334)<br>[`app/test_domain_completion.py:PersistedGraphContractTests.test_future_relationship_is_not_current_context`](../../app/test_domain_completion.py#L418) |
| Persisted tenant-safe one-hop graph read, observed retargeting context and explicit external policy/AI/BI fallbacks | [`app/domains/projections.py:graph_context`](../../app/domains/projections.py#L173) | [`app/test_domain_completion.py:PersistedGraphContractTests.test_graph_context_uses_persisted_owned_nodes_and_edges`](../../app/test_domain_completion.py#L431)<br>[`app/test_domain_completion.py:PersistedGraphContractTests.test_foreign_neighbor_and_edge_are_not_exposed`](../../app/test_domain_completion.py#L442)<br>[`app/test_domain_completion.py:PersistedGraphContractTests.test_missing_projection_returns_unavailable_without_building_graph`](../../app/test_domain_completion.py#L451)<br>[`app/test_domain_completion.py:OperationalCompletionTests.test_retargeting_context_is_observed_data_not_recommendation`](../../app/test_domain_completion.py#L285)<br>[`app/test_domain_completion.py:CrossSourceAndQueueContractTests.test_queue_declares_unavailable_external_policies`](../../app/test_domain_completion.py#L481) |
| Canonical outbound shipment submit/cancel, call and message request contracts with authorization and no execution/state change | [`app/domains/contracts.py:prepare_operation`](../../app/domains/contracts.py#L54) | [`app/test_domain_completion.py:ExternalContractTests.test_shipment_preparation_returns_contract_without_execution`](../../app/test_domain_completion.py#L339)<br>[`app/test_domain_completion.py:ExternalContractTests.test_call_and_message_preparation_preserve_canonical_state`](../../app/test_domain_completion.py#L350)<br>[`app/test_domain_completion.py:ExternalContractTests.test_outbound_preparation_rejects_viewer_and_payload_overrides`](../../app/test_domain_completion.py#L362) |
| Repeatable isolated continuation demo and PostgreSQL variant/status race protection | [`app/management/commands/demo_completion.py:Command.handle`](../../app/management/commands/demo_completion.py#L18) | [`app/test_domain_completion.py:ContinuationDemoTests.test_verified_demo_replays_without_duplicate_canonical_data`](../../app/test_domain_completion.py#L492)<br>[`app/test_domains.py:PostgresConcurrencyTests.test_concurrent_variant_events_upsert_one_parent_sku`](../../app/test_domains.py#L1006)<br>[`app/test_domains.py:PostgresConcurrencyTests.test_identity_deactivation_racing_resolution_leaves_no_active_link`](../../app/test_domains.py#L1016) |

## Schema and migration safety

Existing `0001_initial.py` and the legacy checked-in database were not modified. The previous
increment introduced migrations 0002–0004 (membership/audit/receipts/support/marketing/callback
foundation, integrity constraints and product images). This continuation adds:

- `app/migrations/0005_variant_deduplication.py`: conditional unique `(product, sku)` for nonblank
  variant SKU. `preflight_domains` now reports duplicate groups read-only; it never repairs them.
- `app/migrations/0006_message_location.py`: nullable canonical Message JSON location.
- `app/migrations/0007_requested_callbacks.py`: nullable requested callback time; scheduling is an
  explicit future-time command. No auto-dialer or background scheduling engine is introduced.

Fresh SQLite and PostgreSQL migrations through 0007 and no-drift checks passed. Applying these
constraints to any populated shared environment still needs reviewed preflight/duplicate resolution.
This is not permission to rewrite another developer's data.

The legacy file SHA-256 remains
`b8ae586e334293f514cec76dab130cdd342096b5c1615655a4a1d58efa9097d1`.
`bizora.local_settings` uses a separate `/tmp` database and in-memory test DB. The PostgreSQL
verifier uses a random localhost container/database, tmpfs and ephemeral credentials, bootstraps
pgvector before baseline migration, then removes only its own container. Its readiness probe now
waits for TCP instead of PostgreSQL's temporary socket-only initialization server.

## API surface


All domain routes begin `/api/businesses/{business_id}/`. Session authentication (CSRF for
writes) and DRF Basic authentication are supported. Basic authentication should only be used
on localhost for this demo or over HTTPS. Membership is required even for Django superusers.

| Method / suffix | Behaviour |
| --- | --- |
| `GET /api/` | Existing public API status; unchanged response |
| `GET, POST {resource}/` | Paginated canonical reads / validated idempotent intake |
| `GET {resource}/{id}/` | Canonical detail plus bounded related projections |
| `POST {resource}/{id}/transition/` | Explicit validated lifecycle command |
| `GET overview/` | Canonical counts, activity and authoritative context; no invented revenue/health |
| `GET customers/{id}/360/` | Customer contacts/tags/identities, orders/payments/refunds/support/calls/delivery/web activity |
| `POST variants/{id}/update/` | Validated catalog edits with optional optimistic timestamp; order snapshots remain unchanged |
| `GET financial-timeline/` | Paginated payment/refund chronology with customer/order filters |
| `GET website-performance/` | Visitor/session/event records plus explicit unavailable analytical capabilities |
| `GET support-queue/` | Open/pending queue, priority order, assigned/unassigned/team views |
| `POST conversations/{id}/assign/` | Agent/team/AI assignment, reassignment or release |
| `POST conversations/{id}/handover/` | Atomic AI/Human handling state, ownership, reason and history |
| `POST messages/{id}/read/` | Idempotent read acknowledgement |
| `GET identity/{canonical,external,links,conflicts,merge-candidates,history}/` | Manager-only identity reads |
| `POST identity/{command}/` | Manager-only deterministic identity/review commands |
| `POST actions/{id}/review/` | Manager approval/rejection of a persisted recommendation-backed action; never executes it |

Resources: `products`, `product-images`, `variants`, `product-references`, `customers`, `contacts`, `tags`,
`customer-references`, `orders`, `payments`, `refunds`, `conversations`, `participants`,
`messages`, `attachments`, `notes`, `campaigns`, `campaign-metrics`, `conversions`,
`ad-accounts`, `ad-sets`, `ads`, `creatives`, `visitors`, `sessions`, `website-events`,
`shipments`, `shipment-events`, `calls`, `call-events`, `transcripts`, `callbacks`.

Identity commands: `canonical`, `register`, `resolve`, `link`, `unlink`, `verify-contact`,
`anonymous-link`, `set-status`, `enrich-external`, `resolve-many`, `validate-links`, `identified-link`, `detect-merges`, `review-merge`, `execute-merge`, `review-conflict`.
`execute-merge` returns `BLOCKED` after checking approval and records why. It does not
partially reparent customers/orders/BI/graph/AI references.

List controls: `page`, `page_size` (default 25, max 100), supported resource-specific exact
filters, `q` for supported names/SKUs/order numbers/subjects/tracking codes, and ISO-offset
`since`/`until` where date fields exist. Unsupported filters fail validation. Queue supports
`assigned=me|team|unassigned`, status, priority and channel. There is no unrestricted PATCH
or DELETE. Child projection sections cap results at 50 and explicitly report truncation;
use paginated resource endpoints for the rest.

Example product intake (curl prompts for the local user's password):

```bash
curl --user demo-owner -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-product-2' \
  -d '{"data":{"name":"Coffee","sku":"COFFEE","price":"150.00"}}' \
  http://127.0.0.1:8000/api/businesses/1/products/
```

Example order body, using the actual customer/product IDs printed by the demo:

```json
{"connection_id":1,"data":{"external_order_id":"demo-order-2","customer":1,
 "items":[{"product":1,"quantity":2,"unit_price":"125.00"}],"shipping_amount":"60.00"}}
```

Transition body: `{"status":"CONFIRMED","expected_status":"PENDING","reason":"Reviewed"}`.
Assignment body: `{"assignee_type":"AGENT","assignee_id":1,"reason":"Support queue"}`.
Handover body: `{"target":"AI","reason":"Routine question","summary":"Human-provided context"}`.
Identity registration: `{"connection_id":1,"entity_type":"CUSTOMER","identity_type":"EMAIL",
"value":"demo@example.test","external_id":"52","verified":true}`. Verification must reflect
actual manager-reviewed evidence; a random email/phone assertion must not be marked verified.


### Additional endpoints and contracts

All suffixes below are under `/api/businesses/{business_id}/` with existing membership/roles.

| Method / suffix | Implemented behavior |
| --- | --- |
| `POST conversations/{id}/priority/` | `{priority, reason}`, validated and audited |
| `GET conversations/{id}/context/?order={id}` | Canonical messages/notes/history/customer and validated optional order; policy/reply explicitly unavailable |
| `GET visitors/{id}/journey/` | Chronological paginated events across the visitor's sessions |
| `GET customers/{id}/retargeting-context/` | Observed sessions/events/conversions; no audience score or recommendation |
| `GET graph-context/{kind}/{id}/` | Existing owned one-hop nodes/edges only; generation unavailable |
| `POST callbacks/{id}/schedule/` | `{scheduled_at: ISO timestamp with offset}`, future time, idempotent audit, no call execution |
| `POST operations/{operation}/{id}/prepare/` | `shipment_submit`, `shipment_cancel`, `call_initiate`, `message_send`; canonical request with `UNAVAILABLE` / `NOT_EXECUTED` |
| `POST identity/set-status/` | `{canonical_identity_id, status, reason}`; ACTIVE/INACTIVE/SUPERSEDED, never a fake MERGED state |
| `POST identity/enrich-external/` | `{external_identity_id, metadata, observed_at, reason, verification?}`; explicit reviewed verification and monotonic seen bounds |
| `POST identity/resolve-many/` | `{external_identity_ids: [id1,id2,...]}`; 2–20 verified independent customer identifiers, atomic result |
| `POST identity/validate-links/` | Explicit manager-triggered stale/invalid-link conflict review; does not silently repair |
| `POST identity/identified-link/` | `{visitor_id, identification_event_id, external_identity_id}`; verified login/signup/form evidence |

List filters additionally support paired `connection_id`/`external_id`, customer `contact` +
`contact_type`, customer tags, inbox message-content search and `ordering=newest|oldest`.
Identity query filters are resource-validated: status/entity type/canonical/external/rule key.
Provider identifiers remain opaque and case-sensitive; only comparable email/phone values normalize.
No arbitrary outbound payload override, unrestricted PATCH or DELETE is introduced.

## Remaining work, ownership and decisions

**A — unfinished local behavior:** the audit retains operational frontend views as PARTIAL;
there is no UI application to extend and a new framework was deliberately not introduced.
Product source/replay and variant dedup work, but arbitrary product creates without a source
reference do not deduplicate globally by SKU (SKU uniqueness across products is not assumed).
Customer multi-field corroboration and opt-in verified product SKU matching are explicit fixed
rules, not a general configurable matching engine. Link confidence is stored/range-checked but
currently fixed at 1 for accepted links; no graded scoring/calibration policy is implemented.
Product merge candidates intentionally do not invent confidence. These local limitations are
not mislabelled as another developer's implementation blocker. Agree SKU authority, rule
configuration and confidence semantics before broadening automatic matches.

**B — tested local seams completed, external behavior still missing:**

| Owner | Local interface completed | Still required from owner |
| --- | --- | --- |
| Integrations | Canonical typed intake, source isolation/replay, observed states/events, non-executing outbound envelope | Real provider schemas/status mapping, authentication/signatures, adapter transport/acknowledgements, retries, recording/attachment access |
| Business Intelligence | Existing metric/fact/issue/evidence readers, current verified evidence checks, preserved attribution inputs | Revenue/attribution, funnel/abandonment/retention, support SLA metrics, campaign/courier/region analysis and authoritative issue outputs |
| Business Graph | Safe persisted one-hop read and relationship validity guards | Graph building, full traversal/journey/projection contracts and redirect/reprojection on merge |
| AI Intelligence | Context/evidence inputs and manager proposal review; explicit unavailable generated result | Replies, generated summaries/recommendations, action execution and outcome feedback |
| Business Memory & Knowledge | Explicit unavailable policy context, actual canonical customer/order/history context | Authorized policy retrieval and context provenance |
| Business Configuration / Observability | Named unavailable overdue/escalation/freshness capabilities | Response/resolution policy, threshold semantics, freshness and notification policies |

**C — genuinely blocked:** canonical identity consolidation, downstream relationship preservation
and completed merge history. `identity.execute_merge` returns `BI_GRAPH_AI_MERGE_CONTRACT` and
records the blocked attempt. BI/Graph/AI owners must agree polymorphic reference redirection,
reprojection, audit/history preservation and transaction/failure semantics before any physical
merge. Identity MERGED lifecycle/match provenance/review terminal state remain PARTIAL for that
same reason. Approval is not evidence of a completed merge.

Provider execution, authoritative BI calculations, graph generation, AI text generation and
knowledge retrieval are not implemented locally. B means the input/read/fallback seam works;
it does not imply those services exist. Missing results stay unavailable, never fabricated.

## Verification results

Captured final output: [SQLite suite](verification/sqlite-tests.txt),
[PostgreSQL suite and fresh migrations](verification/postgresql-tests.txt),
[fresh SQLite migrations and repeat demo](verification/sqlite-migrations.txt).

| Check | Actual result |
| --- | --- |
| Full SQLite `manage.py test --noinput` | **195 discovered; 191 passed; 4 skipped; 0 failures/errors** |
| Full PostgreSQL/pgvector suite | **195 discovered; 193 passed; 2 skipped; 0 failures/errors** |
| Fresh SQLite and PostgreSQL migration through 0007 | Passed |
| Both backends `check`, `makemigrations --check --dry-run`, `preflight_domains` | Passed; no schema drift; no duplicate groups on fresh DB |
| Fresh isolated SQLite `demo_completion`, twice | Passed; identical business/customer/order/payment/shipment/link/visitor/support IDs |
| Audit generator | 298 unique rows / 31 groups; all cited source/test symbols resolve |
| `git diff --check` | Passed |
| Branch / legacy database | `feat/business-domains`; SHA-256 unchanged |

SQLite skips all four real PostgreSQL concurrency tests. PostgreSQL skips the two intentionally
SQLite-only demo tests. PostgreSQL exercises simultaneous receipt replay, competing refunds,
variant same-SKU intake and identity deactivation racing resolution. SQLite's success alone is
not concurrency evidence. No production services, secrets, existing Compose volumes or named
shared databases were used. Disposable verification containers were removed.

A PostgreSQL initialization race in the verifier was reproduced and corrected by waiting for
TCP readiness; the final verification runs passed afterward. New tests also exposed a missing
FK ancestry path for valid recommendation evidence, which was corrected without bypassing
ownership validation. Full suites were rerun after the final runtime/test changes.

## Verified local demo

Use the existing virtualenv; no dependency installation is needed for these commands.

```bash
export DJANGO_SETTINGS_MODULE=bizora.local_settings
export BIZORA_DATA_DIR="$(mktemp -d /tmp/bizora-demo-XXXXXX)"
export DJANGO_SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py createsuperuser --username demo-owner
.venv/bin/python manage.py demo_completion --username demo-owner
.venv/bin/python manage.py demo_completion --username demo-owner
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

The command reuses `demo_domains` and its isolated-business/source guard, then demonstrates
verified email+phone corroboration, login journey recovery and support priority/context.
Use the IDs and API URLs printed by the command. Authentication uses the password you set;
Basic auth is for localhost or HTTPS. Example (curl prompts for the password):

```bash
curl --user demo-owner http://127.0.0.1:8000/api/businesses/1/conversations/2/context/
curl --user demo-owner http://127.0.0.1:8000/api/businesses/1/visitors/1/journey/
```

The printed IDs above are from a verified fresh database; use your actual printed values if
reusing a database. The demo intentionally shows unavailable AI/policy outputs and performs
no live transport. It refuses the tracked/nonlocal database. Repeatability does not suppress
legitimate audit history: canonical IDs remain stable while reviewed commands can add audit.

```bash
DJANGO_SETTINGS_MODULE=bizora.local_settings .venv/bin/python manage.py test --noinput
.venv/bin/python scripts/verify_domains_postgres.py
.venv/bin/python scripts/audit_domain_requirements.py
```

Docker and the cached `pgvector/pgvector:0.8.7-pg16` image are required for the PostgreSQL verifier.
Existing `docker-compose.yml` is not the isolated verification workflow and its stock PostgreSQL
configuration does not bootstrap the vector extension. Existing-environment deployment remains
a separately reviewed migration plan.

## Changed files and PR readiness

Continuation runtime changes: `app/domains/common.py`, `data.py`, `identity.py`, `operations.py`,
`projections.py`; new `app/domains/contracts.py`, `queries.py`; `app/domain_views.py`,
`app/serializers/domains.py`, `app/urls.py`, `app/models.py`; migrations 0005–0007;
`app/management/commands/preflight_domains.py`; new `demo_completion.py`;
`app/test_domain_completion.py`, additional concurrency methods in `app/test_domains.py`;
`scripts/verify_domains_postgres.py`; new `scripts/audit_domain_requirements.py`; this report,
Markdown/JSON audit and captured verification logs. README demo instructions were refreshed.

The working tree also contains the user's earlier uncommitted increment (settings, README,
foundations/migrations 0002–0004 and other domain files). `git status` includes those earlier
changes; they must not all be attributed to this continuation. No commit/push/merge/branch switch
was made, no dependencies installed, and no production credentials or services accessed.

**PR assessment:** suitable for review as a backend increment with the passing evidence and
explicit limitations above. **Not ready to present as completion of all three domains or all 298
requirements**, and not an approved deployment to an existing populated database. Review the
whole uncommitted diff and migration preflight before preparing a PR; no PR was opened.

## All 31 group statuses

Groups are COMPLETE only when every documented subfeature in that group is COMPLETE. See the
full audit for each exact requirement, evidence and category; do not infer completeness from
this compact roll-up.

| Domain / group | COMPLETE | PARTIAL | BLOCKED | Group status |
| --- | ---: | ---: | ---: | --- |
| business-data / Product | 6 | 2 | 0 | PARTIAL |
| business-data / Customer | 10 | 0 | 0 | COMPLETE |
| business-data / Order | 10 | 1 | 0 | PARTIAL |
| business-data / Payment | 8 | 1 | 0 | PARTIAL |
| business-data / Communication | 7 | 4 | 0 | PARTIAL |
| business-data / Customer Support | 14 | 1 | 0 | PARTIAL |
| business-data / Marketing | 9 | 3 | 0 | PARTIAL |
| business-data / Website Behavior | 13 | 1 | 0 | PARTIAL |
| business-data / Courier | 8 | 4 | 0 | PARTIAL |
| business-data / Calling | 9 | 4 | 0 | PARTIAL |
| identity-resulation / Canonical Identity | 5 | 1 | 0 | PARTIAL |
| identity-resulation / External Identity | 7 | 0 | 0 | COMPLETE |
| identity-resulation / Identity Linking | 5 | 2 | 0 | PARTIAL |
| identity-resulation / Cross-Source Matching | 6 | 2 | 0 | PARTIAL |
| identity-resulation / Anonymous Identity Linking | 5 | 2 | 0 | PARTIAL |
| identity-resulation / Merge Detection | 4 | 2 | 2 | PARTIAL |
| identity-resulation / Identity Conflict Resolution | 9 | 0 | 0 | COMPLETE |
| identity-resulation / Identity History | 6 | 0 | 1 | PARTIAL |
| business-oparations / Business Overview | 0 | 6 | 0 | PARTIAL |
| business-oparations / Customer 360 | 0 | 12 | 0 | PARTIAL |
| business-oparations / Product Operations | 0 | 10 | 0 | PARTIAL |
| business-oparations / Order Operations | 0 | 11 | 0 | PARTIAL |
| business-oparations / Payment Operations | 0 | 8 | 0 | PARTIAL |
| business-oparations / Unified Inbox | 0 | 9 | 0 | PARTIAL |
| business-oparations / Support Queue | 0 | 8 | 0 | PARTIAL |
| business-oparations / Conversation Assignment | 8 | 0 | 0 | COMPLETE |
| business-oparations / AI ↔ Human Handover | 0 | 8 | 0 | PARTIAL |
| business-oparations / Marketing Operations | 0 | 10 | 0 | PARTIAL |
| business-oparations / Website Performance | 0 | 11 | 0 | PARTIAL |
| business-oparations / Delivery Operations | 0 | 11 | 0 | PARTIAL |
| business-oparations / Call Operations | 0 | 12 | 0 | PARTIAL |
