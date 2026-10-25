# Integration & Data Observability

This module implements all eight areas in `features/intrgration-data-observability.md` on the existing Django/DRF backend. It observes integration and processing outcomes, persists troubleshooting evidence, and exposes business-scoped reliability APIs. Integration execution and canonical processing remain separate boundaries.

## Architecture and ownership

| Package | Responsibility |
| --- | --- |
| `app/observability/models.py` | Observations, error groups, failures, freshness, grants, policy, attempts, and audit evidence. |
| `app/observability/services.py` | Atomic/idempotent recording and validated relationships, counters, timestamps, and transitions. |
| `app/observability/selectors.py` | Batched connection projections, provider evidence classification, freshness, and coherent summaries. |
| `app/observability/policies.py` | Deterministic health/freshness rules and bounded diagnostic redaction. |
| `app/observability/operations.py` | Authorized retry/replay/check orchestration, durable attempt records, limits, backoff, and recovery history. |
| `app/observability/lifecycle.py` | Audited acknowledgement, review, resolution, ignore, and reopening. |
| `app/integrations/` | Protected source capture and the provider-operation interface/registry. |
| `app/business_data/products.py` | Narrow canonical product validation/persistence used by the deterministic prototype adapter. |
| `app/observability/views.py`, `serializers.py`, `urls.py` | Authenticated APIs, validated filters, pagination, safe representations, and structured errors. |
| `app/observability/demo.py` | Seeded source inputs and independently validated expectations. |

Existing `IntegrationSource`, `IntegrationConnection`, and `IntegrationSyncLog` remain the provider, connection, and sync foundations. Public model imports remain available through `app.models`, including the existing `VectorField` import used by migration 0001. The differing UUID-based `db_diagram.sql` has not been imported or substituted for the ORM.

No connector accounts, OAuth lifecycle, revenue metrics, business issues, identity decisions, graph projections, or LLM calls are implemented here. Downstream consumers use the returned reliability context rather than treating integration errors as business-performance findings.

## Storage and migration

Apply `app.0002_integration_data_observability`. It adds 13 models and extends `IntegrationSyncLog` with explicit entity, trigger, success/skip, discovered-total, cursor, retry-parent, initiator, observation-time, and counter-version fields. It preserves existing records and primary keys.

Old sync counters have unspecified accounting semantics. Their values remain unchanged and are marked `counter_schema=LEGACY`; API success/skip counts are `null` rather than fabricated. Existing run observation times are backfilled from completion/start/creation time, so migration does not make historical failures look recent. Newly recorded runs use `counter_schema=V1`. An unfinished legacy run requires a complete explicit counter snapshot before adopting V1 accounting.

Historical references use protection against accidental deletion. Receipts, error fingerprints, provider-event identities, freshness identities, operation keys, grants, and policy scopes have database uniqueness constraints. Numeric and policy constraints complement service validation. Cross-business relationships are checked before accepted state is committed.

`IntegrationPayload` belongs to the integration boundary and keeps immutable captured JSON, a digest, signature evidence, and original timestamps. It is absent from the admin and ordinary list/detail serializers. Diagnostic access returns a redacted copy; replay uses the protected original. Database operators must retain normal protections for the stored original source material.

## Recording contract and event wiring

The internal recording entry point is:

```python
from app.observability.services import record_observation

receipt = record_observation(
    business_id=business.pk,
    connection_id=connection.pk,
    key="provider-delivery-or-processing-observation-id",
    kind="connection_check",
    data={"outcome": "SUCCESS", "latency_ms": 25},
    observed_at=aware_observation_time,
    received_at=aware_telemetry_reception_time,
)
```

The observation key is unique within a connection. Redelivery with identical kind/content returns the receipt; rebinding the key is rejected. Distinct occurrences use distinct keys. `received_at` describes telemetry reception and cannot precede the observation. Payload source/original reception times are separate fields.

Supported kinds:

