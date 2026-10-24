# Bizora — final domain increment and integration readiness

24 October 2026 · branch `feat/business-domains`.

## Result and scope

A working Django operational UI now covers all thirteen Business Operations groups. Source-aware
product intake, safer canonical inputs, explicit unknown manual confidence, non-destructive merge
planning and seven swappable owner contracts extend the existing backend without replacing it.

**298 requirements: 229 COMPLETE, 66 PARTIAL, 3 BLOCKED, 0 NOT STARTED.**
The [full Markdown audit](my-domains-requirements-audit.md) and [JSON inventory](domain-requirements-audit.json)
preserve every original subfeature/description/source line and current code/test evidence.
The original specifications retain their actual filenames under `docs/implementations/features/`:
`business-data.md`, `identity-resulation.md`, `business-oparations.md`.

| Domain | COMPLETE | PARTIAL | BLOCKED | Domain status |
| --- | ---: | ---: | ---: | --- |
| Business Data | 95 | 20 | 0 | PARTIAL |
| Identity & Resolution | 50 | 6 | 3 | PARTIAL |
| Business Operations | 84 | 40 | 0 | PARTIAL |

Unfinished responsibilities: **2 PARTIAL/A local decisions**, **61 PARTIAL/B external owner
integrations**, **3 PARTIAL/C merge lifecycle outcomes**, **3 BLOCKED/C merge requirements**.
A/B/C describes responsibility; it does not upgrade a fallback or fixture to completed behavior.
Some audit upgrades reflect correcting an earlier overly broad demand for arbitrary matching engines,
which the source specification does not require. They are not counted as newly written matching code.
Full graph journeys, AI generation, authoritative BI calculations and live provider transport are
not complete and are never presented as working. The integration handoff is
[TEAM_LEAD_HANDOFF.md](TEAM_LEAD_HANDOFF.md); detailed interfaces are [contracts/README.md](contracts/README.md).

## Existing implementation preserved

The starting tree had **195 tests**. It already implemented canonical intake/lifecycle, source-scoped
hash receipts, monetary/order/refund invariants, immutable order snapshots, catalog/variants/images,
customer contacts/tags/references/timeline, conversations/messages/attachments/notes, assignment and
handover, campaign hierarchy/raw reported metrics/conversions, visitors/sessions/events, shipments,
calls/transcripts/callbacks, exact and corroborated identity matching, login/purchase journey recovery,
conflicts/history, review-only merge candidates, tenant-safe evidence and bounded operational APIs.
Those systems remain authoritative; this increment adds **50 meaningful tests** (49 readiness tests
and one PostgreSQL race), bringing full discovery to **245**. No duplicate operations database exists.

## Architecture and conventions

- Python 3.11.17; Django 4.2.27; DRF 3.15.2; psycopg 3.2.9; pip/requirements.txt unchanged.
  Python 3.12 Dockerfile runtime was not separately tested. No dependencies were installed.
- Existing ORM in `app/models.py` and unchanged `0001_initial.py` are the runtime source of truth.
  Alternative `db_diagram.sql` is not an executable replacement schema.
- APIs under `/api/businesses/{business_id}/` call typed validation and transactional domain services.
  Business Data owns canonical records; Identity links existing entities; Operations composes them.
- New UI under `/ops/` is isolated in `operations_ui.py`, `operations_urls.py`, templates and template
  tags. Lists reuse existing authenticated APIs; details/commands call existing projections/services.
  UI can be replaced by a future frontend without changing canonical services or creating tables.
- VIEWER reads, OPERATOR canonical/support writes, MANAGER/OWNER identity and proposal review.
  Membership is required even for a Django superuser. Session writes enforce CSRF; Basic auth is
  supported for localhost/HTTPS API access. UI logout is POST only and login redirects are host-checked.
- PostgreSQL locks a business row to serialize mutations. DB constraints are the final guard.
  SQLite does not prove SELECT FOR UPDATE or multi-writer safety. Five real PG races are exercised.
- Money remains finite nonnegative Decimal with two fractional digits. Pending refunds reserve
  capacity; completed refunds derive payment refund state. No FX/revenue/BI calculation is invented.
