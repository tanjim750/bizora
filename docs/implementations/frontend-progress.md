# Next.js frontend progress

Updated: 8 November 2026. Design source: [`DESIGN.md`](../requirements/DESIGN.md). Django remains authoritative for records, membership, role checks, and state transitions.

## Implemented and verified

| Surface | Mounted Django endpoint | Frontend state |
| --- | --- | --- |
| Login, logout, business switch | `/api/frontend/session/`, `login/`, `logout/` | Session cookies and CSRF; active memberships only |
| Overview | `/api/businesses/{id}/overview/`, `support-queue/` | Real counts; unavailable analytics labeled |
| Canonical lists and details | `/api/businesses/{id}/{resource}/`, `{resource}/{pk}/`, customer `360/` | All 32 registry resources exposed through lists; details and filters |
| Intake | POST `/api/businesses/{id}/{resource}/` | Advanced JSON form; idempotency key; Django validation |
| Operations | Transition, assignment, priority, handover, read, schedule, variant update, outbound prepare | State-aware controls on matching records; pending/execution language |
| Financial and web evidence | `financial-timeline/`, `website-performance/`, visitor journey | Mounted reads; BI gaps remain explicit |
| Context | `graph-context/`, customer retargeting, conversation context | Related record detail sections |
| AI advisory | Assistant query, recommendations, issues, support/marketing/diagnosis/summarization endpoints | Advisory panels; no automatic authoritative writes |
| Human review | Scoped `actions/{pk}/review/`, identity conflict/candidate review, merge dry-run | Explicit reason and review; no merge execution control |
| Identity management | Canonical, register, resolve, link, unlink, verify, status, enrich, detect and validate commands | Manager forms and evidence lists; final merge blocked |
| Contract diagnostics | `/contracts/{owner}/{capability}/` | Seven owner-specific capability checks with explicit adapter status |
| Product assessment | `/products/assess/` | Name and SKU assessment before advanced intake |

Verification: Next production build; Node unit tests; Django auth and operations tests; browser login, business selection, overview and 320px mobile navigation; live proxy login and customer creation using an isolated local database.

## Unfinished work

| Priority | Work | Why it remains |
| --- | --- | --- |
| P1 | Replace the advanced JSON intake with field-specific forms for each canonical resource, including money, dates, source mapping, and inline validation. | The mounted endpoints work through Django validation, but JSON is not a complete operator experience. |
| P1 | Add richer identity evidence detail and guided source reconciliation. | The mounted commands are connected, but operators must enter IDs manually. Final merge execution stays blocked until preservation guarantees are established. |
| P1 | Complete the reviewed product source reconciliation flow. | The UI now assesses products before intake; mapping and evidence comparison still rely on ID entry. |
| P1 | Add an explicit AI action execution screen only after the executor contract and simulated versus live evidence are reconciled. | The UI deliberately exposes human review but not global execute actions or provider completion claims. |
| P2 | Add connection evidence and operational history to service diagnostics. | The seven contract checks are connected; integration connection records need a dedicated detail presentation. |
| P2 | Add pagination and server-side filtering to AI recommendation, action, and issue APIs. | These mounted endpoints currently return unpaginated arrays. |
| P2 | Add browser coverage for review, refund, callback, and provider preparation flows using isolated fixtures. | The current Playwright test covers the main authenticated read and navigation path; Django tests cover many backend workflows. |
| P2 | Reconcile the existing `IntegrationSyncLog.created_at` migration drift and run the frontend integration suite against PostgreSQL 16. | `makemigrations --check --dry-run` reports one pending field alteration; current verification used isolated SQLite. |

Separate Business Intelligence, Business Graph, Configuration, Observability, and Overview modules remain unmounted at the root URL configuration. The frontend links only to mounted core projections and displays unavailable or not-mounted states for absent analytics.