| Kind | Input highlights | Persisted output |
| --- | --- | --- |
| `connection_check` | `outcome`: SUCCESS/DEGRADED/ERROR/AUTH_ERROR/EXPIRED; optional auth/credential status, latency, code/message. | Connection check and classified error when appropriate. |
| `provider_request` | SUCCESS/AUTH_ERROR/RATE_LIMIT/TIMEOUT/PROVIDER_ERROR/CONNECTIVITY_ERROR; capability, target, HTTP status, latency, remaining quota, retry-after, quota scope. | Provider request evidence and classified failures. |
| `sync` | New entity/mode/trigger or existing `sync_id`; status, absolute counters, optional discovered total, cursor, safe metadata. | Existing/new sync run and terminal failure context. |
| `failed_record` | Entity/external ID, stage, code, optional payload/sync/webhook references. | Classified failed record and grouped error. |
| `webhook` | Event ID/type/entity, validation/status, optional payload/provider time; `delivery=False` for processing updates. | Event observation, delivery evidence, failed-record/error context. |
| `data_confirmed` | Entity, source timestamp, original reception timestamp, completeness. Publish only after the owning processor confirms valid canonical persistence. | Monotonic entity/source watermark. |
| `integration_error` | Code/category/severity, safe message/details, optional entity/sync/webhook context. | Scoped error group and occurrence history. |

Provider IDs absent from a webhook observation fall back to `observation:<key>`. This deduplicates that receipt, not unrelated provider deliveries. Adapters should supply stable provider event IDs or their own conservative identity. Do not use body equality alone as a universal event identifier.

The same contract can be dispatched with `DomainEvent('integration.observation', payload)`. `AppConfig.ready()` registers the handler idempotently. There is no public observation-ingestion endpoint. Producers are trusted integration/processing code and must still supply valid scoped references.

Recording locks the connection row and commits its receipt, observations, failures, and projections atomically. Out-of-order sync progress is retained as an accepted receipt but cannot overwrite newer run state. Counters use absolute snapshots. PostgreSQL concurrency tests verify duplicate suppression, occurrence increments, and competing operational requests.

`publish_after_commit(**observation)` defers synchronous dispatch until the producer's transaction commits; rollback suppresses publication. This is not a durable queue or outbox. Callback errors propagate; integration owners needing guaranteed delivery must add their own durable publication infrastructure. Supported retry/replay writes are within the same transaction as the canonical operation.

## State and accounting rules

- Connection administrative lifecycle, measured health, provider health, and entity freshness are separate response dimensions.
- Latest recent communication supplies connection/authentication health. High latency, sufficiently sampled recent error rates, quota exhaustion/approach, failed records/webhooks, partial/failed syncs, and overdue runs supply explained degradation signals.
- Last successful communication and last failure are preserved independently. Acknowledging/ignoring an error does not repair the connection.
- Explicitly disabled monitoring suppresses alerts without changing the observed data's actual freshness. Disconnected active integrations remain visible as problems.
- Simplified connection reliability prioritizes ERROR/DEGRADED over stale data. Otherwise stale, delayed/incomplete, or unavailable monitored entity data yields STALE, DEGRADED, or UNKNOWN with a separate `summary_reason`.
- V1 sync accounting: `processed = succeeded + skipped + failed <= received`; a known discovered total is at least received. COMPLETED/PARTIAL accounts for all received records. Clean completion has zero failures; PARTIAL has successes and failures. Unknown/zero progress denominators yield `null` percentages.
- New sync modes are FULL/INCREMENTAL; trigger origin is MANUAL/SCHEDULED/REPLAY/RETRY. PENDING may proceed to RUNNING/FAILED; RUNNING may proceed to COMPLETED/PARTIAL/FAILED. Terminal runs stay historical; retry creates a linked child run.
- Pending runs have no execution start time. RUNNING establishes it; queue wait is not included in execution duration. An initial terminal observation can supply an explicit start time, otherwise its execution duration is unknown.
- Error categories: AUTHENTICATION, CONNECTIVITY, PROVIDER_API, RATE_LIMIT, WEBHOOK, SYNC, MAPPING, NORMALIZATION, VALIDATION, INTERNAL. Severity is LOW/MEDIUM/HIGH/CRITICAL.
- Error fingerprints group the same category/code/stage/entity type within a connection. Different records can contribute distinct occurrences to one group. Duplicate observation receipts do not increment it. The first/last occurrence is monotonic. A new failure after resolution reopens the group with an audit entry.
- Error states: ACTIVE → ACKNOWLEDGED/RESOLVED/IGNORED; ACKNOWLEDGED → RESOLVED/IGNORED; RESOLVED/IGNORED → ACTIVE by explicit review or new qualifying evidence.
- Failed-record states support OPEN/REVIEWING, delegated retry, RESOLVED, and IGNORED. Manual resolution requires a note and is labeled MANUAL; confirmed processing recovery is labeled PROCESSING. Administrative closure cannot confirm data freshness.
- Detail responses expose the latest 20 attempts, delivery observations, and/or audit entries. Full evidence remains persisted and is available in the restricted admin.

