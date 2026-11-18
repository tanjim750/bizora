# Bizora runtime, browser and source audit — 19 November 2026

What this repo does: Bizora is a Django/DRF business operations backend with a Next.js client. It stores commerce, customer, support and identity records, exposes business intelligence and knowledge views, and keeps AI proposals behind approval controls. The assumed load is multiple staff working in separate businesses; the small local fixture does not establish production capacity.

Branch: `audit/runtime-security-2026-11-19`. Starting commit: `32fea97075c4678fab94bb0c458477aaca87480c`. The initial working tree was clean. Changes and tests were made on the new branch, without pushing or deploying.

Code commits: `02c9401` (Dialyra), `2defa82` (offline build), `0bec47f` (identity review and failure states), `ece93fd` (mobile layout).

## Verification results

| Check | Result |
| --- | --- |
| Python runtime | Python 3.12.16 |
| Django system check | No issues |
| Migration drift | `makemigrations --check --dry-run`: no changes |
| Complete Django suite | 1,569 discovered/run: **1,551 passed, 18 skipped, zero failures** |
| Frontend unit tests | **262 passed**, zero skipped |
| Production frontend build | Passed without network access after removing build-time font downloads |
| Full-stack Chrome suite | **16 passed**, zero skipped, with fresh disposable Django/Next.js services |
| Exploratory browser run | 24 workspace/tab URLs; invalid login; malformed queries; foreign business; 320 px navigation; configuration-service outage |
| Formatting | Changed frontend implementation and test files passed targeted Prettier checks |
| Production settings check | Two unresolved warnings: `security.W004` and `security.W008` |
| PostgreSQL 16/pgvector | **Not executed**; the 18 skipped tests cover PostgreSQL-specific behavior |
| Formal independent security audit | **Incomplete**; delegated sessions had no filesystem tools |

The app was actually started and used through a browser. Checks included login, workspace selection, all 32 canonical list endpoints, product-source review, a recorded refund, identity conflict resolution and merge approval, graph snapshot creation, viewer restrictions, foreign-tenant denial, CSRF rejection, logout, pagination, local signed courier callbacks, and mobile navigation. The merge approval test also checks that canonical identities remain active: approval does not execute a destructive merge.

Exploratory checks used browser automation and direct visual inspection. They are not human acceptance testing, a formal accessibility audit, or a cross-browser certification. All records and credentials were dummy fixtures. No real provider call, shipment, advertising request, email or payment was sent.

## Defects fixed

These were reproduced against the original code before their repair, or against the recorded original component for the configuration outage. Passing checks after the repair are recorded below. Priorities describe repair order; they are not an independently verified vulnerability rating.

