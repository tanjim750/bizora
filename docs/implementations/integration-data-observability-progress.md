# Integration & Data Observability — implementation progress

Branch: `codex/integration-data-observability`.

## Contracts and decisions

- Reuse the existing integer-keyed ORM and `IntegrationSyncLog`; additive migrations only.
- Implement observability services/selectors/API under `app/observability/`; registered models remain available through `app.models`.
- Lifecycle, observed connection health, provider health, and entity freshness are separate dimensions.
- Sync `processed = succeeded + skipped + failed`, bounded by received; discovered is optional. Progress observations are absolute snapshots, not increments. Retries create new runs.
- Freshness uses a monotonic source coverage watermark and original reception fallback, never retry time. Defaults: delayed after 900 seconds, stale after 1800; connection/entity overrides take precedence over business defaults.
- Explicit business grants: READER and MANAGER; superusers may inspect provider-wide evidence. No implicit access for other authenticated users.
- Internal observations are idempotent by business/connection/event identity; operational actions require idempotency keys. Mutations lock the connection to serialize related changes on PostgreSQL.
- Retry/replay delegates to an integration boundary. Supported prototype operations are explicit mocks; live capabilities are unsupported until an adapter is registered.
- Original payloads remain behind a protected integration-owned reference; diagnostic projections are allowlisted/redacted.

## Baseline

- Previous inspection: 61 ORM models, one migration, one status API test; domain documents include all eight observability features (81 named subfeatures).
- Branch creation succeeded after requesting Git metadata access through the sandbox.
- Host Python 3.14 lacked project dependencies; Python 3.12.14 was selected from the bundled runtime. Dependencies were installed in /tmp/bizora-test-venv after the sandboxed network attempt failed.
- No developer database writes performed.

## Engineering loop evidence

- Baseline: Python 3.12.14 temporary environment; pinned dependencies installed. Original 1 test, Django checks, and migration drift check passed.
- Policies: RED missing policy module; GREEN 7 deterministic tests covering exact freshness boundaries, missing/future data, provider failure scopes, rate limits, latency, and recursive redaction.
- Persistence/recording: RED missing BusinessAccess/recording services; implemented additive migration, seven observation kinds, idempotency receipts, atomic recording, startup registration, and separate health/freshness state. First run exposed nullable-field validation and fixture timing errors; corrected optional-field validation and made synthetic reception follow observation time. Terminal-transition fixture now uses a later event so it tests transitions rather than intentionally ignored late events.
- Integrated regression after recording: 23 tests passed; no migration drift.
- API slice: RED missing views; GREEN 15 API tests, including grants, all collections, safe detail, signature-failure coherence, lifecycle, policy override, pagination/filter validation, and bounded query growth.
- Operational slice: RED missing payload boundary; GREEN 14 tests. Mock retries/replay persist real canonical products through a Business Data boundary, preserve immutable source payloads and original timestamps, and record idempotent attempts. Failed attempts expose backoff/limits; unsupported live adapters do not claim success. Injection test exposed malformed DRF serializer error shape; corrected structured validation errors.
- Edge-case slice: RED 11 failures/3 errors; GREEN 18 tests after fixing invalid grants/IDs, inconsistent signature evidence, unsupported resource filters, strict policy numbers, failure grouping, local-day duration statistics, audit timestamps, and incomplete partial syncs. Integrated suite then passed 70 tests.
- Runtime/migrations: RED environment selection and legacy-accounting tests; GREEN 3 tests after adding explicit PostgreSQL/disposable SQLite configuration and preserving existing counters as LEGACY instead of guessing missing success counts. Drift check passed.
- Real PostgreSQL 16 + pgvector: 4 concurrent transactional tests passed (duplicate observations, occurrence increments, identical retry requests, and competing retries). Sandboxed localhost access required an authorized escalation; the first Docker inventory review timed out and its single retry succeeded.
- Demo/skipped-record slice: RED missing command and incorrect late-duplicate accounting; GREEN demo and operation tests (18 combined). Ten-record partial runs now reconcile 8 successes, 1 skipped late duplicate, and 1 failure through actual product processing.

## Feature checklist