## Freshness and monitoring policy

Policy precedence is connection+entity, connection default, business+entity, business default, then platform defaults. A selected policy row is a complete policy; unspecified values when creating it take platform defaults. Updates retain that row's existing values. Runtime observations remain separate from configurable policy.

| Policy | Default |
| --- | --- |
| Freshness delayed/stale thresholds | 900 / 1800 seconds |
| Recent health observation TTL | 3600 seconds |
| Provider/error monitoring window | 900 seconds |
| Minimum provider samples/connections | 3 / 2 |
| Error-rate threshold / latency threshold | 0.25 / 2000 ms |
| Retry limit / sync-stalled interval | 3 / 3600 seconds |
| Monitoring enabled | true |

For a trustworthy watermark: age ≤ delayed is FRESH; delayed < age ≤ stale is DELAYED; age > stale is STALE. Missing/future coverage is UNAVAILABLE with a reason. Exact boundaries are tested. Source time must not follow original reception, and original reception must not follow processing confirmation; inconsistent source times cannot establish trusted coverage.

The watermark advances monotonically from confirmed source time or, when absent, original reception time. Processing time is not a freshness replacement. Old replay, a connection test, rejected/received-only webhook, empty poll, and manual resolution cannot make old data current. Successful records in a partial run remain available with incomplete coverage flagged.

`freshness/` and connection detail expose entity/provider/connection, coverage/as-of time, age, thresholds, completeness, warning, reason, and evidence ID. This is the reusable contract for dashboard warnings, analytical completeness checks, and AI context; no LLM is required. Business timezone is returned on connection projections and used for daily sync-history aggregation.

The prototype quota warning is APPROACHING at 1–10 remaining requests and EXHAUSTED at zero or a rate-limit outcome. Connection quota details and retry-after time are visible to that business. Provider health excludes isolated authentication failures and connection-specific quota failures.

Provider health evaluates scoped capability/target samples. It requires sufficient samples and connections, declares UNAVAILABLE at an 80% failure rate, and DEGRADED at the configured error/latency threshold or provider-wide rate limiting. Insufficient/stale evidence is UNKNOWN. Self-hosted WooCommerce/custom websites default to connection-specific targets, preventing one store's failure from declaring a global service outage.

Tenant provider responses can use shared GLOBAL status evidence but expose only their own sample counts. They never expose other businesses' connections, names, raw observations, or exact counts. Explicit superuser global diagnostics expose aggregate counts/rates. Observation age is evaluated on reads, so health expires without a worker rewriting snapshots.

## API and authorization

Root: `/api/businesses/<business_id>/observability/`. Existing `/api/` behavior remains unchanged.

All routes require an authenticated active user and an explicit `BusinessAccess` READER/MANAGER grant, or superuser privilege. Unknown roles are denied. Readers may inspect ordinary reliability data. Managers may configure policy, operate, review/resolve, and inspect redacted payload diagnostics. Global provider diagnostics and the observability admin require superuser privilege. There is no implicit tenant access for all authenticated users or generic staff users.

