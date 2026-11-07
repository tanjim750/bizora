# Implementation prompt: Integration & Data Observability

Copy the prompt below into the implementation agent's chat while working in the Bizora repository. This is a repository-specific implementation task, including a mandatory test-first engineering loop.

---

You are the implementation agent for Bizora / Business Brain. Implement the complete **Integration & Data Observability** backend module in this existing Django project, following the repository's domain and feature documents.

Work autonomously from repository analysis through implementation, migrations, tests, documentation, and final verification. Do not stop after producing a plan, models, endpoint scaffolding, or a demonstration. Deliver working behavior for all eight documented feature areas.

## 1. Mandatory working method: test-first engineering loop

Use a persistent, evidence-driven engineering loop:

**Understand requirement → write a failing behavioral test FIRST → run it and confirm the intended failure → implement the behavior → rerun the test → diagnose and fix failures → refactor → run relevant regressions → repeat.**

Write focused tests quickly, but make their assertions meaningful. Tests must come before the production implementation of each behavior. Do not implement the entire module first and add tests afterward.

Follow this algorithm throughout the task:

```text
read the repository instructions, code, and domain documents
establish the current test and migration baseline
create a requirement-to-test-to-implementation checklist

while any required behavior is unimplemented or any required check fails:
    choose the next coherent behavior, or reproduce an existing defect
    write or extend the smallest meaningful behavioral test FIRST
    run that test and confirm it fails for the intended reason
    fix unrelated setup failures separately; they are not behavioral proof
    implement the behavior through the actual application layers
    run the focused tests

    while focused tests fail:
        inspect the failure and identify its cause
        correct the implementation
        add a regression test first when discovering another defect
        rerun the focused tests

    refactor without changing the required behavior
    run tests for the affected slice and its neighboring behavior
    update the checklist with files, test names, and actual results

    after each substantial slice:
        run the complete project test suite and relevant Django checks
        repair regressions before proceeding

run the final completion gates on the final code
if any requirement or required check fails:
    return to the loop
else:
    deliver the implementation with verification evidence
```

Do not stop merely because one endpoint works or the first test run passes. Continue until the documented scope and completion gates are satisfied. Do not impose an arbitrary iteration count. Each iteration must use new evidence and make progress; do not blindly repeat the same command or unchanged fix.

Never delete, skip, weaken, or replace a valid failing test to make the suite green. Correct a test only when the documented contract proves the test was wrong, and record why. Do not hide failures with broad exception handling, fake success responses, disabled migrations, or unnecessary mocking of the behavior under test.

Keep a concise progress document at `docs/implementations/integration-data-observability-progress.md`. Record requirements, decisions, red/green evidence, remaining work, and verification commands. Resume from it if context is compacted; do not restart completed work.

If a genuine external blocker prevents a required check, finish independent work, document the exact blocker and attempted remedies, and report the task as incomplete. An unavailable test environment is not a passing result. Ask the user only for missing information or access that cannot reasonably be obtained from the repository or environment.

## 2. Read and understand the project before designing changes

Inspect applicable `AGENTS.md` instructions, the working tree, and the current implementation first. Preserve unrelated user changes. Paths and observations below describe the repository when this prompt was prepared; recheck them because implementation may have advanced.

Read these sources in this order, preserving their existing spellings:

1. `docs/implementations/domain.md` — the complete domain map.
2. `docs/implementations/features/intrgration-data-observability.md` — the authoritative feature specification for this task; read the whole document, including examples and domain boundaries.
3. `docs/implementations/features/intregations.md` — ownership of providers, connections, credentials, syncs, raw payloads, ingestion, retry, and replay.
4. `docs/implementations/features/business-data.md` — canonical normalization and persistence boundaries.
5. `docs/implementations/features/business-configuration.md` — configuration ownership, freshness thresholds, monitoring preferences, timezones, and configuration-versus-runtime separation.
6. `docs/implementations/features/overview-monitoring.md` — downstream monitoring consumers.
7. `docs/implementations/features/business-intelligence.md` and `docs/implementations/features/ai-intelligence.md` — reliability context and evidence boundaries.
8. `docs/implementations/features/prototype-simulation.md` — deterministic source events, injected integration failures, expected results, and reproducible validation.
9. The remaining feature documents: `identity-resulation.md`, `business-graph.md`, `business-memory-knowledge.md`, and `business-oparations.md` — understand their responsibilities and avoid taking them over.
10. `app/models.py`, all migrations, `app/events/`, `app/serializers/`, `app/views.py`, `app/urls.py`, `app/tests.py` or its replacement, `app/apps.py`, and `app/admin.py`.
11. `bizora/settings.py`, `bizora/urls.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `docs/setup/docker.md`, and `db_diagram.sql`.

Summarize your findings briefly, then proceed with the work. Do not ask the user to reconfirm the documented requirements.

## 3. Actual repository baseline and implications

At prompt preparation, this is an early backend project, not a completed product with working integrations:

- Dependencies are pinned to Django `4.2.27`, Django REST Framework `3.15.2`, and `psycopg[binary]` `3.2.9`.
- There is one application, `app`, containing 61 Django domain models and one initial migration.
- The implemented API is a status/message response at `/api/`, covered by one `APITestCase`. Preserve its behavior and test.
- There is no frontend, queue worker, scheduler, Celery, Redis, or completed provider connector in the checked-in implementation.
- The event system consists of `DomainEvent(name, payload)`, a synchronous in-memory subscriber dictionary, and `dispatch`/`subscribe`. It is not a durable event bus. The example `health.checked` handler has no operational behavior, and handler startup wiring needs inspection.
- The models provide broad foundations across business data, identity, intelligence, graphs, knowledge, AI, and simulation. Their existence does not mean their corresponding services or workflows are implemented.
- There are no dedicated persisted observability models for webhook observations, individual failed records, classified integration errors, provider request telemetry, or source/entity freshness.
- Global DRF permissions currently use `AllowAny`. There is no modeled user-to-business membership or tenant authorization policy.
- `bizora/settings.py` uses SQLite. Docker Compose provisions PostgreSQL and supplies environment variables, but settings do not currently select PostgreSQL from them.
- `KnowledgeEmbedding` uses a custom `app.models.VectorField` returning SQL type `vector`; the initial migration imports it. PostgreSQL validation must account for the actual extension support of the chosen database image. Do not casually change unrelated knowledge storage to solve setup issues.
- `db_diagram.sql` is a broader, different schema reference: it contains 78 tables, UUID keys, and names such as `integrations`, `integration_providers`, `raw_payloads`, and `sync_states`. The Django implementation instead uses integer keys, `IntegrationSource`, `IntegrationConnection`, and `IntegrationSyncLog`. Do not assume the SQL reference tables exist in the ORM or import the SQL wholesale.
- `db.sqlite3` is tracked and already contains data. Do not modify it while validating this module. Use Django's test database and disposable databases for migration checks.
- During prompt preparation, the host's default Python was `3.14.8` and the project dependencies were not installed there. No Django tests were run during prompt preparation. Docker specifies Python `3.12`; choose and document a suitable project runtime before making test claims.

Reuse and extend the existing integration foundations:

| Existing model | Relevant fields and meaning |
| --- | --- |
| `Business` | Integer primary key, slug, currency, business timezone, status. Existing timestamps require explicit values. |
| `IntegrationSource` | Global provider/source registry: key, name, category, connection type, active flag. |
| `IntegrationConnection` | Business + source, lifecycle status, external account references, config, `is_mock`, `last_synced_at`, `last_successful_sync_at`. |
| `IntegrationSyncLog` | Connection, sync type, status, received/processed/failed counters, error message, start/completion times, metadata. |
| `MockScenario`, `MockScenarioEvent`, `MockExpectedResult` | Existing deterministic simulation foundations; reuse where appropriate. |

Treat current models and migrations as the implemented storage baseline and the feature documents as the behavioral requirements. Add deliberate, additive migrations for missing behavior. Document meaningful differences from the SQL reference; do not redesign all domains or change existing primary keys.

## 4. Architectural scope and domain boundaries

Business Brain's core flow is:

```text
External platforms
    → Integrations
    → canonical Business Data
    → Identity & Resolution
    → deterministic Business Intelligence
    → Business Graph / Business Memory
    → AI Intelligence
    → Overview & Monitoring / Business Operations
