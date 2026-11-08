# Frontend implementation audit and handoff

Updated: 8 November 2026. Scope: Next.js client in `frontend/`, mounted Django routes in `app/urls.py`, and the existing implementation reports. Django `/ops/` is a separate, working server-rendered UI. This file tracks the newer Next.js client.

## Work inventory, in implementation order

| ID | Status | Required work | Evidence / boundary |
| --- | --- | --- | --- |
| F01 | Open | Replace raw JSON intake with validated, field-specific forms for all 32 canonical resources, including money, dates, relationship IDs, and source references. | `frontend/src/components/CreateRecord.js` currently has one JSON textarea. `app/domains/registry.py` lists the resources. Django still validates writes. |
| F02 | Partial | Complete source evidence comparison and distinct-product review. Guided assessment now sends source identity, shows candidate details, and requires a manager reason and confirmation before mapping. | `/products/assess/` and `/product-references/` are mounted. The direct mapping command was removed from product detail. The browser flow passes against an isolated local business. Review reason is stored in private `source_metadata`; the current read projection excludes it, so a durable review display remains to build. |
| F03 | Partial | Add scoped lookup and guided link/unlink/reconciliation with explicit confirmation. Identity evidence is now expandable on the review page, but commands still require manual IDs and the first 25 evidence rows are shown. | Identity read and review endpoints are mounted. Final merge execution is intentionally blocked in `app/domains/merge.py`. |
| F04 | Open | Add connection evidence and sync history to service diagnostics when a mounted read contract is available. | `ContractTools.js` only probes seven owner contracts. Configuration and Observability API modules are not mounted in `bizora/urls.py`. |
| F05 | Blocked by authoritative execution evidence | Complete AI action execution UI only after the executor contract distinguishes simulated, prepared, and confirmed provider effects. | `ReviewForms.js` supports review. `/actions/<pk>/execute/` exists, but the Next.js UI must not imply live provider execution without the backend guarantee. |
| F06 | Needs backend | Add server pagination and filtering for AI recommendation, issue, and action collections, then add client paging controls. | `AssistantWorkspace` and `ActionReview` render returned arrays; the AI collection endpoints are currently unpaginated. |
| F07 | Open | Add isolated browser flows for proposal review, refund request, callback schedule, and provider preparation, including role and tenant boundaries. | `frontend/tests/e2e/workspace.spec.js` covers login, overview, navigation, and mobile only. |
| F08 | Open | Verify against PostgreSQL 16 and resolve the `IntegrationSyncLog.created_at` migration drift before claiming authoritative DB readiness. | `frontend-progress.md` records SQLite-only live frontend verification and one pending field alteration. |
| F09 | Blocked by mount | Connect Business Intelligence, Business Graph, Configuration, Observability, and expanded Overview screens once their APIs are mounted and authorized. | `bizora/urls.py` mounts only `app.urls` and `/ops/`; unmounted modules cannot be shown as live data. |

## Work log

- 8 Nov 2026: Inspected Next.js route/component inventory, frontend progress report, Django root routes, domain registry, product assessment and mapping behavior, and existing tests. Found the pre-existing `.gitignore` edit; leave it out of frontend commits.
- 8 Nov 2026: Implemented guided product assessment and reviewed source mapping (F02 partial). Added source identity validation and candidate checks in `productReview.js`, candidate detail links, manager-only reason and confirmation, a fresh assessment before write, and an idempotency key. Removed the direct mapping action from product detail. Added unit tests and a Playwright browser test. Added expandable identity evidence (F03 partial).
- Verification: `npm test` 7 passed; `npm run build` passed; `npm run format:check` passed; `ProductIntakeReviewTests` 6 passed with isolated SQLite; Playwright workspace and product review 2 passed against temporary `/tmp/bizora-frontend-audit` data. `makemigrations --check --dry-run` reports pending `0010_alter_integrationsynclog_created_at.py` (F08 remains open).
- Next step: finish F03 with server-backed lookup and pagination for all identity collections, then F01 field forms. Add the remaining F07 browser flows with isolated fixtures. Recheck DB migrations and PostgreSQL 16 separately; do not count the temporary SQLite run as authoritative DB verification.

## Continuation notes

- Session and CSRF handling live in `frontend/src/lib/clientApi.js` and `frontend/src/app/api/backend/[...path]/route.js`; do not move credentials into browser storage.
- Follow `ecc-conventions`: existing relative imports in plain JS tests, `*.test.js`, and imperative Conventional Commits. This skill is generic to ECC; follow this repository's existing Next.js file names and import aliases for components.
- Treat Django as the source of truth for membership, state, money, product identity, and execution status. A frontend review step cannot replace server authorization.