| Method | Relative route | Result |
| --- | --- | --- |
| GET | `summary/` | Coherent reliability status/reason and connection problems; grouped errors and failed events. |
| GET | `connections/`, `connections/<id>/` | Health, lifecycle, quota, source freshness, success/failure times, and error summaries. |
| POST | `connections/<id>/test/` | Delegated connectivity check. |
| GET | `syncs/`, `syncs/<id>/` | Active/history records, progress, cursor, duration, stalled flag, parent/initiator, attempts. |
| GET | `syncs/statistics/` | Count/failure/partial totals, mean completed duration, latest 100 business-local daily buckets. |
| POST | `syncs/<id>/retry/` | New integration-owned execution with a linked child run. |
| GET | `failed-records/`, `failed-records/<id>/` | Source identity, stage/code, payload reference, review/resolution and attempts. |
| GET | `failed-records/groups/?group_by=code` | Group counts by code, stage, or entity type. |
| PATCH | `failed-records/<id>/` | Audited review/manual lifecycle change. |
| POST | `failed-records/<id>/retry/` | Eligible processing retry. |
| GET | `webhooks/`, `webhooks/<id>/` | Receipt/validation/processing, safe payload reference, timings, duplicates, delivery and replay evidence. |
| POST | `webhooks/<id>/replay/` | Eligible replay through the same trusted processor. |
| GET | `freshness/` | Flat source/entity reliability context, paginated by owning connections. |
| GET | `providers/`, `providers/<id>/` | Scoped capability health; `?scope=global` requires superuser. |
| GET | `errors/`, `errors/<id>/` | Classified, scoped error groups and occurrence/lifecycle context. |
| PATCH | `errors/<id>/` | Acknowledge, resolve, ignore, or reopen. |
| GET | `policies/` | Paginated configuration rows. |
| PUT | `policies/` | Upsert a business/connection/entity policy after manager authorization and validation. |
| GET | `payloads/<id>/` | Manager-only redacted diagnostic copy; access itself is audited; no update route. |

Mutation examples:

```json
{"idempotency_key": "operator-replay-2026-10-26-001"}
```

```json
{"status": "ACKNOWLEDGED", "note": "Investigating provider credentials."}
```

```json
{"connection_id": 12, "entity_type": "ORDER", "delayed_seconds": 900, "stale_seconds": 1800}
```

Example safe freshness shape:

```json
{
  "connection_id": 12,
  "provider_id": 3,
  "entity_type": "ORDER",
  "status": "STALE",
  "reason": "EXPECTED_UPDATE_OVERDUE",
  "coverage_at": "2026-10-26T10:00:00Z",
  "as_of": "2026-10-26T11:00:00Z",
  "age_seconds": 3600,
  "delayed_seconds": 900,
  "stale_seconds": 1800,
  "complete": true,
  "warning": true
}
```

Collections default to 25 owning records per page and allow `page_size` 1–100. `freshness/` pages connections, then returns their matching entity rows; its `count` is the connection count, not a claim about total entity rows. Missing configured entities appear as UNAVAILABLE rather than disappearing.

History/error/failure/webhook filters include applicable connection/provider/entity/status and aware ISO `from`/`to` ranges. Syncs additionally support `active=true|false`, mode, and trigger. Errors support category/severity/stage, and failures support stage/grouping. Resource-inappropriate filters, invalid enum values, unsafe ordering, and malformed ranges return 400. Detail endpoints do not accept collection filters. Histories support id/time/status ordering with a stable ID tie-breaker. No GET calls a provider.

Cross-business URL/detail/body/filter/reference access is rejected. Common diagnostic credential keys and credential-bearing text are redacted recursively and bounded; connection configs/authorization headers are never dumped. Invalid mutations return structured 400 errors; denied access returns 403 under the current authentication setup. Unknown scoped objects return 404. Unsupported operations return 409 with an UNSUPPORTED attempt, while a completed synchronous attempt returns 200 and an explicit SUCCEEDED/FAILED status. There is no unbacked 202/queue claim.

Use the superuser admin to grant READER/MANAGER access and configure policy. Operational evidence is read-only there. Producers may also create grants through trusted application code:

```python
BusinessAccess.objects.update_or_create(
    business=business, user=user, defaults={"role": "MANAGER"}
)
```

## Retry/replay boundary and supported capabilities

`IntegrationOperations` defines connection checking, captured-payload processing, and the owning domain's `confirm_processing(result)` contract. Observability requires typed processing results and explicit owner confirmation before recording valid coverage; it does not query product/order business tables itself. `register_adapter(provider_key, factory)` allows trusted integration code to supply a live implementation; requests cannot select arbitrary import paths or factories. A registered owner can support another canonical domain through the same interface, as tested with an order owner.

