# Bizora: team-lead handoff

Branch: `feat/business-domains`. No commit, push, merge or branch switch was performed.
This is an integration-ready increment for review, **not completion of all 298 requirements**.

## Ownership and readiness

| Domain | Owns | Current full-requirement assessment |
| --- | --- | --- |
| Business Data | Canonical product/customer/order/payment/refund/message/support/campaign/website/shipment/call records; validation, lifecycle, lookup and replay | 95 COMPLETE / 20 PARTIAL |
| Identity & Resolution | Deterministic matching, registry/links/conflicts/history, review and non-destructive merge planning | 50 COMPLETE / 6 PARTIAL / 3 BLOCKED |
| Business Operations | Authenticated operational APIs/UI, authorized commands, current evidence/context consumption and proposal approval | 84 COMPLETE / 40 PARTIAL |

Total **229 COMPLETE / 66 PARTIAL / 3 BLOCKED / 0 NOT STARTED**.
[All 298 assessments](my-domains-requirements-audit.md) · [machine-readable audit](domain-requirements-audit.json) ·
[full implementation report and evidence](my-domains-implementation-report.md).

Unfinished responsibility: 2 PARTIAL/A local decisions, 61 PARTIAL/B owner integrations,
3 PARTIAL/C merge lifecycle outcomes and 3 BLOCKED/C merge execution/preservation/history.

## Entry points

- Canonical intake: `app.domains.data.ingest`; lookup/search: `queries.lookup` and `conversation_search`.
- Product preflight/review: `catalog.assess_product`; API `POST /api/businesses/{id}/products/assess/`.
- Identity: `app.domains.identity`; manager API `/api/businesses/{id}/identity/{command}/`.
- Merge planning: `merge.plan`, `merge.dry_run`;
  `POST /api/businesses/{id}/identity/merge-candidates/{id}/dry-run/`.
- Operations: `operations.assign/handover/review_action/set_priority/schedule_callback`;
  `projections.overview/customer360/detail/financial_timeline/support_context/graph_context`.
- Existing domain APIs remain under `/api/businesses/{id}/`; new external owner seam is
  `POST contracts/{integrations|bi|graph|ai|memory|configuration|monitoring}/{capability}/`.
- UI login/business selection: `/ops/login/`, `/ops/`.
  All 13 sections: `/ops/business/{id}/{overview|customers|products|orders|payments|inbox|queue|assignment|handover|marketing|website|delivery|calls}/`.
  Additional manager review: `identity/`; financial chronology: `financial-timeline/`.
  Record detail: `/ops/business/{id}/records/{resource}/{record_id}/`;
  additional canonical lists: `/ops/business/{id}/resources/{resource}/`.

UI code is isolated in `app/operations_ui.py`, `operations_urls.py`, `templates/operations/`
and `templatetags/operations.py`; shared root URLs only mount `/ops/`. It uses existing canonical
APIs for lists and existing services/projections for commands/details. Replace the templates
without replacing canonical services. No duplicate operational tables or frontend framework.

Roles: VIEWER reads; OPERATOR canonical/support writes; MANAGER/OWNER identity and proposal review.
Membership is required even for a Django superuser. Internal notes remain within authenticated
business scope and are excluded from provider message requests. Session writes require CSRF.

## Connect the other domains

Read [contracts/README.md](contracts/README.md) and [examples.json](contracts/examples.json).
`boundaries.Adapter.exchange` is the process-local protocol. `bizora.domain.v1` validates
version, tenant, correlation ID, required input/output shapes and simulation provenance.
Trusted server settings select adapters, not clients:

```python
BIZORA_DOMAIN_ADAPTERS = {
    "Business Intelligence": "your_bi.adapters.EntityContextAdapter",
    "Business Graph": "your_graph.adapters.EntityContextAdapter",
    "AI Intelligence": "your_ai.adapters.EntityContextAdapter",
    "Business Memory": "your_memory.adapters.PolicyContextAdapter",
    "Configuration": "your_configuration.adapters.PolicyAdapter",
    "Monitoring": "your_monitoring.adapters.FreshnessAdapter",
    "Integrations": "your_integrations.adapters.PreparationAdapter",
}
```

These are example paths, **not shipped services**. Missing adapters return UNAVAILABLE. UI detail
pages consume configured owner context; the future frontend can use the same API contract.
Existing persisted BI/Graph/AI records are also read through safe bounded projections.
Owners must supply their own semantics/provenance, authentication, transport and bounded timeouts.
Do not enable fixture adapters in a shared/production environment.

Input example (replace IDs with owned records):