| # | Priority | Problem and reproduction | Repair and verification |
| --- | --- | --- | --- |
| F1 | P1 | An anonymous POST to `/api/dialyra/webhook/` changed a dummy call from `INITIATED` to `COMPLETED` and could write its transcript. | [Webhook view](../app/dialyra_views.py) now requires a separate bearer secret for the URL business. The unscoped URL returns 410. Regression checks reject absent, wrong, foreign-business and non-ASCII tokens without writes. |
| F2 | P1 | Two businesses had calls with the same provider ID. A service bound to the second business updated the first business's call. | [Webhook lookup](../app/services/dialyra_service.py) now scopes and locks calls by business and Dialyra connection, including the metadata fallback. Tests cover tenant collisions, another provider's call and an unscoped service. |
| F3 | P2 | Conflict and merge review buttons returned HTTP 404. The frontend invented `/identity/.../{id}/review` URLs and sent the wrong conflict fields. | [Admin review handlers](../frontend/src/components/Admin.js) now use `review-conflict` and `review-merge`, with the backend's identifier and decision fields. Browser tests verify the saved decision and conflict reason. Errors are visible in the dialog. |
| F4 | P2 | Merge rows displayed `#` without IDs because the UI read `source_identity` and `target_identity`; the API returns `candidate_identity` and `primary_identity`. Conflict columns also read fields absent from that model. | The UI now reads the actual model fields. A browser regression checks both merge identity IDs. Existing canonical identity columns are preserved and checked. |
| F5 | P1 | A forced HTTP 503 from the merge planner produced a made-up plan and fingerprint, hiding the failure. | The UI clears any previous plan and shows the actual error. A browser test injects the 503 and checks that no fingerprint appears. Sample identity cards wired to real record IDs were also removed. |
| F6 | P1 | When the effective-configuration API returned 503, the UI labelled hardcoded sample regions and settings as “Authoritative System Configuration.” | The sample configuration was deleted. A disposable backend fault fixture reproduces the old display; the repaired screen shows “Configuration unavailable.” Other configuration views remain reachable. |
| F7 | P2 | `npm run build` failed offline because the root layout fetched three Google Fonts families. | The layout uses the existing installed-font/system fallback stacks. The real production build passes with external networking disabled. Exact fonts can differ between client machines. |
| F8 | P2 | Originate-call payloads such as `["phone"]`, `{"phone":123}` and a dictionary-valued phone raised `AttributeError` and HTTP 500. | Object and phone-type validation now return HTTP 400. A regression also checks that no provider transport is called. |
| F9 | P2 | At 320 px the business selector extended to x=216 while the search button began at x=154. Controls overlapped despite the page having no horizontal scrollbar. | Two `min-width: 0` constraints let the selector shrink within its flex container. The browser test now checks control bounds as well as scrolling and Escape behavior. |

Backend regressions are in [test_dialyra_security.py](../app/test_dialyra_security.py) and [test_dialyra.py](../app/test_dialyra.py). Browser regressions are in [identityReviews.spec.js](../frontend/tests/e2e/identityReviews.spec.js), [identity.spec.js](../frontend/tests/e2e/identity.spec.js) and [workspace.spec.js](../frontend/tests/e2e/workspace.spec.js). The full-stack runner now seeds real identity-review records rather than relying on sample cards.

## Must fix before a production sign-off

1. **PostgreSQL behavior still needs verification** (`scripts/verify_domains_postgres.py`; PostgreSQL-only transaction tests).
   - **What this is:** PostgreSQL 16 is the authoritative database. SQLite does not implement its row locks or pgvector behavior.
   - **Problem:** Eighteen tests were skipped. Passing SQLite tests does not prove concurrent refunds, replay handling, locking or vector queries on PostgreSQL.
   - **Fix:** Run the isolated PostgreSQL 16/pgvector verifier with disposable data and the required isolation. PostgreSQL server binaries were not available in this sandbox, and the host Docker socket was deliberately not exposed.
   - **If we skip it:** Money and concurrent-write behavior remain unverified on the actual database engine.

2. **Production HTTPS and serving configuration are unfinished** (`bizora/settings.py`; `Dockerfile:16`; `docker-compose.yml:4`).
   - **What this is:** Production needs an HTTPS entry point and an application server suitable for deployment.
   - **Problem:** The production check still reports unset HSTS and Django HTTPS redirect. Both container commands start Django's development server. The real ingress, certificate and proxy settings were not visible.
   - **Fix:** Choose the production WSGI/ASGI server and static-file setup; configure HTTPS at the edge or Django, then verify forwarded headers and secure login/write behavior. Enable HSTS only after the actual HTTPS setup is verified.
   - **If we skip it:** These templates do not establish a reviewed production deployment. This is a release gap, not proof that an unseen edge is insecure.

## Should fix

3. **Dialyra bypasses the managed credential-reference path** (`app/services/dialyra_service.py:108`; `app/configuration/integrations.py:183`).
   - **What this is:** Managed integration settings store business-specific environment references, resolved by `resolve_credentials`.
   - **Problem:** Dialyra instead reads raw `api_key`/`access_token` values from the connection or the process-wide `DIALYRA_API_KEY`. A connection configured only through managed references is not resolved by this client. Remote account/business binding is also not demonstrated locally.
   - **Fix:** Agree on the remote business/account mapping and migrate Dialyra to the existing credential resolver, with tests for disabled connections and credential changes. This needs an explicit compatibility plan for existing raw/global credentials; silently removing their fallback would break current setups.
   - **If we skip it:** Configuration can appear complete while the client uses a different credential source. This report does not claim a demonstrated remote cross-tenant leak.

