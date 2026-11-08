# Next.js frontend progress

Updated: 8 November 2026. Design source: [`DESIGN.md`](../requirements/DESIGN.md). Django remains authoritative for records, membership, role checks, and state transitions.

## Build and completion status

**The Next.js production build succeeds. The frontend is not fully complete.** A successful build confirms that Next.js can compile the application; it does not mean every workflow is finished or every backend endpoint has a finished UI. Items below marked **Partial** or **Not connected** are not ready to count as complete.

## Implemented and verified (current scope)

| Surface | Mounted Django endpoint | Frontend state |
| --- | --- | --- |
| **Verified** Login, logout, business switch | `/api/frontend/session/`, `login/`, `logout/` | Session cookies and CSRF; active memberships only |
| **Verified** Overview | `/api/businesses/{id}/overview/`, `support-queue/` | Real counts; unavailable analytics labeled |
| **Partial** Canonical lists and details | `/api/businesses/{id}/{resource}/`, `{resource}/{pk}/`, customer `360/` | Lists for all 32 registry resources, details and filters; not every resource has a purpose-built workflow |
| **Partial** Intake | POST `/api/businesses/{id}/{resource}/` | Advanced JSON form with idempotency and Django validation; not operator-ready field forms |
| **Partial** Operations | Transition, assignment, priority, handover, read, schedule, variant update, outbound prepare | Controls are available for implemented record types; not every endpoint/action has a dedicated end-to-end workflow |
| **Partial** Financial and web evidence | `financial-timeline/`, `website-performance/`, visitor journey | Mounted reads; BI gaps remain explicit |
| **Partial** Context | `graph-context/`, customer retargeting, conversation context | Related context is shown on selected record detail views |
| **Partial** AI advisory | Assistant query, recommendations, issues, support/marketing/diagnosis/summarization endpoints | Advisory panels; pagination and complete action lifecycle are unfinished |
| **Partial** Human review | Scoped `actions/{pk}/review/`, identity conflict/candidate review, merge dry-run | Review controls exist for scoped flows; no final identity merge execution |
| **Partial** Identity management | Canonical, register, resolve, link, unlink, verify, status, enrich, detect and validate commands | Manager forms and evidence lists; source reconciliation is manual and final merge is blocked |
| **Partial** Contract diagnostics | `/contracts/{owner}/{capability}/` | Seven owner capability checks; connection history and live provider execution evidence are missing |
| **Partial** Product assessment | `/products/assess/` | Name and SKU assessment exists; source mapping/reconciliation is incomplete |

Verification: Next production build; Node unit tests; Django auth and operations tests; browser login, business selection, overview and 320px mobile navigation; live proxy login and customer creation using an isolated local database.

8 November integration pass: all 17 mounted Next.js navigation sections and 32 canonical resource lists loaded through Django in an isolated browser run. Product source review, identity linking, refund, callback scheduling, call preparation, campaign platform filtering, and seven owner contract probes also passed. `IntegrationSyncLog.created_at` migration drift is resolved by migration 0010. PostgreSQL 16 verification remains open because this workspace cannot access a local server or Docker daemon. See [`frontend-handoff.md`](frontend-handoff.md) for exact coverage and remaining work.

## Not properly complete yet

| Priority | Status | Work still required |
| --- | --- | --- |
| P1 | **Partial** | Replace JSON intake with field-specific, inline-validated forms for each canonical resource, including money, dates, and source mapping. |
| P1 | **Partial** | Add identity evidence detail and guided source reconciliation; current flows require manual IDs. Keep final merge unavailable until preservation guarantees are established. |
| P1 | **Partial** | Finish reviewed product source reconciliation and evidence comparison; current assessment does not complete mapping. |
| P1 | **Not connected** | Finish the AI action execution lifecycle only after the executor contract distinguishes simulated from live provider evidence. Current UI supports advisory/review, not execution. |
| P2 | **Partial** | Add connection evidence and operational history to service diagnostics. |
| P2 | **Backend limitation** | Add pagination and server-side filtering for AI recommendation, action, and issue collections; current APIs return unpaginated arrays. |
| P2 | **Partial verification** | Browser coverage now includes refund, callback, call preparation, product review, identity linking, all mounted sections/lists, and owner contract probes. Add proposal review browser fixture and explicit role/tenant browser cases. |
| P2 | **Verification gap** | Migration 0010 resolves `IntegrationSyncLog.created_at` drift; run frontend integration verification against PostgreSQL 16. Current live verification used isolated SQLite. |

## Endpoint audit update

Expanded Overview, Configuration, and Observability URL modules are now mounted under `/api/businesses/{id}/`. Their read collections and supported record details are available in the Business insights, Configuration, and Integration health sections. Both legacy `BusinessAccess` grants and the active `BusinessMembership` used by Next.js are recognized; an existing inactive or lower-role membership overrides a legacy grant. The browser route sweep visits every new read collection and all canonical resource lists.

Verification for this pass: 209 Django tests passed (11 skipped), 7 Node tests passed, all 5 Playwright browser tests passed against an isolated local SQLite database, Next.js production build and Prettier check passed, and migration drift check found no changes. The browser run opened the live Next.js UI and drilled into an integration connection. PostgreSQL 16 was not available for this run.

The new module screens are read-only evidence views. Configuration updates, observability operations, and their history/diagnostic endpoints still need purpose-built controls. Business Intelligence and Business Graph remain unmounted because their views require an authorized `request.business` context that the current router does not provide. The generic canonical intake is still JSON based; AI action execution is still unavailable pending authoritative execution evidence. PostgreSQL 16 integration verification remains open.