| Area | Status | Evidence |
| --- | --- | --- |
| Connection health | Implemented | Connection observations, error/latency/quota patterns, lifecycle and summaries; API/edge tests |
| Sync monitoring | Implemented | Absolute accounting, state transitions, stalled runs, cursor and progress; recording/edge tests |
| Sync history | Implemented | Retry lineage, legacy preservation, business-local duration statistics; migration/operation tests |
| Failed records | Implemented | All stages, grouping, review, protected diagnostics, real recovery; API/operation/edge tests |
| Webhook monitoring | Implemented | Validation, timing, deliveries, duplicate suppression and trusted replay; recording/API/operation tests |
| Data freshness | Implemented | Exact thresholds, monotonic coverage, completeness and policy precedence; policy/recording/edge tests |
| Provider health | Implemented | Scoped capabilities, cross-connection evidence and privacy; policy/edge/demo tests |
| Integration errors | Implemented | Every category/severity, occurrence deduplication and audited lifecycle; recording/edge/transaction tests |
| Grants, redaction, validation | Implemented | Explicit grants, manager diagnostics, strict inputs, superuser admin; API/admin tests |
| Events, idempotency, transactions | Implemented | Startup registration, commit/rollback and real PostgreSQL competing requests; recording/publication/transaction tests |
| APIs and query growth | Implemented | Validated filters, pagination, field projections and bounded collection queries; API tests |
| Deterministic demo and acceptance | Implemented | Repeatable command with 13 expectations; tampering fails; demo tests |
| Migrations and final gates | Verified | Additive 0002, fresh/upgrade checks, 96 PostgreSQL tests, and 13 demo checks passed |

## Remaining work

Implementation and final verification are complete. No feature area remains unimplemented. Live operation adapters beyond the explicit PRODUCT prototype remain an integration-owner capability, not a claimed implementation.

## Per-subfeature traceability (81 documented requirements)

Implementation references below are under `app/observability/`; test references are modules under `app/tests/`. Cross-cutting invariants additionally run in the PostgreSQL concurrency suite. Verification results are recorded above and in final gates below.