```

Observability follows connectivity, provider requests, syncs, webhooks, and processing outcomes along this flow. It reports whether the inputs are healthy, current, complete, and reliable.

Respect these ownership rules:

- Integrations owns connection establishment, credentials, OAuth, provider requests, synchronization, signature validation, idempotent ingestion, and execution of retry/replay.
- Business Data owns normalization, validation, canonical entities, and their persistence.
- Identity owns authoritative identity links and resolution decisions.
- Business Intelligence owns business metrics, verified facts, and business issues.
- Business Graph projects canonical entities and verified relationships; it does not establish business truth.
- Business Memory owns durable knowledge and retrieval; AI explains grounded context and proposes actions.
- Business Configuration owns configurable thresholds and preferences; observability owns measured runtime results.
- Overview & Monitoring and Business Operations consume reliability projections and operational context.
- Prototype Simulation supplies reproducible inputs and expected outcomes through real application paths.

Observability must not establish provider accounts, refresh OAuth tokens, implement every external connector, create a second order/customer database, perform authoritative identity resolution, calculate revenue/ROAS, or turn an integration outage into a `BusinessIssue`.

This is a backend implementation. Build usable DRF APIs and internal service contracts, with appropriate admin visibility. Do not introduce a frontend application or a new technology stack.

## 5. Design the missing pieces without expanding into unrelated modules

The following names and structures are implementation suggestions, not models or contracts already defined by the feature documents. Choose the smallest clear design that meets the requirements and explain material choices.

### Persistence

Reuse `IntegrationSyncLog` for run history instead of creating a competing sync source of truth. Add explicit fields or closely related records for missing entity context, trigger mode, checkpoints, counters, parent retry runs, and progress where needed. Keep sync mode such as full/incremental separate from trigger origin such as manual/scheduled/replay.

Provide persisted representations for:

- Connection health observations and latest health projection, including communication success, failure, authentication state, credential usability, latency, and observation time.
- Provider request outcomes and provider/capability health evidence, including success/failure category, response status, latency, rate-limit context, target scope, and observation window.
- Webhook receipt, validation, routing, processing, duplication, timings, failures, and replay attempts. These observe ingestion; they do not replace the integration-owned receiver.
- Failed external records, including source, connection, entity type, external identifier, raw payload reference, failed stage, error classification, retry/review state, resolution, and attempt history.
- Classified integration errors, including severity, safe technical details, user-facing explanation, fingerprint, correlation, first/last occurrence, occurrence count, and lifecycle history.
- Freshness per business, connection, and entity category, including expected intervals, reliable watermarks, last valid update, observation time, and explicit reason for unavailable/unknown state.
- Durable identities or receipts for observations and operational requests where necessary to enforce idempotency.

Use appropriate indexes, uniqueness constraints, foreign keys, timestamp defaults for new fields, and deletion rules. Preserve historical evidence. Enforce consistent business/connection/provider relationships in services and serializers and with database constraints where feasible. Validate nonnegative counters, coherent timestamps, permitted statuses, and legal transitions.

Do not hide important queryable lifecycle or identity fields inside unstructured JSON. Use JSON for bounded provider-specific metadata. Do not copy the entire SQL reference schema into the project.

### Application structure

Keep application logic out of views and serializers. A package such as `app/observability/` may contain services, selectors, typed inputs/results, health/freshness policies, error classification, redaction, event handlers, and integration-operation interfaces. Keep model discovery correct and preserve existing imports, especially `app.models.VectorField` referenced by migrations.

Do not reorganize the whole project merely to introduce this module. If converting `app/tests.py` into an `app/tests/` package, preserve the original status endpoint test and avoid conflicting file/package names.

### Integration seams

Because real connector workflows are absent at this baseline, introduce narrow, tested contracts to receive actual observations and delegate connectivity tests, sync retries, record retries, and webhook replay to their integration/processing owner.

Implement a deterministic mock boundary for the supported prototype operations. Exercise the real observability orchestration, persistence, handlers, permissions, and API projections with it. Mark simulated outcomes explicitly; do not present a simulated result as a successful live-provider action.

Do not call an unimplemented adapter, set `status = SUCCESS`, and claim retry/replay works. A live capability without an implementation must return an explicit unsupported/unavailable result with no false state changes. For supported mock capabilities, implement and test the complete delegated operation and its observed outcome. Do not claim canonical persistence occurred unless the processing owner actually confirms it.

Avoid adding Celery, Redis, Kafka, Prometheus, or another platform dependency by default. A synchronous execution path plus explicit management commands is acceptable for this prototype. Return an asynchronous accepted response only when a real durable execution mechanism exists.

## 6. Implement all eight feature areas

### A. Connection Health

Implement business-scoped list/detail views and internal recording/query services for:

- Connection lifecycle visibility: connected, disconnected, expired, disabled, and relevant existing states.
- Separately derived observed health: healthy, degraded, error, or unknown, with reason codes and evidence.
- Delegated connectivity testing for supported capabilities and display of past test results.
- Authentication and credential usability without returning credentials.
- Last successful communication, latest failure, recent error aggregation, observation age, latency, and degradation due to partial failures or elevated errors.
- Centralized summaries across configured connections.

Keep administrative lifecycle state, observed health, and data freshness separate. A stale dataset is not automatically a disconnected connection. Disabled connections must not generate misleading active-outage alerts. No recent observations must not become a fabricated healthy state.

Define and test deterministic status precedence and the mapping to the simplified document statuses: `HEALTHY`, `DEGRADED`, `ERROR`, `STALE`, `DISCONNECTED`, `UNKNOWN`. Preserve detailed dimensions even when returning a simplified summary.

### B. Sync Monitoring

Observe pending/running/terminal runs; full/incremental modes; manual/scheduled/replay origins; provider, connection, and entity; start time, elapsed time, progress, safe cursor/checkpoint context, and partial failures.

Support discovered/received, processed, succeeded, skipped, and failed counts as applicable. Define the exact semantics and accounting invariants before implementation, including how existing counter fields map to them. Do not double count the same record or confuse retry attempt totals with unique record outcomes. Expose unknown progress honestly when a provider supplies no total.

Reject impossible state transitions and invalid counts. Distinguish a run that completed with record failures from both a clean completion and a total failure. Observe stalled/overdue runs when the configured monitoring policy supplies an expectation.

### C. Sync History

Provide paginated history and detail with execution times, duration, result counters, provider/entity context, mode/trigger, safe metadata, error references, retry relationships, and retry attempt outcomes.

Retain the original failed run when retrying; represent the new attempt explicitly. Support filters for connection, provider, entity, status, mode, origin, and time range. Derive historical duration/failure summaries from persisted runs with documented windows.

### D. Failed Records

Capture and inspect failures from retrieval, mapping, normalization, validation, identity-resolution input, and persistence. Preserve provider/connection/entity/external ID, payload reference, failure stage/code/message, occurrence timing, processing correlation, attempts, review state, and resolution evidence.

Support classification, grouping of similar failures, manual inspection/review, delegated retry, and traceable resolution. Preserve history after success. A repeated unsuccessful retry must remain visible with its attempt history. Distinguish a successful processing retry from an administrative acknowledgement, ignore, or manual closure; administrative actions must not advance data freshness.

Use bounded retry policies and explicit recoverable versus nonrecoverable classifications. Delegate execution and backoff policy to the integration boundary. Do not sleep inside request handlers or automatically retry invalid credentials/signatures forever.

### E. Webhook Monitoring

Observe provider/event identity, receipt, signature validation, routing, processing, duplicates, failures, provider event time when available, receive/process times, and retry/replay attempts.

Expose transport latency and processing latency separately when their timestamps exist. Missing or inconsistent provider times must produce an explained unavailable/invalid measure, not fabricated or negative latency.

Use provider-appropriate deduplication scoped to the correct business and connection. Preserve delivery attempts without processing the canonical event twice. Document conservative behavior when a provider supplies no stable event identifier.

Replay supported, eligible failed events through the same integration validation/routing/processing boundary. Never bypass signature validation, silently mark an invalid signature valid, trust an unverified payload, or allow an API caller to replace immutable captured content. A validation failure remains rejected unless the integration's documented validation policy establishes eligibility. Unsupported or ineligible replay must be explicit and leave trusted state unchanged.

### F. Data Freshness

Implement `FRESH`, `DELAYED`, `STALE`, and `UNAVAILABLE` source/entity classifications, with thresholds, age, last reliable update/watermark, evaluation time, and reason codes.

Read freshness expectations and monitoring preferences from a narrow Business Configuration contract. Reuse its implementation if present; if absent, provide minimal validated configuration storage or a documented config adapter, with explicit default values and override precedence. Do not implement the entire configuration domain. Keep configurable policy distinct from observed runtime state.

Test exact threshold boundaries. Use timezone-aware timestamps and the business timezone for local reporting boundaries. Make the evaluation clock injectable or otherwise deterministic in tests.

Successful connectivity, webhook receipt, a completed sync, and valid canonical data are distinct signals. Do not advance entity freshness from a failed or merely received record. An empty poll must not claim new data was received; if a provider can attest current coverage without changes, represent that separately and document how it affects trust. Partial success updates only the entity coverage it actually establishes.

Track source/event time, original reception time, processing confirmation, and coverage watermark where available. Late events and replayed old payloads must not move freshness backward or falsely make old source coverage current. Document fallback behavior when source timestamps are unavailable. Do not infer freshness solely from `IntegrationConnection.last_successful_sync_at`.

Return reusable reliability context for dashboards, Business Intelligence, and AI: status, as-of time, age, coverage/completeness warning, source/entity, and evidence/reason references. Implement this contract without building those other modules or requiring an LLM.

### G. Provider Health

Observe availability, response outcomes, latency, rate limits, error rates, degraded capabilities, and cross-connection impact. Return `HEALTHY`, `DEGRADED`, `UNAVAILABLE`, or `UNKNOWN` with a documented window, sample count, and evidence.

Separate a business's revoked token from a provider outage. Consider the scope of the provider target: an individual self-hosted WooCommerce store, endpoint, account quota, region, or capability may fail without the entire provider being unavailable. Do not declare a global outage from one tenant's authentication problem or insufficient samples.

Define deterministic thresholds, sample requirements, expiry of old observations, and recovery behavior. Handle zero observations and zero denominators explicitly. Separate connection-specific rate limits from evidence of broader provider degradation.

Provider-wide summaries may use appropriately aggregated telemetry, but tenant-facing responses must not expose another business's account names, connection IDs, payloads, errors, or identifying counts. Keep detailed cross-business diagnosis limited to an explicit privileged policy.

### H. Integration Errors

Implement a centralized business-scoped error view covering authentication, connectivity, provider API, rate limit, webhook, sync, mapping, normalization, validation, and internal processing failures.

Preserve classification/code, severity, provider, connection, entity/external ID, optional sync/webhook/failed-record references, safe technical context, readable explanation, correlation, first/last seen, occurrence count, and status.

Support active/acknowledged/resolved/ignored lifecycle behavior with valid transitions, actor/time/note history, and a documented recurrence/reopening policy.

Deduplicate repeated instances of an underlying failure with a stable, scope-aware fingerprint. Distinct observations of that problem increment occurrence count; re-delivery of the same observation must not increment it twice. Prevent lost increments under concurrency. Do not merge errors across businesses or unrelated causes.

Acknowledging, ignoring, or manually resolving an error does not repair the underlying connection or refresh data. Health must remain grounded in observations.

## 7. Event wiring, consistency, and operational reliability

Define explicit typed observation/service contracts for connection checks, provider requests, sync start/progress/completion, webhook reception/validation/processing, record failures/successes, and reliability changes. Event names are your design choice; document them instead of assuming they already exist.

Wire handlers through a deliberate application startup path. Prevent duplicate subscriptions under repeated initialization. Test actual dispatch-to-persistence behavior; direct calls to a handler alone do not verify event wiring.

Treat event payloads as untrusted inputs. Validate referenced businesses, connections, sources, syncs, webhooks, timestamps, identifiers, and statuses. Do not accept a caller-supplied business ID when the referenced connection belongs to another business.

Make accepted observation handling atomic and idempotent. Use database-enforced identities/constraints and appropriate transaction/locking or atomic update behavior for counters and state transitions. Duplicate deliveries, duplicate action submissions, concurrent retries, and out-of-order observations must have deterministic outcomes.

Respect transaction boundaries between source processing and observability. Do not publish an apparent canonical success before its transaction commits. Choose a tested post-commit or durable recording approach where needed, and make recording failures visible without making false claims about durable delivery. Do not portray the existing in-memory dispatcher as a queue or outbox.

Avoid network calls in list/detail GET requests. Recompute time-based health/freshness safely at query time or through an explicit refresh command; stale persisted snapshots must not remain healthy indefinitely simply because no new event arrived.

## 8. Authorization, data protection, and API contract

Every observability query and operation must enforce authorization for the selected business. `IsAuthenticated` plus an arbitrary URL `business_id` is insufficient.

Inspect available authorization first. If there is still no business access mechanism, implement the smallest explicit access/grant mechanism required for this module, such as a minimal membership/grant model and reusable permission helper. Define read versus manage permissions and explicit privileged provider-wide access. Do not build a general organization/role management product, and do not default to access for all authenticated users.

Reject cross-business object references in URL parameters, filters, request bodies, services, and events. Protect list, detail, aggregation, retry, replay, resolution, and raw-payload access consistently. Use the selected DRF authentication scheme's documented unauthorized status and a consistent policy for concealed cross-business objects. Test both authorized and denied paths.

Treat credentials, headers, raw provider payloads, cursors, config, exception strings, and nested metadata as potentially sensitive. Return safe allowlisted projections and recursively redact sensitive fields in diagnostic representations. Do not serialize whole connection configs or exceptions blindly. Never store authorization headers or token values as ordinary observation details. Preserve replay material through the integration-owned protected payload/reference mechanism, not by exposing it through list endpoints or destructively sanitizing the only usable original.

A suitable URL namespace is:

```text
/api/businesses/<business_id>/observability/
```

Implement and document a coherent contract covering at least:

| Method | Relative route | Required behavior |
| --- | --- | --- |
| GET | `summary/` | Coherent connection/sync/failure/webhook/freshness/provider/error reliability summary. |
| GET | `connections/`, `connections/<id>/` | Business connection health, reasons, timing, freshness and recent-error context. |
| POST | `connections/<id>/test/` | Authorized delegated connection test, with honest capability/result reporting. |
| GET | `syncs/`, `syncs/<id>/` | Active monitoring and historical run detail; active/history distinguished by documented filters. |
| POST | `syncs/<id>/retry/` | Authorized delegated retry with original/new run linkage and idempotency. |
| GET | `failed-records/`, `failed-records/<id>/` | Inspection, classification, grouping, review, and attempt/resolution context. |
| POST | `failed-records/<id>/retry/` | Eligible delegated processing retry and recorded outcome. |
| POST/PATCH | Documented failed-record review/resolution route | Traceable administrative review/resolution, distinguished from processing success. |
| GET | `webhooks/`, `webhooks/<id>/` | Receipt, validation, routing, processing, duplication, latency, and attempt context. |
| POST | `webhooks/<id>/replay/` | Eligible delegated replay through trusted processing with recorded outcome. |
| GET | `freshness/` | Source/entity freshness, thresholds, timestamps, coverage warnings, and reasons. |
| GET | `providers/`, `providers/<id>/` | Safe provider/capability health and evidence. |
| GET | `errors/`, `errors/<id>/` | Classified, grouped errors with occurrence and lifecycle context. |
| POST/PATCH | Documented error lifecycle routes | Authorized acknowledgement, resolution, and ignore actions. |

Adjust route naming if an established project convention exists, but preserve the complete behavior and document the final names. Do not add public unauthenticated telemetry ingestion merely to make demonstrations easy; internal services/events are sufficient.

Use explicit serializers, validated filtering and ordering, bounded pagination, stable ordering, time ranges, consistent enum values, timezone-aware ISO timestamps, and structured validation errors. Apply provider/connection/entity/status/time filters where relevant. Invalid filters must not silently widen access or raise an unhandled exception.

Return reason codes, evidence references, and readable impact alongside simplified statuses. Include an evaluation/as-of time so consumers can understand what the response describes. Avoid double counting one failure as separate unrelated incidents in the summary.

Use efficient selectors and grouped queries. Avoid per-connection/per-record query loops, unbounded payload responses, and unbounded history scans. Add a meaningful query-growth regression check for representative collection endpoints.

## 9. Required tests: implement each behavior after its failing test

Use Django `TestCase`, DRF `APITestCase`, and `TransactionTestCase` where appropriate. Reuse the current test runner unless there is a clear reason to add dependencies. Keep ordinary tests fast, deterministic, isolated from live providers, and independent of actual sleeping or wall-clock changes. Mock external boundaries and clocks, not the services, policies, persistence, or API behavior being verified.

Build an explicit matrix linking **every feature and subfeature in the observability specification** to implementation and test evidence. The cases below are the minimum behavioral coverage, not a replacement for that matrix:

1. **Baseline and schema:** preserve `/api/`; create/apply new migrations on a disposable fresh database; upgrade from the existing migration with representative integration rows preserved; validate constraints and migration drift.
2. **Connection health:** successful check, authentication rejection, expired/disabled/disconnected states, degraded observations, missing/old observations, last-success/last-failure timestamps, and scoped error summaries.
3. **Sync state and counters:** pending/running/completed/partial/failed paths; mode versus trigger origin; entity/provider filtering; unknown progress; safe cursor display; valid duration; invalid counters/transitions; duplicate progress; retry linkage; stalled-run policy when configured.
4. **Sync history:** pagination/order/time filtering, retained failed runs, retry outcomes, and duration/failure summaries.
5. **Failed records:** each supported stage/classification, source identity, safe payload reference, grouped failures, manual review, retry success, retry failure, nonrecoverable/unsupported retry, attempt limits, history preservation, and administrative closure without false data success.
6. **Webhooks:** receipt versus validation versus processing; valid success; invalid signature; routing/processing failure; duplicate delivery; replay eligibility; replay success/failure; repeated replay request; replay without usable payload; latency with missing/skewed timestamps; no bypass of validation; no duplicate canonical operation.
7. **Freshness:** fresh/delayed/stale/unavailable; exact thresholds; per-business/connection/entity isolation; default/override precedence and invalid config; timezone boundaries; failed/empty/partial syncs; late/out-of-order updates; old replay; clock control; no false refresh from connectivity or administrative actions.
8. **Provider health:** healthy/degraded/unavailable/unknown; latency/error windows; minimum samples; old evidence expiry; zero denominators; capability/target scope; 429/rate-limit handling; recovery; individual token failure versus provider-wide failure; safe cross-connection aggregation.
9. **Errors:** classification/severity/context; fingerprint grouping; distinct occurrence increments; duplicate observation suppression; concurrent increment behavior; lifecycle transitions; recurrence/reopening; sanitized technical detail; acknowledgement/ignore without fabricated recovery.
10. **Authorization:** anonymous denial; authenticated user without grants; permitted reader; permitted manager; denied reader mutation; different businesses; cross-business URL/body/filter/FK/event injection; privileged provider detail policy; protected payload access.
11. **Idempotency and ordering:** repeated and concurrent events/actions do not duplicate observations, runs, processing, resolution, or counters; late observations do not overwrite newer projections incorrectly.
12. **Events and transactions:** real event dispatch persists expected state; startup does not register handlers twice; committed versus rolled-back processing produces correct observations; failures do not leave partial accepted state or false success.
13. **API behavior:** pagination, validated filters/order/time windows, empty datasets, malformed inputs, missing objects, unsupported capabilities, consistent enums/errors, safe serializers, and summary coherence.
14. **Performance and confidentiality:** collection queries remain bounded as data grows; no cross-business leaks, token/config/header exposure, unsafe nested metadata, or accidental raw payload dumps.
15. **Downstream context:** deterministic reusable freshness/reliability context includes as-of/evidence/warnings and does not create business facts/issues or invoke an LLM.
16. **End-to-end prototype:** deterministic source observations pass through the real recording/event/orchestration path, database, selectors, serializers, permissions, and API; assert meaningful final state rather than merely HTTP 200.

Where correctness depends on PostgreSQL locking or concurrency semantics, validate it on PostgreSQL using appropriate transactional tests. SQLite cannot prove `select_for_update` behavior. Clearly distinguish portable tests from database-specific tests and report the exact databases used. Do not silently skip required database checks and claim full concurrency validation.

## 10. Deterministic demonstration and acceptance scenarios

Provide a repeatable management command or similarly runnable demonstration, with explicit business scope, seed, fixed evaluation time, expected results, and a failing exit status when validation fails. Reuse existing simulation models where useful without implementing all Prototype Simulation features.

Feed observations through the real module entry points; do not seed final health/error/freshness rows as the only proof. Namespace demo records and make repeat runs predictable without clearing existing business data. Keep mock/provider outcomes explicit.

Include these scenarios:

- **Healthy baseline:** a supported mock connection check succeeds, valid entity processing is confirmed, and the API reports healthy connection and fresh data with supporting times.
- **Partial sync:** a deterministic run has successes, a skipped record, and a mapping/validation failure. The run is partial, counters reconcile, the failed record is inspectable, and its grouped error is visible. A supported retry preserves history and updates the observed processing outcome correctly.
- **Webhook failure from the specification:** WooCommerce has 37 distinct signature-validation failures and its last successful order update was 52 minutes before the fixed evaluation time. Assert degraded connection context, 37 failed webhook events, a grouped `WEBHOOK_SIGNATURE_INVALID` error with 37 occurrences, the correct configured freshness classification, and one coherent reliability warning. Re-delivering those same observations must not double the counts. Rejected signatures must not enter trusted processing.
- **Isolated authentication problem:** one business's Meta token is invalid; that connection reports the problem without declaring every business's Meta provider unavailable.
- **Broader provider failure:** sufficient scoped timeout/5xx/latency observations across appropriate targets demonstrate provider/capability degradation, with safe tenant-facing detail.
- **Freshness and replay:** time passes without a valid update and data becomes stale; replaying an old event does not falsely reset source coverage to now. A genuinely new, confirmed update restores only the appropriate source/entity freshness.
- **Access boundary:** a second business exists, and its data cannot be read, counted, referenced, retried, replayed, or resolved by the first business's user.

Use these scenarios as automated acceptance tests as well as a documented runnable demo. They must run without live provider credentials or an LLM.

## 11. Suggested implementation sequence

1. Inspect the complete project and establish baseline/runtime/database facts.
2. Build the traceability matrix and document state/counter/freshness/authorization contracts.
3. Write failing persistence, validation, and business-access tests; add the minimal models, grants if needed, and additive migrations.
4. Write failing observation/event/idempotency tests; implement recording services and reliable startup wiring.
5. Implement connection and provider health through their failing policy/service/API tests.
6. Implement sync monitoring/history and failed-record lifecycle through their failing tests.
7. Implement webhook monitoring and delegated retry/replay through their failing tests.
8. Implement source/entity freshness and downstream reliability context through boundary and stale/replay tests.
9. Implement error aggregation/lifecycle and coherent summary projections through their failing tests.
10. Complete permissions, API filters/pagination, admin visibility, and performance checks.
11. Add deterministic acceptance scenarios and the runnable demonstration through their tests.
12. Audit every documented subfeature, run final checks, fix defects in the same loop, and deliver evidence.

Reorder slices when dependencies justify it. Keep the test-first loop intact and maintain a usable integrated path as the module develops.

## 12. Final completion gates

Use the actual configured project runtime or documented container equivalent. At minimum, run:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test app
python manage.py test
git diff --check
```