- Receipts scope event IDs by business/connection and hash payloads; changed replay, stale updates
  and invalid relationships reject atomically. New reviewed intake uses the same service and receipts.
- External owner contracts validate scope/version/request ID, finite JSON, minimum result schemas,
  known nested entity references and fixture provenance. Owner-specific analytical semantics and
  opaque identifiers still require the supplying owner's schema; envelope validation is not proof
  of every business assertion.

সহজ বাংলায়: মূল customer/order/payment এক জায়গাতেই থাকে। Identity বিভিন্ন source-এর ID-কে
প্রমাণ দিয়ে সেই মূল record-এর সঙ্গে যুক্ত করে। Operations UI ওই record-গুলো দেখায় এবং অনুমোদিত
command চালায়। Adapter হলো অন্য দলের implementation লাগানোর নির্দিষ্ট সংযোগস্থান। Dry-run শুধু
কোন relationship প্রভাবিত হবে তা পরীক্ষা করে; কোনো customer মুছে বা merge করে না।

## New code and exact executable evidence

The following symbols and tests support the new behavior. The exhaustive audit cites group
integration tests; that is not a claim of one independent acceptance test per prose sentence.

| Implemented behavior | Source | Test evidence |
| --- | --- | --- |
| Source-aware preflight; source/reference + reviewed identity reuse; shared SKU review and explicit manager distinct-product decision | [`app/domains/catalog.py:assess_product`](../../app/domains/catalog.py#L5) | [`app/test_integration_readiness.py:ProductIntakeReviewTests`](../../app/test_integration_readiness.py#L14) |
| Contradictory source mappings/identity links cannot overwrite a product; SKU/external-ID whitespace cannot bypass review | [`app/domains/data.py:ingest`](../../app/domains/data.py#L126) | [`app/test_integration_readiness.py:SourceContradictionAndMergeRaceTests.test_source_mapping_and_reviewed_identity_contradiction_does_not_overwrite`](../../app/test_integration_readiness.py#L470)<br>[`app/test_integration_readiness.py:IdentifierWhitespaceTests`](../../app/test_integration_readiness.py#L553) |
| Attachment type/MIME/metadata/filename/size/URL safety, atomic rejection of bad nested files | [`app/domains/data.py:_attachment`](../../app/domains/data.py#L58) | [`app/test_integration_readiness.py:AttachmentContractTests`](../../app/test_integration_readiness.py#L69) |
| Manual link confidence remains unknown; nested identifiers reject malformed values; full recorded refund required for an operational refunded-order command | [`app/domains/identity.py:_link`](../../app/domains/identity.py#L80) | [`app/test_integration_readiness.py:FinalCorrectnessTests`](../../app/test_integration_readiness.py#L318) |
| Tenant-safe current non-purchase product/customer context, joined with purchase history | [`app/domains/projections.py:detail`](../../app/domains/projections.py#L78) | [`app/test_integration_readiness.py:ProductRelationshipContextTests`](../../app/test_integration_readiness.py#L585) |
| Versioned seven-owner input/output schemas, no-adapter/timeout fallback, nested scope checks, configured adapters and fixture provenance | [`app/domains/boundaries.py:exchange`](../../app/domains/boundaries.py#L55)<br>[`app/domains/boundaries.py:configured_adapter`](../../app/domains/boundaries.py#L36) | [`app/test_integration_readiness.py:ExternalBoundaryContractTests`](../../app/test_integration_readiness.py#L87)<br>[`app/test_integration_readiness.py:AdapterConfigurationTests`](../../app/test_integration_readiness.py#L436)<br>[`app/test_integration_readiness.py:OwnerUIConnectionTests`](../../app/test_integration_readiness.py#L501) |
| Versioned canonical ingress simulation and outbound preparation; no provider execution or credentials | [`app/domains/mock_transport.py:MockCanonicalTransport`](../../app/domains/mock_transport.py#L54)<br>[`app/domains/contracts.py:prepare_operation`](../../app/domains/contracts.py#L54) | [`app/test_integration_readiness.py:FinalCorrectnessTests.test_fixture_ingress_is_versioned_replay_safe_and_never_accepts_live_source`](../../app/test_integration_readiness.py#L348)<br>[`app/test_integration_readiness.py:ExternalBoundaryContractTests`](../../app/test_integration_readiness.py#L87) |
| Merge ORM/polymorphic/receipt inventory and fingerprint; successful/rejected/missing/unsafe/stale owner acknowledgements, never destructive execution | [`app/domains/merge.py:plan`](../../app/domains/merge.py#L17)<br>[`app/domains/merge.py:dry_run`](../../app/domains/merge.py#L65) | [`app/test_integration_readiness.py:MergeReadinessTests`](../../app/test_integration_readiness.py#L137)<br>[`app/test_integration_readiness.py:SourceContradictionAndMergeRaceTests.test_relationship_change_during_adapter_reconciliation_rejects_stale_plan`](../../app/test_integration_readiness.py#L482) |
| All 13 UI sections plus identity review, canonical lists, details, search/filter/pagination, empty states, role/tenant/CSRF/XSS/redirect safety | [`app/operations_ui.py:section`](../../app/operations_ui.py#L98)<br>[`app/operations_ui.py:resources`](../../app/operations_ui.py#L136)<br>[`app/operations_ui.py:detail`](../../app/operations_ui.py#L188)<br>[`app/operations_ui.py:command`](../../app/operations_ui.py#L199) | [`app/test_integration_readiness.py:OperationsUITests`](../../app/test_integration_readiness.py#L205) |
| Variant creation/edit and external mapping; conflict/merge review; queue channel/priority/assignment filters | [`app/operations_ui.py:command_forms`](../../app/operations_ui.py#L49)<br>[`app/operations_ui.py:command`](../../app/operations_ui.py#L199) | [`app/test_integration_readiness.py:AdditionalUIWorkflowTests`](../../app/test_integration_readiness.py#L370) |
| Financial chronology, evidence-backed proposal approval and observed website errors; no action execution | [`app/operations_ui.py:financial_timeline`](../../app/operations_ui.py#L266)<br>[`app/operations_ui.py:command`](../../app/operations_ui.py#L199) | [`app/test_integration_readiness.py:FinancialAndActionUITests`](../../app/test_integration_readiness.py#L512) |
| Pending media reference save/replay and safe file-reference links; private notes never enter outbound message requests | [`app/templatetags/operations.py:reference_link`](../../app/templatetags/operations.py#L50)<br>[`app/operations_ui.py:command`](../../app/operations_ui.py#L199) | [`app/test_integration_readiness.py:MediaReplyUITests`](../../app/test_integration_readiness.py#L568)<br>[`app/test_integration_readiness.py:FinalProjectionSecurityTests`](../../app/test_integration_readiness.py#L414) |
| PostgreSQL simultaneous new product SKU intake creates one product and requires review for the competing event | [`app/domains/data.py:ingest`](../../app/domains/data.py#L126) | [`app/test_domains.py:PostgresConcurrencyTests.test_concurrent_product_sku_intake_requires_review_instead_of_duplicate`](../../app/test_domains.py#L1006) |

## Operational UI and APIs

UI entry: `/ops/login/` and `/ops/`; select an owned business. Section URLs:
`/ops/business/{id}/{overview|customers|products|orders|payments|inbox|queue|assignment|handover|marketing|website|delivery|calls}/`.
Additional pages: `identity/` (manager), `financial-timeline/`, `resources/{resource}/`,
`records/{resource}/{id}/`. All canonical resource lists have authenticated rendering/empty-state tests.
UI commands support lifecycle changes, priority, assignment/release, AI/human handling-state handover,
private notes, read acknowledgement, pending text/media, variant create/edit/source mapping, refunds,
callback requests/scheduling and manager conflict/candidate/proposal review. Source mapping and agent/
team IDs are checked against business membership/ownership. Invalid commands show escaped feedback.

Native forms/details, visible labels, unique field IDs, focus outlines, skip navigation, table headings,
responsive wrapping and horizontal table scrolling are provided. No external asset/CDN is required.
Rendering/workflows are tested with Django clients; no browser automation, visual screenshot review,
formal accessibility audit or high-load benchmark is claimed.

Canonical API resources remain explicitly allowlisted in `registry.RESOURCES`, with paginated
GET/validated idempotent POST, bounded detail/context, explicit lifecycle commands and no arbitrary
PATCH/DELETE. Existing overview/360/financial/support/inbox/website/identity routes remain available.
New API seams:

| Endpoint suffix under `/api/businesses/{id}/` | Contract |
| --- | --- |
| `POST products/assess/` | Existing canonical envelope, returns CREATE/REUSE/REVIEW; preflight does not create |
| `POST identity/merge-candidates/{id}/dry-run/` | Optional expected_fingerprint only; clients cannot inject adapter acknowledgements |
| `POST contracts/{owner-slug}/{capability}/` | `{request_id,payload}`, seven owner contracts, typed unavailable/rejected/available result |

Owner slugs/capabilities and complete input/output examples are in the contract document. Existing
`operations/{operation}/{id}/prepare/` is versioned `bizora.outbound.v1`; its request uses canonical
uppercase entity types. It never sends/submits/calls/cancels a provider operation.

## Database and migration safety

New migration: `app/migrations/0008_identity_confidence_unknown.py`, nullable IdentityLink confidence.
New manual links use NULL. Existing stored confidence values are not rewritten or reinterpreted. New ID/SKU trimming does not backfill earlier rows; inspect historical whitespace variants before shared-data deployment.
Previous additive migrations 0002–0007 remain; baseline 0001 is unchanged. Fresh migrations through
0008 and no-drift checks pass on both backends. Applying existing uniqueness constraints to a
populated shared DB still needs reviewed duplicate preflight and migration/data-preservation planning.

Only isolated databases were used. Local settings point outside the repository and Django tests use
isolated test databases. The checked-in legacy `db.sqlite3` SHA-256 is unchanged:
`b8ae586e334293f514cec76dab130cdd342096b5c1615655a4a1d58efa9097d1`.
PostgreSQL verification uses a new localhost pgvector container with tmpfs/random credentials and
port, bootstraps vector before migration and removes only that container. No existing Compose volume,
production database, credential or service was used. SQLite vector columns do not prove vector search.

## Verification and regression results

Final captured outputs: [SQLite suite](verification/sqlite-tests.txt),
[PostgreSQL migrations/suite](verification/postgresql-tests.txt),
[fresh SQLite migrations/repeat demo/UI smoke](verification/sqlite-migrations.txt),
[focused readiness suite](verification/readiness-tests.txt).

| Check | Actual result |
| --- | --- |
| Full SQLite suite | **245 discovered; 240 passed; 5 skipped; 0 failures/errors** |
| Full PostgreSQL/pgvector suite | **245 discovered; 243 passed; 2 skipped; 0 failures/errors** |
| Focused readiness suite | **49 passed; no skips/failures/errors** |
| Both backends check / makemigrations --check --dry-run / fresh migration / preflight | Passed through 0008; no schema drift |
| Fresh isolated SQLite demo twice | Passed; stable canonical IDs |
| Fresh database UI smoke | All 13 sections and manager identity page returned 200 |
| Audit generator | All 298 rows / 31 groups; cited code/test symbols resolve |
| git diff --check / branch / legacy hash | Passed; feat/business-domains; legacy hash unchanged |

The 195 existing tests remain. New tests are 49 readiness tests plus one PG race = **50 new**.
SQLite skips five real PostgreSQL concurrency cases: receipt replay, competing refunds, variant
upsert, identity deactivation/resolution, product SKU duplicate prevention. PostgreSQL skips the two
intentionally SQLite-only local demos. Disposable verification containers were removed.

Focused tests first exposed a merge envelope expecting entity_id where a merge has source/target
IDs; validation was corrected and focused/full suites rerun. Integration preparation was tightened
so MESSAGE_SEND cannot refer to a CUSTOMER: it validates the real canonical message and connection
and forbids payload overrides. Final runs include all fixes and existing regression tests.

## Remaining gaps and immediate decisions

**A (2 PARTIAL):** Shipment Detail View still keeps arbitrary raw provider metadata private; agree
safe public provider-diagnostic fields before exposing it. Merge Confidence retains deterministic
verified-contact confidence and unknown product-SKU confidence; no calibrated graded scoring policy
is invented. These local decisions are not falsely attributed to an external implementation blocker.

**B (61 PARTIAL):** Local UI/input/read/fallback/request contracts exist, but real source adapters,
provider transport/attachment/recording access, BI attribution/revenue/funnels/support/region analyses,
full Graph journeys, AI generation, knowledge policy retrieval, configured overdue/escalation policies
and real freshness/health still need owner implementations. Result containers are not an exhaustive
schema for each owner's analytics/policy data. Agree semantic/provenance schemas and operational
timeouts before connecting a real adapter. Context sections cap at 50 with count/truncation; use
paginated resource lists. Owner result arrays are bounded at 1000 with optional owner continuation.

**C:** consolidation, downstream relationship preservation and completed merge history remain BLOCKED;
MERGED lifecycle/match provenance/review terminal outcomes are PARTIAL for the same reason. The new
plan/dry-run inventories actual ORM relationships and validates owner reconciliation responses, but
cannot discover arbitrary embedded JSON/provider references/external stores. Acknowledgements are not
persisted leases or atomic preservation guarantees. Even unanimous fixture success never executes.
A future reviewed executor needs durable/expiring owner preparation, redirects/reprojection,
transaction/failure/retry semantics and audit preservation. `execute_merge` stays blocked.

Large-data performance is unbenchmarked: recursive ownership checks, bounded context assembly and
merge inventory hash scans favor correctness. Unexpected owner-specific identifiers/content still
need domain-specific schema validation. UI uses recorded/imported state; pending messages and
callback schedules do not imply actual delivery/calls. No background execution was introduced.

## Verified demonstration

Use the existing virtualenv. No dependency installation is needed for these commands:

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

Open `http://127.0.0.1:8000/ops/`, sign in and select the demo business. The command prints actual
UI/API URLs and reuses its guarded isolated simulated source. It demonstrates canonical records,
verified corroboration/login journey recovery and support context/priority. Browse all 13 sections;
record notes, pending media, assignments/handover and evidence-backed review. Unavailable owner
capabilities remain explicit. No fake AI advice, analytics, identity matches or live provider success.

## Changed files and integration readiness

New: `app/operations_ui.py`, `app/operations_urls.py`, `app/templates/operations/*`,
`app/templatetags/operations.py`, `app/domains/catalog.py`, `boundaries.py`, `merge.py`,
`app/test_integration_readiness.py`, migration 0008, `TEAM_LEAD_HANDOFF.md`, contract documentation/examples.
Updated: `bizora/urls.py` (mount only), `app/urls.py`, `domain_views.py`, `models.py`,
`domains/common.py`, `data.py`, `identity.py`, `registry.py`, `projections.py`, `contracts.py`,
`mock_transport.py`, `management/commands/demo_completion.py`, `app/test_domains.py` (new race),
README, audit generator/Markdown/JSON, implementation report and captured verification logs.

The existing baseline already contains the previous domain increments. Review tracked changes and newly added untracked files.
No commit, push, merge, branch switch, dependency install, destructive existing-database operation
or production access occurred. Other teams' implementations were not replaced. Root URL/model edits
are the minimal shared wiring/schema changes for these owned domain features.

**Ready for integration/PR review as a tested increment; not full completion of all three domains
or an approved populated-database deployment.** Follow the handoff's explicit merge/migration,
adapter wiring and combined-suite checks. No PR was opened automatically.

## All 31 feature groups

A group is COMPLETE only when every subfeature is COMPLETE. Per-row remaining behavior and source
requirements are preserved in the exhaustive audit.

| Domain / group | COMPLETE | PARTIAL | BLOCKED | Group status |
| --- | ---: | ---: | ---: | --- |
| business-data / Product | 7 | 1 | 0 | PARTIAL |
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
| identity-resulation / Identity Linking | 6 | 1 | 0 | PARTIAL |
| identity-resulation / Cross-Source Matching | 8 | 0 | 0 | COMPLETE |
| identity-resulation / Anonymous Identity Linking | 5 | 2 | 0 | PARTIAL |
| identity-resulation / Merge Detection | 4 | 2 | 2 | PARTIAL |
| identity-resulation / Identity Conflict Resolution | 9 | 0 | 0 | COMPLETE |
| identity-resulation / Identity History | 6 | 0 | 1 | PARTIAL |
| business-oparations / Business Overview | 2 | 4 | 0 | PARTIAL |
| business-oparations / Customer 360 | 9 | 3 | 0 | PARTIAL |
| business-oparations / Product Operations | 7 | 3 | 0 | PARTIAL |
| business-oparations / Order Operations | 9 | 2 | 0 | PARTIAL |
| business-oparations / Payment Operations | 8 | 0 | 0 | COMPLETE |
| business-oparations / Unified Inbox | 7 | 2 | 0 | PARTIAL |
| business-oparations / Support Queue | 5 | 3 | 0 | PARTIAL |
| business-oparations / Conversation Assignment | 8 | 0 | 0 | COMPLETE |
| business-oparations / AI ↔ Human Handover | 5 | 3 | 0 | PARTIAL |
| business-oparations / Marketing Operations | 5 | 5 | 0 | PARTIAL |
| business-oparations / Website Performance | 3 | 8 | 0 | PARTIAL |
| business-oparations / Delivery Operations | 6 | 5 | 0 | PARTIAL |
| business-oparations / Call Operations | 10 | 2 | 0 | PARTIAL |

## Final closeout decisions and repository hygiene

No new runtime feature, scoring policy or migration was added during final closeout.
The two PARTIAL/A items remain intentionally explicit:

| Local item | Current safe behavior | Exact decision needed before local implementation |
| --- | --- | --- |
| Shipment diagnostics | Canonical recipient/status/tracking/charges/COD and stored event timeline are available; raw provider payloads remain private. No live tracking request is made. | Team lead + Integrations approve a versioned allowlist of public diagnostic fields, their types/meaning, credential/PII redaction and VIEWER/OPERATOR visibility. Then implement only that projection with tenant/redaction tests; do not copy authoritative shipment data. |
| Merge confidence | Existing shared verified-contact candidates use 1 for a matching predicate; this is not a calibrated probability of one real entity. Shared SKU confidence is unknown; manual link confidence is NULL. Review does not execute a merge. | Team lead + Identity owner choose rule-evidence score versus calibrated probability, rule versions and evidence/thresholds for any graded values. No guessed scores, automatic approval, legacy-score reinterpretation or backfill before that decision. Physical consolidation still requires downstream preservation guarantees. |

Final rerun: SQLite **245 tests: 240 passed / 5 skipped**; PostgreSQL **245 tests: 243 passed /
2 skipped**; zero failures/errors. Both backends passed system checks, migration consistency and
fresh migrations through 0008, plus preflight. Audit remains **229 COMPLETE / 66 PARTIAL /
3 BLOCKED** across all 298 requirements. Seven owner schemas/examples/API slugs, all four contract
versions and thirteen operational section routes agree. Other teams' implementations were not built.

`.gitignore` now covers environment variants, virtualenvs, local DB/sidecar files, temporary files,
private-key files and generated caches. Modified/addable paths had no prohibited artifacts or
credential-pattern findings; this was a scoped filename/pattern check, not a comprehensive security
audit. Ignored secret files were not opened. Public test fixture passwords are test data, not
production credentials. Nothing is staged. The repository's **already tracked** `db.sqlite3` remains
unchanged and outside this diff; ignore rules do not remove a tracked file. No database, environment,
cache or temporary artifact was newly added. Intentional sanitized verification logs are retained.

Closeout evidence: [fresh SQLite checks and suite](verification/sqlite-tests.txt),
[fresh PostgreSQL checks and suite](verification/postgresql-tests.txt), and
[contract/hygiene checks](verification/closeout-checks.txt).
No commit, push, merge or branch switch was performed. Safe for integration review with the
above decisions and external dependencies still open; not 298/298 completion or deployment approval.