| ID | Requirement | Implementation | Behavioral test evidence |
| --- | --- | --- | --- |
| 1.1 | Connection Health / Connection Status | `services.py: connection_check; selectors.py: connection_snapshots` | `test_observability_api; test_observability_edges; test_observability_operations` |
| 1.2 | Connection Health / Connectivity Testing | `services.py: connection_check; selectors.py: connection_snapshots` | `test_observability_api; test_observability_edges; test_observability_operations` |
| 1.3 | Connection Health / Authentication Health | `services.py: connection_check; selectors.py: connection_snapshots` | `test_observability_api; test_observability_edges; test_observability_operations` |
| 1.4 | Connection Health / Credential Status | `services.py: connection_check; selectors.py: connection_snapshots` | `test_observability_api; test_observability_edges; test_observability_operations` |
| 1.5 | Connection Health / Last Successful Connection | `services.py: connection_check; selectors.py: connection_snapshots` | `test_observability_api; test_observability_edges; test_observability_operations` |
| 1.6 | Connection Health / Last Failure | `services.py: connection_check; selectors.py: connection_snapshots` | `test_observability_api; test_observability_edges; test_observability_operations` |
| 1.7 | Connection Health / Connection-Level Error Summary | `services.py: connection_check; selectors.py: connection_snapshots` | `test_observability_api; test_observability_edges; test_observability_operations` |
| 1.8 | Connection Health / Degraded Connection Detection | `services.py: connection_check; selectors.py: connection_snapshots` | `test_observability_api; test_observability_edges; test_observability_operations` |
| 1.9 | Connection Health / Connection Health View | `services.py: connection_check; selectors.py: connection_snapshots` | `test_observability_api; test_observability_edges; test_observability_operations` |
| 2.1 | Sync Monitoring / Active Sync Visibility | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 2.2 | Sync Monitoring / Sync Type Tracking | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 2.3 | Sync Monitoring / Sync Progress | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 2.4 | Sync Monitoring / Sync Status | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 2.5 | Sync Monitoring / Entity-Level Sync Monitoring | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 2.6 | Sync Monitoring / Provider-Level Monitoring | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 2.7 | Sync Monitoring / Sync Duration | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 2.8 | Sync Monitoring / Current Cursor State | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 2.9 | Sync Monitoring / Manual Sync Trigger Context | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 2.10 | Sync Monitoring / Partial Failure Detection | `services.py: _sync; serializers.py: SyncSerializer` | `test_observability_recording; test_observability_operations; test_observability_edges` |
| 3.1 | Sync History / Historical Sync Records | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 3.2 | Sync History / Execution Time | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 3.3 | Sync History / Sync Result Summary | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 3.4 | Sync History / Sync Type History | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 3.5 | Sync History / Failure History | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 3.6 | Sync History / Duration History | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 3.7 | Sync History / Provider History | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 3.8 | Sync History / Entity History | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 3.9 | Sync History / Retry Visibility | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 3.10 | Sync History / Troubleshooting Context | `views.py: syncs/statistics; serializers.py: SyncSerializer` | `test_observability_migrations; test_observability_operations; test_observability_edges` |
| 4.1 | Failed Records / Failed Record Capture | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 4.2 | Failed Records / Source Identification | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 4.3 | Failed Records / Raw Payload Reference | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 4.4 | Failed Records / Failure Stage | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 4.5 | Failed Records / Failure Reason | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 4.6 | Failed Records / Error Classification | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 4.7 | Failed Records / Retry Status | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 4.8 | Failed Records / Manual Review | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 4.9 | Failed Records / Resolution Tracking | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 4.10 | Failed Records / Failure Aggregation | `services.py: _failure; operations.py; lifecycle.py; views.py: GroupsView/PayloadDiagnosticView` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges` |
| 5.1 | Webhook Monitoring / Webhook Event Log | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.2 | Webhook Monitoring / Provider Identification | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.3 | Webhook Monitoring / Webhook Type Tracking | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.4 | Webhook Monitoring / Reception Status | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.5 | Webhook Monitoring / Validation Status | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.6 | Webhook Monitoring / Processing Status | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.7 | Webhook Monitoring / Webhook Latency | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.8 | Webhook Monitoring / Duplicate Detection | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.9 | Webhook Monitoring / Failed Webhooks | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.10 | Webhook Monitoring / Webhook Retry Visibility | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 5.11 | Webhook Monitoring / Webhook Replay | `services.py: _webhook; operations.py: _replay_webhook; serializers.py: WebhookSerializer` | `test_observability_recording; test_observability_operations; test_observability_api; test_observability_edges; test_observability_demo` |
| 6.1 | Data Freshness / Last Successful Data Update | `services.py: _confirmed; policies.py: freshness; selectors.py: Policies/connection_snapshots` | `test_observability_policies; test_observability_recording; test_observability_api; test_observability_edges; test_observability_demo` |
| 6.2 | Data Freshness / Source Freshness | `services.py: _confirmed; policies.py: freshness; selectors.py: Policies/connection_snapshots` | `test_observability_policies; test_observability_recording; test_observability_api; test_observability_edges; test_observability_demo` |
| 6.3 | Data Freshness / Entity-Level Freshness | `services.py: _confirmed; policies.py: freshness; selectors.py: Policies/connection_snapshots` | `test_observability_policies; test_observability_recording; test_observability_api; test_observability_edges; test_observability_demo` |
| 6.4 | Data Freshness / Expected Update Interval | `services.py: _confirmed; policies.py: freshness; selectors.py: Policies/connection_snapshots` | `test_observability_policies; test_observability_recording; test_observability_api; test_observability_edges; test_observability_demo` |
| 6.5 | Data Freshness / Stale Data Detection | `services.py: _confirmed; policies.py: freshness; selectors.py: Policies/connection_snapshots` | `test_observability_policies; test_observability_recording; test_observability_api; test_observability_edges; test_observability_demo` |
| 6.6 | Data Freshness / Freshness Status | `services.py: _confirmed; policies.py: freshness; selectors.py: Policies/connection_snapshots` | `test_observability_policies; test_observability_recording; test_observability_api; test_observability_edges; test_observability_demo` |
| 6.7 | Data Freshness / Freshness Age | `services.py: _confirmed; policies.py: freshness; selectors.py: Policies/connection_snapshots` | `test_observability_policies; test_observability_recording; test_observability_api; test_observability_edges; test_observability_demo` |
| 6.8 | Data Freshness / Dashboard Freshness Indicators | `services.py: _confirmed; policies.py: freshness; selectors.py: Policies/connection_snapshots` | `test_observability_policies; test_observability_recording; test_observability_api; test_observability_edges; test_observability_demo` |
| 6.9 | Data Freshness / AI Freshness Context | `services.py: _confirmed; policies.py: freshness; selectors.py: Policies/connection_snapshots` | `test_observability_policies; test_observability_recording; test_observability_api; test_observability_edges; test_observability_demo` |
| 7.1 | Provider Health / Provider Availability | `services.py: provider_request; policies.py: classify_provider; selectors.py: provider_snapshots` | `test_observability_policies; test_observability_edges; test_observability_demo` |
| 7.2 | Provider Health / API Response Monitoring | `services.py: provider_request; policies.py: classify_provider; selectors.py: provider_snapshots` | `test_observability_policies; test_observability_edges; test_observability_demo` |
| 7.3 | Provider Health / Provider Latency | `services.py: provider_request; policies.py: classify_provider; selectors.py: provider_snapshots` | `test_observability_policies; test_observability_edges; test_observability_demo` |
| 7.4 | Provider Health / Rate Limit Monitoring | `services.py: provider_request; policies.py: classify_provider; selectors.py: provider_snapshots` | `test_observability_policies; test_observability_edges; test_observability_demo` |
| 7.5 | Provider Health / Provider Error Rate | `services.py: provider_request; policies.py: classify_provider; selectors.py: provider_snapshots` | `test_observability_policies; test_observability_edges; test_observability_demo` |
| 7.6 | Provider Health / Provider Degradation Detection | `services.py: provider_request; policies.py: classify_provider; selectors.py: provider_snapshots` | `test_observability_policies; test_observability_edges; test_observability_demo` |
| 7.7 | Provider Health / Cross-Connection Impact | `services.py: provider_request; policies.py: classify_provider; selectors.py: provider_snapshots` | `test_observability_policies; test_observability_edges; test_observability_demo` |
| 7.8 | Provider Health / Provider Capability Health | `services.py: provider_request; policies.py: classify_provider; selectors.py: provider_snapshots` | `test_observability_policies; test_observability_edges; test_observability_demo` |
| 7.9 | Provider Health / Provider Health Status | `services.py: provider_request; policies.py: classify_provider; selectors.py: provider_snapshots` | `test_observability_policies; test_observability_edges; test_observability_demo` |
| 8.1 | Integration Errors / Centralized Error Log | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.2 | Integration Errors / Error Classification | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.3 | Integration Errors / Error Severity | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.4 | Integration Errors / Provider Context | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.5 | Integration Errors / Connection Context | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.6 | Integration Errors / Entity Context | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.7 | Integration Errors / Sync Context | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.8 | Integration Errors / Webhook Context | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.9 | Integration Errors / Raw Error Details | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.10 | Integration Errors / Human-Readable Error Message | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.11 | Integration Errors / Error Deduplication | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.12 | Integration Errors / Occurrence Tracking | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |
| 8.13 | Integration Errors / Resolution Status | `services.py: _error; lifecycle.py; serializers.py: ErrorSerializer` | `test_observability_recording; test_observability_edges; test_observability_api; test_observability_transactions` |

## Final review corrections

- Added protected manager-only, redacted, audited payload diagnostics and safe webhook delivery history; corresponding RED tests then passed. Evidence admin is read-only and superuser-only.
- Added recent connection error-rate and approaching/exhausted quota signals through failing tests.
- Fixed disconnected-versus-disabled summary behavior, entity-monitoring suppression, unavailable/incomplete data warnings, and incoherent source times through four failing behavioral tests.
- Legacy migration now preserves actual historical observation times, in addition to unchanged counters; the new migration assertion first failed on migration-time substitution.
- Fixed queue wait being counted as execution duration: the focused RED test now passes; pending starts are null, RUNNING establishes start, and unknown terminal start yields unknown duration.
- Before the last duration fix, all 92 PostgreSQL tests passed without skips; SQLite passed 88 with 4 explicitly database-specific skips. The final suite now contains 93 tests and will be rerun on both databases.

## Final verification — 26 October 2026 (Asia/Dhaka)

Runtime: Python 3.12.14, pinned Django/DRF/psycopg requirements, temporary environment `/tmp/bizora-test-venv`.

| Gate | Actual result |
| --- | --- |
| `python manage.py check` | PASS; no issues. |
| `python manage.py makemigrations --check --dry-run` | PASS; no changes detected. |
| `python manage.py test` on SQLite | PASS: 96 discovered, 92 passed, 4 explicit PostgreSQL-only skips. |
| `python manage.py test` on PostgreSQL 16 + pgvector | PASS: all 96 tests, no skips; includes all 4 concurrent transactional tests. |
| Fresh disposable SQLite `migrate --noinput` | PASS: original migration and additive 0002 applied. |
| `simulate_observability --seed 75001 --at 2026-10-25T12:00:00+00:00` | PASS: all 13 expected outcomes; fresh command and deterministic rerun verified. |
| Upgrade from 0001 | PASS in both full suites; existing tenant/connection rows, counters, and historical times preserved. |
| `git diff --check` / staged diff whitespace | PASS. |
| Developer `db.sqlite3` | Unchanged. |

Final redaction regression covered inline tokens and Basic authorization text. Final ownership regression first failed in two ways: non-product owners could not confirm their domain, and an owner's explicit rejection was ignored. The implemented confirmation interface now delegates that proof to the canonical processing owner; the mock product owner verifies actual scoped persistence, a registered test order owner works through the same generic orchestration, and rejected confirmations roll back without false freshness. Both focused tests and both complete suites pass.

Repeat the PostgreSQL run against a disposable pgvector-enabled database with `BIZORA_DATABASE=postgresql POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55439 POSTGRES_DB=bizora_observability POSTGRES_USER=postgres POSTGRES_PASSWORD=bizora-test-only /tmp/bizora-test-venv/bin/python manage.py test`. The `vector` extension was enabled in that disposable database and its `template1` before initial migration. The temporary test container is removed after verification.

Supported shipped execution is explicitly the deterministic PRODUCT mock adapter, connection checks, and generic owner-registered operation contracts. No live provider adapter, background queue, external account setup, or LLM behavior is claimed. All eight observability areas accept/project their documented observations independently of those integration-owner capabilities.