Focused tests should have been run throughout development. Avoid repeating equivalent full suites after they pass unless a subsequent change or unresolved concern requires it. If the full suite includes all module tests, one final full run can provide both module and regression evidence; report that clearly.

Additionally:

- Apply migrations on a disposable fresh database and exercise the upgrade path from the current migration. Run `python manage.py migrate --noinput` only against that explicitly configured disposable database, never against the tracked working database as a validation shortcut.
- Run required PostgreSQL-specific transactional checks when making PostgreSQL concurrency claims. Resolve environment/database setup honestly, including any existing `vector` extension requirement; do not change unrelated behavior merely to force tests to run.
- Run the deterministic demonstration and validate its expected outcomes.
- Review the final diff for unrelated changes, exposed credentials/payloads, unregistered handlers/models, missing migrations, placeholder feature paths, unbounded queries, and modifications to `db.sqlite3`.
- Recheck the traceability matrix: every required subfeature must be implemented and verified. A discovered omission returns the task to the loop.
- Recheck final documentation against the actual routes, enums, configuration, commands, runtime, and database behavior.

If a check fails, diagnose and repair it, add a regression test first where needed, and rerun the affected checks. After the final code change, rerun the final gates affected by that change. Do not call the module complete while known required tests, migrations, scenarios, or feature requirements are failing or unverified.