The bundled mock adapter supports connection checks and PRODUCT payload processing. It maps provider inputs into the separate Business Data product validator, creates/updates a canonical `Product` plus external reference, and returns typed confirmation. Late/duplicate source versions are skipped and cannot overwrite newer product state. Simulated outcomes are explicitly marked `is_mock`.

For PRODUCT sync retry, the original integration log's protected `metadata.payload_ids` must refer to unique captured records from that connection (maximum 1000). The adapter processes each through canonical validation, preserves successful records when others fail, captures individual failures, and reconciles success/skip/failure totals. Invalid data is not silently counted as success.

The prototype mapping can be corrected with connection configuration `{"mock": {"product_name_field": "title"}}` when the captured provider used `title`; the original body stays immutable. `mock.connection_outcome` and `mock.processing_outcome=TIMEOUT` support controlled provider failures.

An operation idempotency key is bound to its connection/action/target. Competing requests lock the connection, reload target state, and cannot process the same resolved failure twice. Failed retries use bounded exponential backoff beginning at 30 seconds, capped at 300, with a configurable attempt limit; the caller schedules subsequent attempts. No handler sleeps. A processing failure includes safe classification/recoverability and preserves prior history.

Only VALID, FAILED webhook observations with verified immutable captured material can replay. Rejected signatures cannot be promoted or bypassed. Processing failures and unexpected adapter exceptions roll back their processing savepoint while retaining a safe failed attempt. Administrative review does not count as processing recovery.

Live provider implementations and non-PRODUCT prototype processing are explicitly unsupported until their owners supply adapters. The module still records and projects observations for every entity/provider category, independently of executable retry capability. No credentials or live-provider network access are needed for the supported acceptance scenarios.

## Local setup and verification

Use Python 3.12 with the pinned `requirements.txt` dependencies:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

SQLite remains the default. For a disposable demo database, set a fresh path so the tracked database is untouched:

```bash
export BIZORA_DB_PATH="$(mktemp /tmp/bizora-observability.XXXXXX.sqlite3)"
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py simulate_observability --seed 75001 --at 2026-10-25T12:00:00+00:00
```

The demo creates its own `obs-demo-*` businesses, sources, immutable payloads, observed inputs, canonical products, attempts, and expected results. It validates 13 outcomes covering healthy inputs, 8/1/1 partial accounting, rejected webhooks, stale orders, isolated token failure, provider outage, old replay, genuine new coverage, and tenant isolation. Reruns are deterministic and revalidate current state. Tampering causes a failing exit status. `--business-slug` must use `obs-demo-` and cannot appropriate an existing unrelated business. It never clears business data.

The historical order in the webhook scenario is explicit canonical fixture context; new PRODUCT ingestion/recovery runs actual normalization/persistence. `MockScenario`, `MockScenarioEvent`, and `MockExpectedResult` preserve the simulation's inputs and expectations. The command is demonstration infrastructure, not a new production ingestion service.

Portable checks:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
git diff --check
```

Four PostgreSQL locking tests are explicitly skipped on SQLite. They are required before claiming PostgreSQL concurrency validation. Migration tests exercise both fresh database creation and upgrade from app migration 0001 while preserving existing integration records/counters/timestamps.

For PostgreSQL, set `BIZORA_DATABASE=postgresql` and the standard `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` variables. `POSTGRES_TEST_TEMPLATE` defaults to `template1`. Merely having a PostgreSQL service in the existing Docker Compose file does not select it; supply the backend setting deliberately.

The existing `KnowledgeEmbedding.VectorField` requires pgvector before initial PostgreSQL migration. Use a pgvector-enabled PostgreSQL image/database and enable `CREATE EXTENSION IF NOT EXISTS vector` in the target database. For Django test database creation, enable it in the explicitly selected disposable test template as well. The existing plain `postgres:16-alpine` Compose image does not supply this module's verified test environment automatically.

The implementation was validated with a disposable `pgvector/pgvector:pg16` container, Python 3.12.14, and the pinned project dependencies. The setup did not change knowledge storage or disable initial migrations. No developer `db.sqlite3` writes are required for verification.

There is no background worker in this repository. Health/freshness age is evaluated on reads; integration owners supply ongoing observations and execute any scheduled retries. In-memory event dispatch and synchronous prototype operations have the explicit limits described above.