4. **Required checks are not enforced by repository CI** (no `.github/workflows` directory in this checkout).
   - **What this is:** CI runs checks automatically for pull requests.
   - **Problem:** The new browser cases found defects that the existing source-string tests missed. No checked-in workflow requires these tests or PostgreSQL checks before a change merges.
   - **Fix:** Add Python 3.12/PostgreSQL 16, frontend unit/build, and full-stack browser jobs using disposable fixtures. Verify the jobs on the chosen CI runner before relying on them.
   - **If we skip it:** Developers must remember every local command, and the same integration mistakes can return.

## Product capabilities still missing or partial

These are scope gaps visible in the code and UI, not failed assertions or a claim that the entire domain is absent.

| Capability | Current limit | Smallest next step |
| --- | --- | --- |
| Final identity consolidation | `app/domains/merge.py` inventories and reconciles a plan but deliberately returns `execution: BLOCKED`. Approval alone does not merge records. | Complete downstream preservation contracts and an approved executor with PostgreSQL tests. |
| Knowledge authoring and semantic search in the UI | The knowledge screen/API provide lists and keyword search. Upload, edit and delete are absent there; ingestion services exist in Python. The UI explicitly says semantic search is unavailable. | Wire an approved authoring workflow to the existing ingestion services, then expose semantic retrieval only when the provider/index path is verified. |
| Executive revenue/retention analytics | `Overview.js` still marks revenue, AOV, delivery/tracking and trend sections as unavailable. BI service and API modules do exist and are mounted. | Connect the overview sections to authoritative metric observations and preserve honest unavailable states. |
| External owner/provider execution | Generic outbound preparation and owner contracts can return `UNAVAILABLE`. Local courier webhook tests and mocked Dialyra tests do not prove real delivery or calls. | Connect each owner adapter and run approved staging checks with its documented contract. |
| Real provider credential rotation and failure recovery | Local fixtures cannot establish remote scopes, expired-token handling, real carrier behavior or provider retries. | Have each integration owner validate those cases in isolated staging before enabling live execution. |
| Cross-browser, accessibility and user acceptance | Chrome desktop and 320 px were exercised. Human UAT, assistive technology, Safari/WebKit and Firefox behavior were not verified. | Run the existing [manual acceptance plan](manual_acceptance_plan.md) with named testers and supported devices. |
| Load, recovery and dependency security assurance | A 50-read local smoke check is not a capacity test. No fresh vulnerability advisory database or full dependency audit was available. | Define load/recovery targets and provision isolated performance and dependency checks. |

## Evidence and repeatability

The retained local run is `/home/naim/security-audit-skill/bizora/run-2/`, outside the repository. Each runtime invocation records its command, safe environment and limits in `agents/<name>/invocation.json`; its bounded output is in `agents/<name>/artifacts/evidence.log`.

Key runs:

- `baseline`: original backend check, migration drift and 1,561-test suite.
- `webhook-regression-before` / `webhook-regression-after`: unauthorized/cross-tenant behavior and repair.
- `call-input-before`: malformed call input raised server errors.
- `identity-contracts-before`: both review requests returned 404, IDs were blank, and the failed planner hid its error.
- `configuration-fault-before`: original `Admin.js` from the starting commit, with a disposable configuration-API outage.
- `mobile-before`: measured the overlapping controls.
- `final-backend`: complete 1,569-test backend run after backend changes.
- `release-browser`: final frontend unit/format/build and 16-test browser run.
- `exploratory-complete`: final exploratory navigation, invalid inputs, outage and screenshots.
- `visual-proof-final`: the same checks with screenshots captured after the graph and knowledge requests settle.
- `deployment-check`: the two remaining production warnings.