## 13. Required deliverables and final response

Deliver:

- Working backend code for all eight observability areas.
- Additive migrations and appropriate model/admin registration.
- Tested recording/event contracts, policies, selectors, permissions, APIs, and delegated mock operations.
- Deterministic unit, service, API, transactional where required, and end-to-end acceptance tests.
- A repeatable demonstration with expected results.
- `docs/implementations/integration-data-observability.md` describing architecture, model changes, ownership boundaries, event contracts, status/counter semantics, thresholds, access policy, routes with request/response examples, retry/replay limitations, setup, test commands, and demo commands.
- The completed progress/traceability document with actual verification evidence.

Do not claim live integrations exist merely because the prototype integration boundary is exercised. Clearly identify supported mock operations and any explicit unsupported live capabilities. That limitation must not be used to omit the module's required observability behavior.

In the final response, state what now works, the main files changed, migrations/configuration required, exact commands run and their actual results/test counts, supported operational paths, and any remaining blocker or limitation. Keep the response evidence-based. A green test suite without the completed feature checklist is insufficient; a completed checklist without executed required checks is also insufficient.

**Begin with repository understanding and baseline checks. Then write the first failing behavioral tests and keep executing the test → implement → test → repair → regression loop until the module satisfies the documented requirements and completion gates.**