```json
{"request_id":"customer-context-1","payload":{"entity_type":"CUSTOMER","entity_id":1}}
```

Use `POST /api/businesses/1/contracts/bi/entity_context/`. AVAILABLE output echoes scope/version/
request identity and contains `{facts:[],metrics:[],issues:[],evidence:[]}` with `simulated:false`
only for a real owner adapter. Empty fixture containers never imply generated findings.
Canonical inbound fixture version is `bizora.ingest.v1`; outbound preparation is
`bizora.outbound.v1`. Integration signatures/provider schema translation/credentials and execution
receipts remain the Integrations team's responsibility. No live transport was added here.

## Migrations and verification

Never migrate the tracked `db.sqlite3`. Its SHA-256 remains
`b8ae586e334293f514cec76dab130cdd342096b5c1615655a4a1d58efa9097d1`.
Runtime ORM plus migrations are authoritative; `db_diagram.sql` is not an alternative migration.

Migration chain: unchanged `0001_initial`; previous domain migrations `0002`–`0007`; this increment
adds **`0008_identity_confidence_unknown`** (nullable link confidence). New manual links use unknown
confidence rather than fabricated certainty. Existing stored confidence values are not rewritten.
Review duplicate preflight before applying earlier uniqueness constraints to any populated target.

```bash
export DJANGO_SETTINGS_MODULE=bizora.local_settings
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test --noinput
.venv/bin/python scripts/verify_domains_postgres.py
.venv/bin/python scripts/audit_domain_requirements.py
```

Final results: **245 discovered** (195 existing + 50 new). SQLite **240 passed / 5 skipped**;
PostgreSQL **243 passed / 2 skipped**; no failures/errors. SQLite skips five PostgreSQL races;
PostgreSQL skips two SQLite-only demos. Fresh migrations/preflight/schema-drift checks, repeat demo
and all 13 UI sections plus identity review passed on a fresh isolated SQLite database.
Captured logs are under [verification/](verification/).

The PostgreSQL verifier requires Docker + pgvector image, creates only a disposable localhost
container with tmpfs, random credentials/port and no existing volumes, then removes it.
Stock Compose does not bootstrap vector; do not substitute a shared Compose database for this test.

## Local demonstration

```bash
export DJANGO_SETTINGS_MODULE=bizora.local_settings
export BIZORA_DATA_DIR="$(mktemp -d /tmp/bizora-demo-XXXXXX)"
export DJANGO_SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py createsuperuser --username demo-owner
.venv/bin/python manage.py demo_completion --username demo-owner
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/ops/`, sign in, select the demo business. Re-run the demo to verify
stable canonical IDs. Explore Customer 360, orders/payments/refunds, inbox priority/assignment/
handover/private notes and pending media, shipment/call timelines, callback requests, observed
marketing/website records and manager review. Provider execution, generated AI and BI analysis
stay unavailable unless a real owner implementation supplies them. UI uses no external assets.

## Remaining decisions and integration steps

1. Review the complete current diff against the existing 195-test baseline. No automatic
   commit/PR was made. Inspect both tracked and newly added untracked files.
2. Compare incoming teams' model/migration changes; reconcile migrations deliberately in a separate
   integration checkout/branch according to your team's workflow. Do not overwrite shared models
   or the checked-in legacy DB. Preserve source IDs, invariants, constraints and permission checks.
3. Agree adapter result semantics: analytical dimensions/evidence, policy schema, freshness and
   authoritative relationship provenance. Run owner-provided contract tests before configuring paths.
4. Agree a safe public shipment diagnostic/metadata contract (raw provider payloads stay private)
   and merge candidate confidence semantics (product SKU confidence remains unknown). These are the
   two local PARTIAL/A items, not fabricated external implementation blockers.
5. Keep physical merge blocked. ORM inventory does not inspect arbitrary JSON/external stores;
   fixture acknowledgements are not preservation guarantees. BI/Graph/AI/Memory/Integrations/
   Configuration/Monitoring must review reconciliation; a future executor needs durable/expiring
   acknowledgements, redirects/reprojection, retries/failure semantics and audit preservation.
6. Integrations supplies real adapters, signatures, transport, attachment/recording access and
   delivery receipts. BI supplies analytics/attribution; Graph full journeys; AI generated output;
   Memory policies; Configuration SLA/escalation rules; Monitoring real freshness/health.
7. Run the full suites and fresh migrations against the combined tree, then review/prepare the PR
   and merge through your normal process. This branch is ready for integration review, not an
   approved existing-data deployment or a claim of all-domain completion.

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