The exploratory scripts and exact fault fixture remain under the run's `inputs/` directory. The fault was inserted only in a disposable backend copy, never in tracked application source. Screenshots are promoted individually with fixed names and size limits; inspect the final exploratory artifacts for the desktop, 320 px, configuration, graph, knowledge and configuration-failure views.

The first browser attempts failed because the sandbox hid Chrome's `/etc/alternatives` link and because a 192-task limit was too small for Chrome plus both servers. Those were harness failures. The corrected runs used the actual Chrome executable and a bounded 512-task limit; they supersede those attempts. No app behavior was inferred from those failures. An invalid negative page-size probe returned Django REST Framework's default page rather than an error; it was not misreported as a security issue.

All execution used network, filesystem and process namespaces, an empty allowlisted environment, read-only installed dependencies, sanitized disposable source/data, bounded scratch storage, memory/CPU/process/file/time limits, and parent-side bounded artifact promotion. No packages were fetched. The existing `.env`, local database, user accounts and provider credentials were not used. Test servers were stopped by the runners.

For an already provisioned disposable local environment, the underlying checks are:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --noinput
cd frontend
npm test
npm run build
cd ..
python tests/run_full_stack.py
```

Use `bizora.local_settings`, a fresh `BIZORA_DATA_DIR` and a stable test-only `DJANGO_SECRET_KEY` for local SQLite checks. Do not run these against the legacy database. `scripts/verify_domains_postgres.py` is the separate authoritative-database check and was not run here.

## Required callback migration

Before enabling Dialyra callbacks, set a different random `BIZORA_BUSINESS_<ID>_DIALYRA_WEBHOOK_SECRET` per business. Configure its HTTPS callback URL as `/api/businesses/<ID>/dialyra/webhook/` and its custom `Authorization` header as `Bearer <that business's secret>`. The old unscoped URL now returns **410**; an unconfigured business callback returns **503**. Do not reuse the outbound provider API key for this secret.

## Security-audit coverage limit and change review

The requested security skill requires independent reconnaissance, hunting, coverage critics and verification. Three delegated reconnaissance agents all reported that they had no filesystem tools. The formal run is therefore explicitly **incomplete**, with reason `independent_reconnaissance_agents_lack_filesystem_tools`. Its `REPORT.md`, `FINDINGS-DETAIL.md`, `NEEDS-VALIDATION.md`, `run-metadata.json`, `architecture.md`, `findings.json` and `coverage-ledger.json` are retained outside the repo; both JSON validators pass. An empty final findings file means independent verification was unavailable, not that the repo has no vulnerabilities.

The [security-audit skill](/home/naim/.agents/skills/security-audit/SKILL.md) states: “Never skip independent review of a `confirmed` record in any profile.” Because the independent agents could not read source, their required pass could not be replaced by this agent's successful local checks. The formal [security report](/home/naim/security-audit-skill/bizora/run-2/REPORT.md) records that limit.

The prior `run-1` metadata and all ten unfinished ledger entries were read. Relevant current source was compared with its commit. It had no final findings artifact or completed coverage to carry forward.

The parent reviewed the complete change and relevant callers using the review-agent method. That is a self-review, not an independent review. The source audit concentrated on authentication, tenant checks, money writes, identity review, callbacks, AI approval and frontend failure states. The whole tree was mapped, but every implementation file was not read end to end. Historical docs claiming BI/Graph/configuration/observability are unmounted are stale; `app/urls.py` is the current route source, and the README was corrected.

Final change review: No findings of additional regressions in the reviewed diff after the recorded repairs and checks. The database, deployment and independent-review limits above still apply.

Verdict: The repaired local app passes the recorded checks. Resolve PostgreSQL and deployment verification before a production sign-off, and complete the independent security pass.

Not checked: live integrations, production/shared data, real HTTPS infrastructure, production capacity/recovery, a fresh dependency vulnerability scan, human UAT, assistive technology, other browsers, and standalone execution of the separate `MetaMetrics` and `Dialyra-docs` packages. Those subprojects' additional dependencies were not installed for this run.
