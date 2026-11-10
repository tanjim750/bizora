# Bizora frontend — single source of truth

| | |
|---|---|
| Status | **DRAFT for owner review.** No application code has been written. |
| Backend verified at | `origin/main` **`5f176a2`** (2026-11-09). Re-verify before building if `main` has moved. |
| Companion files | [`frontend-api-reference.md`](frontend-api-reference.md) (verified endpoint contracts) · [`frontend-stitch-prompt.md`](frontend-stitch-prompt.md) (page-by-page UI generation prompts) |
| Maintained by | The orchestrator keeps §6 (tracker) and §7 (decisions) current at the end of every working session. |

## How this document was produced, and how far to trust it

1. **Documentation first.** Read `docs/implementations/domain.md`, `TEAM_LEAD_HANDOFF.md`, `contracts/README.md`, the
   12 feature specifications, and the owning engineers' progress notes.
2. **Code verification by five read-only scans** (one per domain group). Every route, field, enum and status code in
   the API reference carries a `file:line` citation. The full scan outputs are the reference file.
3. **Independent reproduction.** The orchestrator re-checked the findings that decide whether a frontend can work at
   all. Those are marked **[R]** (reproduced by running code or Git) below. Items marked **[C]** were read from code and
   not executed. **[LIB]** means a Django/DRF library behaviour that was read from library defaults. **NOT VERIFIED**
   means it needs a running stack.
4. **Zero-hallucination rule.** If a capability appears in a specification but no endpoint exists, this document says
   **NO ENDPOINT FOUND** and marks the screen *backend-blocked*. No route, field or payload here is invented.

> **SUPERSEDED STACK NOTICE (2026-11-09, decision D-F20).** The project adopts the teammate's existing **Next.js 16 + React 19 JavaScript app in `frontend/`** instead of the Vite + React + TypeScript + Tailwind plan below.
> Sections 1.2 (stack), 1.6 (folder structure) and 1.7 (environments) and decisions D-F01 to D-F04 describe the retired plan and are **not instructions**. Still valid: the backend constraints (1.1, 1.3 to 1.5), the design system (section 2; see also the
> hand-corrected tokens in `docs/frontend-overhaul/assets/tokens.css`), the module list (section 3), the nine-workspace page plan (3.0; the route prefix is `/business/[id]/` and tabs are path segments, see `docs/frontend-overhaul/DESIGN_SPEC.md` section 3), the API rules (section 4) and the prerequisites (section 5; P0 and P2 are fixed on main, P1 is partly fixed).
> The agent brief for the overhaul is in `docs/frontend-overhaul/`; per-domain backend problems are in `docs/backend-issues/`.

## 0. Read this first — the backend cannot serve a frontend yet

The backend is described as complete, and the code for most domains exists. But the merged `main` does not run, and
several APIs are not reachable. A frontend can be **designed and scaffolded now**, but it cannot be **integrated** until
the prerequisites in §5 are done.

| # | Finding | Evidence | Effect on the frontend |
|---|---|---|---|
| **P0** | **`main` cannot start.** `manage.py check` crashes; even with the missing imports patched, `import app.urls` fails, so *every* `/api/` route and the `/ops/` UI is dead. | **[R]** Merge `396593f` (parents `fd41ea7` and `e487b0b`) dropped `import sys`/`import copy` (`bizora/settings.py:183,194`), `import re` + `ValidationError` (`app/models.py`), and 14 model classes the code still imports. `app/admin.py` never imports `admin`. The merge result differs from *both* parents in 5 files: `app/models.py`, `app/urls.py`, `bizora/settings.py`, `app/admin.py`, `app/tests/test_status.py`. | Nothing can be called. |
| **P1** | **Five API modules are not mounted:** Business Intelligence, Business Graph, Configuration, Observability, Overview. | **[R]** `app/urls.py` has no `include()`. Observability/Overview/Configuration were mounted at `businesses/<int:business_id>/{observability,overview,configuration}/` in commit `fd41ea7` (`app/urls.py` lines 7–9) and lost in merges `d577133`/`396593f`. BI and Graph were never mounted on any branch. | Those screens have no route to call. |
| **P2** | **No way to log in or discover context from a SPA.** Auth is Django session + CSRF only; there is no JSON login, no "me", no "my businesses", no role endpoint, no CORS. | **[C]** scan A §1; DRF defaults **[LIB]** | The SPA must be same-origin and cannot learn the user's business or role from the API. |
| **P2b** | **Two different authorization tables.** The domain API, AI views and `/ops` use `BusinessMembership` (roles `VIEWER/OPERATOR/MANAGER/OWNER`; AI action routes use `OWNER/ADMIN/OPERATOR`). Observability, Overview and Configuration use `BusinessAccess` (roles `READER/MANAGER`). A user in one table gets 403 from the other's endpoints. | **[R]** `app/models.py:84`, `app/observability/models.py:12-18`; usage grep | One user may see half the app. |
| **P3** | **Business Graph cannot import on Python 3.12**, the declared runtime. `projection.py` annotates with `models.Model` where `models` is `app.models`. It fails at its own tip `09b14db` and at every later commit. | **[R]** reproduced in isolation on 3.12.3. Python 3.14 evaluates annotations lazily, which probably hid it — this is an **inference**; no 3.14 was available. | Graph screens would fail on the deployed runtime. |
| **P3b** | **BI → Graph hand-off produces no edges.** BI writes relationship keys `bi.relationship.<name>.v1`; Graph accepts only bare keys like `customer_order`. | **[R]** `relationships.py:70` vs `projection.py:72-96`; no test bridges the two. | A graph built from real BI data would show nodes and no connections. |
| **P4** | **Nothing runs the BI calculators.** The `pipeline/run/` endpoint only reconciles relationships, syncs the metric registry, and counts facts/issues. No view, command, signal or task calls any metric, anomaly or fact generator. | **[R]** `api.py:502-529` and a grep for every `record_*`/`evaluate_*`/`create_or_update_*` caller | BI dashboards would be empty on a real deployment. |
| **P5** | **AI recommendations and actions are never created by any route**, so their lists are empty until something seeds them. LLM routes return canned text when `BIZORA_LLM_URL` is unset (nothing sets it) and do not say so. | **[C]** scan B | The AI screens can render only empty states and canned replies today. |

Everything marked `LIVE*` below means **routable in `app/urls.py`, working only after P0**.

### Readiness legend (used on every module in §3 and §6)

| Label | Meaning |
|---|---|
| **LIVE\*** | Route exists in `app/urls.py` and is reachable once P0 is fixed. |
| **UNMOUNTED** | The code exists but no URL includes it (P1). Needs a mount decision and often an auth fix. |
| **PARTIAL** | Some sub-features have an endpoint; the rest are listed per module. |
| **UNAVAILABLE-BY-DESIGN** | The endpoint exists but deliberately returns `{"status":"UNAVAILABLE","owner":…}` because another team's adapter is not configured. This is *normal data*, not an error — render an empty state naming the owner. |
| **BLOCKED** | No HTTP surface at all (`NO ENDPOINT FOUND`). The screen can be designed but not wired. |

---

## 1. Frontend architecture and stack

### 1.1 Backend constraints that drive every decision

| # | Constraint (verified) | Consequence for the frontend |
|---|---|---|
| C1 | Authentication is Django **session cookie + CSRF**, with HTTP Basic as DRF's fallback. No token/JWT, no CORS app, no `CSRF_TRUSTED_ORIGINS`. **[C]** scan A §1a | The SPA **must be served from the same origin as `/api/`** (reverse proxy in production, dev-server proxy locally). A separate-origin SPA will not work as shipped. |
| C2 | There is **no JSON login/logout**. Login is the HTML form at `/ops/login/`; logout is `POST /ops/logout/`. The CSRF cookie is issued only by pages that render `{% csrf_token %}`. **[C]** | Sign-in is a handoff to the Django form until the team adds JSON endpoints (§5, P2). |
| C3 | **No "me", no "my businesses", no role endpoint.** The business id and role must be known out of band. **[C]** | Business picker cannot be populated from the API; role-aware UI must infer from `403`s until P2 is done. |
| C4 | Business scope is in the URL: `/api/businesses/{business_id}/…`. A non-member gets **404** (indistinguishable from "business does not exist"); a wrong role gets **403 `FORBIDDEN`**. Superusers get no bypass on this API. **[C]** | The business id is part of every SPA route: `/b/:businessId/…`. |
| C5 | **Five error shapes** coexist (§1.5). **[C]** | One normalising error layer is mandatory. |
| C6 | **Four pagination styles** (§1.3). **[C]** | A pagination adapter, not per-screen code. |
| C7 | Everything is **synchronous and in-request**; no jobs, polling endpoints, websockets or push. Nothing is actually sent to a provider ("recorded", not "sent"). **[C]** | Long actions need explicit loading states; no live updates, so polling is the only freshness mechanism. Labels must say "recorded", never "sent". |
| C8 | **No OpenAPI/Swagger schema exists.** **[C]** | The typed client is hand-written from the API reference and validated at runtime with Zod. |
| C9 | The contracts doc requires clients to **tolerate additive optional fields** (`contracts/README.md`). | Zod schemas use non-strict objects; unknown fields are ignored, not rejected. |
| C10 | Money is per-currency and never summed across currencies; ratios are **fractions**; durations are **seconds**; missing data is **never zero**; periods are half-open `[start, end)`. **[C]** BI registry | Formatting rules in §2.2 are mandatory, not stylistic. |
| C11 | `source_metadata`, `config`, `recording_url` are never returned; customer message text arrives wrapped in `<untrusted_customer_data>` tags. **[C]** | Strip the wrapper for display; never render message content as HTML. |

### 1.2 Stack

| Concern | Choice | Why | Version on npm (checked 2026-11-09) |
|---|---|---|---|
| Language | TypeScript, `strict` | Large API surface with many enums | `typescript` 7.0.2 |
| UI library | React | Ecosystem for tables/graphs/charts | `react`, `react-dom` 19.3.1 |
| Build / dev server | Vite (SPA) | Static build served behind the same origin as Django (C1); no Node server in the auth path. SSR/Next.js adds a second server in the cookie path with no benefit for an authenticated app. | `vite` 8.3.6, `@vitejs/plugin-react` 6.3.0 |
| Routing | TanStack Router | Type-safe routes; filters and pagination live in typed URL search params | `@tanstack/react-router` 1.170.46 |
| Server state | TanStack Query | Caching, invalidation after mutations, refetch-on-focus | `@tanstack/react-query` 5.107.1 |
| UI state | Zustand | Sidebar, theme, table density only | `zustand` 5.1.0 |
| Tables | TanStack Table + Virtual | Server-side pagination, sticky headers, long timelines | `@tanstack/react-table` 9.3.1, `@tanstack/react-virtual` 3.14.26 |
| Forms | React Hook Form + Zod | Server field errors map onto fields; same Zod schemas validate responses | `react-hook-form` 7.91.0, `@hookform/resolvers` 7.0.5, `zod` 4.6.7 |
| Styling | Tailwind CSS driven by CSS variables (the tokens in §2) | Semantic tokens only; raw HEX in components is a bug (kit rule) | `tailwindcss` 4.3.5 |
| Primitives | Radix UI via the shadcn/ui copy-in pattern | Accessible dialogs, menus, tabs; code is owned, not a dependency | not version-checked |
| Icons | lucide-react | | `lucide-react` 1.70.0 |
| Charts | Recharts | SVG time series and bars; keyboard/screen-reader friendly with a table fallback | `recharts` 3.10.1 |
| Graph canvas | React Flow (+ an auto-layout library) | Bounded subgraphs and journeys. The backend caps nothing (see Graph notes), so the client enforces its own limits. Layout library (dagre or elkjs) not version-checked. | `@xyflow/react` 12.12.1 |
| Dates / numbers | `Intl.DateTimeFormat` / `Intl.NumberFormat` with the business timezone and currency; `date-fns` for range math | No timezone library needed for formatting | `date-fns` 4.4.0 |
| i18n | Message catalog from day one (English first). Library: i18next | `Locale Settings` exist in the Configuration spec; strings must not be hard-coded | `i18next` 27.0.1 |
| Unit / component tests | Vitest + Testing Library | | `vitest` 5.1.0, `@testing-library/react` 16.3.3 |
| API mocks | MSW, generated from the API reference | Contract tests without a backend | `msw` 3.0.4 |
| End-to-end | Playwright against a real backend seeded by `manage.py demo_completion` | | `@playwright/test` 1.65.0 |
| Lint / format | ESLint + Prettier | | `eslint` 10.14.0, `prettier` 3.9.10 |

> **Caveat.** These are the latest versions *published* today. They have **not** been installed or built together. At
> scaffold time run the install, resolve peer dependencies, and commit a lockfile. Node 22.23.2 is installed on the
> development machine.

### 1.3 Data fetching, pagination and state

**Query keys** always start with the business: `[businessId, domain, resource, params]`. Changing business clears the cache.

**Pagination adapter.** Four styles exist; the adapter normalises them to `{ items, total, hasMore, page }` so tables are written once.

| Style | Used by | Request | Response |
|---|---|---|---|
| DRF page number | Domain resource lists, support queue, identity tables, financial timeline, visitor journey; Observability and Configuration lists | `page`, `page_size` (default 25, **max 100**) | `{count, next, previous, results}`; `next`/`previous` are absolute URLs; a page past the end is **404** `{"detail":"Invalid page."}` **[LIB]** |
| Limit / offset | Business Intelligence lists (metrics, snapshots, facts, issues) | `limit` (default 50, clamped 1–200), `offset` | `{total_count, limit, offset, results}`; a non-integer value silently resets **both** to 50/0 |
| Capped sections | Detail, Customer 360, overview, context payloads | none | `{count, results (≤ 50), truncated}` — fetch the child list route for more |
| Bare array | AI recommendations/actions/issues; graph snapshot list | none | `[…]`, **no pagination** (client-side paging only) |

**Mutations.** `POST businesses/{id}/{resource}/` is an **idempotent create-or-update** and requires an `Idempotency-Key`
header (1–180 chars). Generate **one UUID per user action** and reuse it on retry: same key + same body → `200` with the
existing record; same key + changed body → `409 IDEMPOTENCY_CONFLICT`. Other command POSTs carry no key and are
state-idempotent. There is **no PATCH, PUT or DELETE** on the domain API.

**Concurrency tokens to send back:** `transition.expected_status` (→ `409 STALE_STATE`), `variants/{pk}/update/`
`expected_updated_at` (→ `409`), merge `expected_fingerprint` (→ `400 STALE_PLAN`), and `version` on Configuration
writes (→ `409`). A `409` means "reload and retry": refetch, show a non-blocking notice, keep the user's input.

**Freshness.** There is no push channel. Use `refetchOnWindowFocus` plus a per-screen `refetchInterval` only where a screen
is operational (queue, inbox, sync status); intervals are **frontend defaults**, not backend policy, and are configurable.
Every such screen shows "Updated hh:mm" in the business timezone.

**State split.** Server state → TanStack Query. Filters, sort, page and selected tab → URL search params (shareable,
back-button safe). Business → route param. Theme, density, sidebar → Zustand, persisted locally. Role → a context derived
from the first successful call and from `403 FORBIDDEN` responses until P2 provides it.

### 1.4 Authentication, session and CSRF

Same-origin only (C1). The sequence until JSON endpoints exist:

1. `GET /ops/login/` — renders `{% csrf_token %}`, which sets the `csrftoken` cookie.
2. `POST /ops/login/` as `application/x-www-form-urlencoded` with `username`, `password`, `csrfmiddlewaretoken` (the
   cookie value) and `next`. Success is a `302` and the `sessionid` cookie is set.
3. Every unsafe request thereafter sends `X-CSRFToken: <csrftoken cookie>`.
4. Logout is `POST /ops/logout/` (CSRF required).

Cookies are Django defaults: `sessionid` (DB-backed, `SameSite=Lax`, not `Secure`) and `csrftoken`. Unauthenticated calls
return **403 `{"detail":"Authentication credentials were not provided."}`, not 401** **[LIB]**, so the client treats that
exact body as "session expired" and redirects to sign-in. HTTP Basic works for server-side clients only and is not used by
the browser app.

*Dev note (library behaviour, to confirm at integration):* Django 4.2 checks the `Origin` header on unsafe requests. When
the Vite dev server proxies to Django, either rewrite `Origin` to the Django origin in the proxy or set
`CSRF_TRUSTED_ORIGINS` for the dev origin.

### 1.5 Error contract

One `ApiError { status, kind, code?, detail?, fieldErrors?, raw }` is produced from all of these shapes:

| Shape | Where | Meaning / handling |
|---|---|---|
| `{"code","detail"}` | Domain API | Switch on `code`, show `detail`. 403 `FORBIDDEN` = role too low; 404 `NOT_FOUND` = business invisible, unknown resource, or missing record; 409 = `STALE_EVENT`, `STALE_STATE`, `IDEMPOTENCY_CONFLICT`, `HANDOVER_CONFLICT`, `CONSTRAINT_CONFLICT`; everything else 400 |
| `{"<field>": ["msg"]}` or `["msg"]` | DRF serializers; Observability/Configuration view checks | Map onto form fields; a bare list is a non-field error |
| `{"detail": "…"}` | Auth, CSRF, 404, 405, 409 (Config) | `"Authentication credentials were not provided."` → session expired; `"CSRF Failed…"` → reload to refresh the token |
| `{"error": "…"}` | AI action routes, BI API, Graph API | BI messages are deliberately generic; Graph messages are specific and may name an owning business id — never show raw Graph text to a non-owner |
| `{"query": "…"}` / `{"unknown": [...]}` | Observability, Overview, Configuration | Unsupported/repeated query parameter or unknown body key — a client bug, log it |
| HTML 500 | Any unhandled exception (several bad inputs reach this: see the reference) | Show a generic failure with a retry; never parse as JSON |

A missing related id returns **400 `INVALID_RELATION`**, not 404, on most commands. `UNAVAILABLE` envelopes
(`{"status":"UNAVAILABLE","owner":…,"reason":…}`) are **successful data**: render an `UnavailableState` naming the owner.

### 1.6 Folder structure

The frontend lives in `frontend/` at the repository root (decision D-F03; confirm with the owner).

```
frontend/
  src/
    app/              providers, router, app shell, route guards (business + role)
    api/
      http.ts         fetch wrapper: base URL, CSRF header, Idempotency-Key, error normalisation
      errors.ts       ApiError + the six shapes above
      pagination.ts   the four pagination styles -> one shape
      schemas/        Zod schemas per domain (non-strict)
      <domain>.ts     typed endpoint functions, one file per backend domain
    features/         one folder per module in section 3 (customers, orders, inbox, intelligence, graph, ai, …)
    components/
      ui/             design-system primitives (section 2)
      data-table/     server-paginated table
      charts/         time series, delta, sparkline
      evidence/       EvidencePanel, JsonViewer, UnavailableState, SimulatedBadge
      graph/          GraphCanvas, JourneyTimeline
    lib/              formatters (money, ratio, duration, tz), enum label maps, role guards
    styles/           tokens.css (generated from section 2), tailwind config
    test/             MSW handlers + fixtures generated from frontend-api-reference.md
  e2e/                Playwright specs
```

### 1.7 Environments and deployment

- **Development:** Vite dev server proxies `/api`, `/ops` and `/admin` to Django (default `127.0.0.1:8000`).
- **Production:** build the SPA to static files; a reverse proxy serves them on `/` and forwards `/api/`, `/ops/`, `/admin/` to
  Django on the same host. Adding a `frontend` service to `docker-compose.yml` is a team decision (the compose file is shared).
- **Backend runtime:** Python 3.12, Django 4.2.27, DRF 3.15.2; PostgreSQL 16 is authoritative (`AGENTS.md`). Note that
  `docker-compose.yml` sets `POSTGRES_HOST` but `settings.py` only switches to PostgreSQL when `BIZORA_DATABASE=postgresql`,
  so Compose silently uses SQLite unless `.env` sets it. **[C]**
- **Secrets:** none belong in the bundle. The `.env*` files are never read by tooling in this repository.

### 1.8 Quality gates for the frontend

`typecheck` · `lint` · unit/component tests · MSW contract tests · Playwright smoke per module · an automated
accessibility check on each route · a visual review at 360, 768 and 1280 px in both themes. UI work is **not** "done"
from code alone; it needs screenshots (kit design law) or an explicit "NOT VISUALLY VERIFIED" label.

---

## 2. Design system

Direction: **formal, calm, high-contrast enterprise.** Cool-slate neutrals carry about nine-tenths of the interface; one cobalt-blue
primary marks actions and selection; semantic colours are reserved for status. There is no second accent, no gradient and no
decorative illustration. Text is near-black ink on near-white, never pale grey, so it reads rich. Data is the hero: tabular
numerals, restrained chrome, generous but dense layout. One signature element, the **evidence thread** (a thin vertical line
with small nodes joining Data → Evidence → Fact → Issue → Recommendation), appears in the evidence drawer and in timelines.
Motion is minimal (see 2.3). Every colour below was **computed and contrast-checked** (WCAG 2.2 AA); see 2.1.4. This replaced the
first indigo-and-teal draft on 2026-11-09 (decision D-F13).

### 2.1 Colour

#### 2.1.1 Semantic tokens (light and dark)

| Token | Light HEX | Light HSL | Dark HEX | Dark HSL | Use |
|---|---|---|---|---|---|
| `canvas` | `#F8FAFC` | `hsl(210 40% 98%)` | `#0B1220` | `hsl(220 49% 8%)` | App background behind everything |
| `surface` | `#FFFFFF` | `hsl(0 0% 100%)` | `#111A2B` | `hsl(219 43% 12%)` | Tables, panels, modals, drawers, inputs |
| `surface-subtle` | `#F1F5F9` | `hsl(210 40% 96%)` | `#18233A` | `hsl(221 41% 16%)` | Table header rows, row hover, code blocks, disabled fills |
| `border` | `#E2E8F0` | `hsl(214 32% 91%)` | `#243049` | `hsl(221 34% 21%)` | Dividers and outlines (decorative, no contrast requirement) |
| `border-input` | `#76859B` | `hsl(216 16% 54%)` | `#6B7C98` | `hsl(217 18% 51%)` | Boundary of inputs, selects, checkboxes, switches (3:1 required) |
| `text` | `#0F172A` | `hsl(222 47% 11%)` | `#F1F5F9` | `hsl(210 40% 96%)` | Primary text, headings, numbers (near-black ink, never pure black) |
| `text-secondary` | `#334155` | `hsl(215 25% 27%)` | `#CBD5E1` | `hsl(213 27% 84%)` | Labels, column headers, secondary copy |
| `text-muted` | `#526278` | `hsl(215 19% 40%)` | `#94A3B8` | `hsl(215 20% 65%)` | Timestamps, helper text, placeholders (still 4.5:1) |
| `primary` | `#1D4ED8` | `hsl(224 76% 48%)` | `#60A5FA` | `hsl(213 94% 68%)` | Primary buttons, active controls, links, selected-state marks. The only accent colour |
| `primary-hover` | `#1E40AF` | `hsl(226 71% 40%)` | `#93C5FD` | `hsl(212 96% 78%)` | Hover and pressed state of primary (a darker step, no new hue) |
| `primary-subtle` | `#EFF6FF` | `hsl(214 100% 97%)` | `#14264D` | `hsl(221 59% 19%)` | Selected row, active tab fill, soft chips, AI and intelligence markers |
| `primary-text` | `#1E40AF` | `hsl(226 71% 40%)` | `#BFDBFE` | `hsl(213 97% 87%)` | Text and icons placed on primary-subtle; emphasised links |
| `on-primary` | `#FFFFFF` | `hsl(0 0% 100%)` | `#0B1220` | `hsl(220 49% 8%)` | Text and icons placed on primary / primary-hover |
| `success` | `#15803D` | `hsl(142 72% 29%)` | `#4ADE80` | `hsl(142 69% 58%)` | Success icon and graphical use |
| `success-subtle` | `#F0FDF4` | `hsl(138 76% 97%)` | `#0F2B1C` | `hsl(148 48% 11%)` | Success chip / banner fill |
| `success-text` | `#166534` | `hsl(143 64% 24%)` | `#86EFAC` | `hsl(142 77% 73%)` | Text on success-subtle |
| `warning` | `#B45309` | `hsl(26 90% 37%)` | `#FBBF24` | `hsl(43 96% 56%)` | Warning icon and graphical use |
| `warning-subtle` | `#FFFBEB` | `hsl(48 100% 96%)` | `#33270B` | `hsl(42 65% 12%)` | Warning chip / banner fill |
| `warning-text` | `#92400E` | `hsl(23 82% 31%)` | `#FCD34D` | `hsl(46 97% 65%)` | Text on warning-subtle |
| `danger` | `#B91C1C` | `hsl(0 74% 42%)` | `#F87171` | `hsl(0 91% 71%)` | Danger icon, destructive button fill, error border |
| `danger-subtle` | `#FEF2F2` | `hsl(0 86% 97%)` | `#3A1416` | `hsl(357 49% 15%)` | Danger chip / banner fill |
| `danger-text` | `#991B1B` | `hsl(0 70% 35%)` | `#FCA5A5` | `hsl(0 94% 82%)` | Text on danger-subtle |
| `info` | `#0369A1` | `hsl(201 96% 32%)` | `#38BDF8` | `hsl(198 93% 60%)` | Info icon and graphical use |
| `info-subtle` | `#F0F9FF` | `hsl(204 100% 97%)` | `#0C2A3D` | `hsl(203 67% 14%)` | Info chip / banner fill |
| `info-text` | `#075985` | `hsl(201 90% 27%)` | `#7DD3FC` | `hsl(199 95% 74%)` | Text on info-subtle |
| `focus` | `#1D4ED8` | `hsl(224 76% 48%)` | `#93C5FD` | `hsl(212 96% 78%)` | 2px keyboard focus ring (3:1 required) |

Usage rules: neutrals are about nine-tenths of every screen; `primary` is the only accent. Text always sits on its paired surface (never `primary` text on `primary-subtle`; use `primary-text`). Status colour is never the only signal: pair it with a label and an icon. A component uses at most two colours. Hover and active states are a darker or lighter step of the same hue, never a new colour. Components reference **tokens only**; a raw HEX in a component is a defect. There is no second accent and no gradient. Dark theme has its own neutral scale; it is not an inversion of the light one.

#### 2.1.2 Navigation rail (identical in both themes)

| Token | HEX | HSL | Use |
|---|---|---|---|
| `nav-bg` | `#0F172A` | `hsl(222 47% 11%)` | Sidebar background (same in light and dark) |
| `nav-text` | `#CBD5E1` | `hsl(213 27% 84%)` | Sidebar item text |
| `nav-text-active` | `#FFFFFF` | `hsl(0 0% 100%)` | Active sidebar item text |
| `nav-active-bg` | `#1E293B` | `hsl(217 33% 17%)` | Active sidebar item fill |
| `nav-indicator` | `#60A5FA` | `hsl(213 94% 68%)` | Active item left indicator bar (marks the selected page) |
| `nav-muted` | `#94A3B8` | `hsl(215 20% 65%)` | Sidebar section labels |

#### 2.1.3 Data-visualisation palette

Series colours are the categorical order from the `dataviz` skill, re-checked against Bizora's own surfaces (§2.1.4).

| # | Series | Light HEX (vs `surface`) | Dark HEX (vs `surface`) |
|---|---|---|---|
| 1 | Series 1 · blue | `#2A78D6` (4.4:1) | `#3987E5` (4.8:1) |
| 2 | Series 2 · orange | `#EB6834` (3.2:1) | `#D95926` (4.5:1) |
| 3 | Series 3 · aqua | `#1BAF7A` (2.8:1) | `#199E70` (5.1:1) |
| 4 | Series 4 · yellow | `#EDA100` (2.2:1) | `#C98500` (5.7:1) |
| 5 | Series 5 · magenta | `#E87BA4` (2.7:1) | `#D55181` (4.4:1) |
| 6 | Series 6 · green | `#008300` (4.9:1) | `#008300` (3.5:1) |
| 7 | Series 7 · violet | `#6250D6` (5.8:1) | `#9085E9` (5.6:1) |
| 8 | Series 8 · red | `#E34948` (4.0:1) | `#E66767` (5.4:1) |

Rules: at most **six** series in a chart, in order; beyond that group into "Other". Scatter-type charts (every pair visible at once) use at most **three**. Light-theme slots 3, 4 and 5 are below 3:1 against `surface`, so every chart carries direct labels or a data-table alternative, and every mark also has a marker shape or label in addition to colour. Delta arrows are **neutral by default**: the backend reports movement only (`INCREASED`/`DECREASED`/`UNCHANGED`/`UNAVAILABLE`) and says improvement depends on the metric's polarity. Colour a delta success or danger only when the server supplies that polarity; the Overview KPI rules carry a per-KPI `direction` field (reference Part C, V-CFG), so check its allowed values there before relying on it.

#### 2.1.4 Contrast verification (WCAG 2.2) and chart check

Computed with the WCAG relative-luminance formula for every foreground/background pair the system uses: **31 pairs per theme pass, 0 fail**, plus the navigation rail. The input-border token is separate from the decorative border because WCAG 1.4.11 requires 3:1 for control boundaries. The chart colours were run through the `dataviz` validator (script `validate_palette.js`): lightness band, chroma floor, colour-blind separation and normal-vision separation all pass in both themes (worst adjacent colour-blind ΔE 9.1 light / 8.4 dark against a target of 8; worst normal-vision ΔE 19.3). The only warning is light-theme contrast for three series, which the label rule above resolves. The first three series also pass the all-pairs test in both themes.

| Pair | Light | Dark | Required |
|---|---|---|---|
| Body text (`text` on `surface`) | 17.9:1 | 15.9:1 | 4.5:1 |
| Secondary text (`text-secondary` on `surface`) | 10.4:1 | 11.7:1 | 4.5:1 |
| Muted text on table header (`text-muted` on `surface-subtle`) | 5.7:1 | 6.1:1 | 4.5:1 |
| Primary button label (`on-primary` on `primary`) | 6.7:1 | 7.4:1 | 4.5:1 |
| Selected-state text (`primary-text` on `primary-subtle`) | 8.0:1 | 10.5:1 | 4.5:1 |
| Success chip (`success-text` on `success-subtle`) | 6.8:1 | 10.8:1 | 4.5:1 |
| Warning chip (`warning-text` on `warning-subtle`) | 6.8:1 | 10.1:1 | 4.5:1 |
| Danger chip (`danger-text` on `danger-subtle`) | 7.6:1 | 8.6:1 | 4.5:1 |
| Info chip (`info-text` on `info-subtle`) | 7.1:1 | 8.9:1 | 4.5:1 |
| Input boundary (`border-input` on `surface`) | 3.8:1 | 4.1:1 | 3.0:1 |
| Focus ring (`focus` on `surface`) | 6.7:1 | 9.7:1 | 3.0:1 |
| Sidebar item (`nav-text` on `nav-bg`) | 12.0:1 | same | 4.5:1 |
| Sidebar active item (`nav-text-active` on `nav-active-bg`) | 14.6:1 | same | 4.5:1 |
| Sidebar section label (`nav-muted` on `nav-bg`) | 7.0:1 | same | 4.5:1 |
| Active indicator bar (`nav-indicator` on `nav-bg`) | 7.0:1 | same | 3.0:1 |

#### 2.1.5 `tokens.css` (generated from the table above; do not edit by hand)

```css
:root {
  color-scheme: light;
  --color-canvas: #F8FAFC;
  --color-surface: #FFFFFF;
  --color-surface-subtle: #F1F5F9;
  --color-border: #E2E8F0;
  --color-border-input: #76859B;
  --color-text: #0F172A;
  --color-text-secondary: #334155;
  --color-text-muted: #526278;
  --color-primary: #1D4ED8;
  --color-primary-hover: #1E40AF;
  --color-primary-subtle: #EFF6FF;
  --color-primary-text: #1E40AF;
  --color-on-primary: #FFFFFF;
  --color-success: #15803D;
  --color-success-subtle: #F0FDF4;
  --color-success-text: #166534;
  --color-warning: #B45309;
  --color-warning-subtle: #FFFBEB;
  --color-warning-text: #92400E;
  --color-danger: #B91C1C;
  --color-danger-subtle: #FEF2F2;
  --color-danger-text: #991B1B;
  --color-info: #0369A1;
  --color-info-subtle: #F0F9FF;
  --color-info-text: #075985;
  --color-focus: #1D4ED8;
  --chart-1: #2A78D6;
  --chart-2: #EB6834;
  --chart-3: #1BAF7A;
  --chart-4: #EDA100;
  --chart-5: #E87BA4;
  --chart-6: #008300;
  --chart-7: #6250D6;
  --chart-8: #E34948;
  --color-nav-bg: #0F172A;
  --color-nav-text: #CBD5E1;
  --color-nav-text-active: #FFFFFF;
  --color-nav-active-bg: #1E293B;
  --color-nav-indicator: #60A5FA;
  --color-nav-muted: #94A3B8;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --color-canvas: #0B1220;
    --color-surface: #111A2B;
    --color-surface-subtle: #18233A;
    --color-border: #243049;
    --color-border-input: #6B7C98;
    --color-text: #F1F5F9;
    --color-text-secondary: #CBD5E1;
    --color-text-muted: #94A3B8;
    --color-primary: #60A5FA;
    --color-primary-hover: #93C5FD;
    --color-primary-subtle: #14264D;
    --color-primary-text: #BFDBFE;
    --color-on-primary: #0B1220;
    --color-success: #4ADE80;
    --color-success-subtle: #0F2B1C;
    --color-success-text: #86EFAC;
    --color-warning: #FBBF24;
    --color-warning-subtle: #33270B;
    --color-warning-text: #FCD34D;
    --color-danger: #F87171;
    --color-danger-subtle: #3A1416;
    --color-danger-text: #FCA5A5;
    --color-info: #38BDF8;
    --color-info-subtle: #0C2A3D;
    --color-info-text: #7DD3FC;
    --color-focus: #93C5FD;
    --chart-1: #3987E5;
    --chart-2: #D95926;
    --chart-3: #199E70;
    --chart-4: #C98500;
    --chart-5: #D55181;
    --chart-6: #008300;
    --chart-7: #9085E9;
    --chart-8: #E66767;
  }
}

:root[data-theme="dark"] {
  color-scheme: dark;
  --color-canvas: #0B1220;
  --color-surface: #111A2B;
  --color-surface-subtle: #18233A;
  --color-border: #243049;
  --color-border-input: #6B7C98;
  --color-text: #F1F5F9;
  --color-text-secondary: #CBD5E1;
  --color-text-muted: #94A3B8;
  --color-primary: #60A5FA;
  --color-primary-hover: #93C5FD;
  --color-primary-subtle: #14264D;
  --color-primary-text: #BFDBFE;
  --color-on-primary: #0B1220;
  --color-success: #4ADE80;
  --color-success-subtle: #0F2B1C;
  --color-success-text: #86EFAC;
  --color-warning: #FBBF24;
  --color-warning-subtle: #33270B;
  --color-warning-text: #FCD34D;
  --color-danger: #F87171;
  --color-danger-subtle: #3A1416;
  --color-danger-text: #FCA5A5;
  --color-info: #38BDF8;
  --color-info-subtle: #0C2A3D;
  --color-info-text: #7DD3FC;
  --color-focus: #93C5FD;
  --chart-1: #3987E5;
  --chart-2: #D95926;
  --chart-3: #199E70;
  --chart-4: #C98500;
  --chart-5: #D55181;
  --chart-6: #008300;
  --chart-7: #9085E9;
  --chart-8: #E66767;
}
```

#### 2.1.6 High-Craft Surface Elevation and Translucent Badges (2026-11-10)

To eliminate flat "AI-generated slop" and achieve modern SaaS visual craftsmanship (Linear / Vercel / Stripe aesthetic):

1. **Surface Layering & Recessed Wells:**
   - `--color-surface-elevated`: `#ffffff` (light) / `#1b2330` (dark).
   - `--color-surface-recessed`: `#edf0f4` (light) / `#0a0e14` (dark) for input backgrounds, code containers, and empty state pods.
   - `--color-border-subtle`: Hairline translucent border dividers (`rgba(255, 255, 255, 0.08)` in dark mode).
   - `--color-border-strong`: Medium-contrast control boundary for hover and focus states.

2. **Specular Top Hairline Highlights & Elevation:**
   - `--shadow-card`: `0 1px 3px 0 rgba(0, 0, 0, 0.4), inset 0 1px 0 0 rgba(255, 255, 255, 0.05)` in dark mode.
   - `--shadow-button-primary`: `inset 0 1px 0 rgba(255, 255, 255, 0.22), 0 1px 2px rgba(18, 28, 43, 0.14)`.

3. **Translucent Status Pills & Banners:**
   - Status chips and badges utilize pill radius (`var(--radius-full)`), `color-mix(in srgb, var(--tone) 24%, transparent)` hairline borders, and muted font-weight (500, 11px) instead of harsh 100% solid saturated borders.
   - Alert banners feature low-opacity tinted surfaces, 28x28 rounded icon badges, and hairline borders with subtle top highlights.
   - Form inputs feature recessed wells, hairline borders, and glowing multi-ring focus outlines.

4. **Interactive Component Showcase (`/business/[id]/ui-kit`):**
   - Live design tokens & color swatch grid with quick-copy tooltips.
   - Sticky quick-jump pill navigation bar with backdrop blur.
   - Typography scale specimens and structured demo containers.

### 2.2 Typography

Three families, all open-licence Google Fonts. Every stack ends with **Noto Sans Bengali** because the product has a
per-business locale setting (`business-configuration.md`: "Locale Settings — preferred language, regional formatting")
and customer messages can contain Bangla, so a Latin-only stack would render tofu boxes.

| Role | Family | Weights | Stack |
|---|---|---|---|
| Heading | **Plus Jakarta Sans** | 600, 700 | `"Plus Jakarta Sans", "Noto Sans Bengali", system-ui, sans-serif` |
| Body / UI | **Inter** | 400, 500, 600 | `"Inter", "Noto Sans Bengali", system-ui, sans-serif` |
| Data / metrics / identifiers | **JetBrains Mono** | 400, 500, 600 | `"JetBrains Mono", "Noto Sans Bengali", ui-monospace, monospace` |

Strict type scale (px, 1rem = 16px):

| Style | Size / line-height | Weight | Tracking | Family | Use |
|---|---|---|---|---|---|
| `display` | 40 / 48 | 700 | −0.02em | Heading | Sign-in title, empty-state headline |
| `h1` | 28 / 36 | 700 | −0.015em | Heading | Page title (one per page) |
| `h2` | 22 / 30 | 600 | −0.01em | Heading | Section title |
| `h3` | 18 / 26 | 600 | 0 | Heading | Card / panel title |
| `h4` | 15 / 22 | 600 | 0 | Heading | Drawer and subsection title |
| `body-lg` | 16 / 24 | 400 | 0 | Body | AI assistant answers, long-form text |
| `body` | 14 / 20 | 400 | 0 | Body | Default UI text |
| `body-strong` | 14 / 20 | 600 | 0 | Body | Emphasis, button labels |
| `small` | 13 / 18 | 400 | 0 | Body | Table cells, helper text |
| `caption` | 12 / 16 | 500 | 0.01em | Body | Chips, timestamps, axis labels |
| `overline` | 11 / 16 | 600 | +0.06em, uppercase | Body | Section labels, column groups |
| `metric-xl` | 32 / 38 | 600 | −0.01em | Mono | Hero KPI value |
| `metric` | 24 / 30 | 600 | 0 | Mono | KPI card value |
| `data` | 13 / 20 | 400 | 0 | Mono | Numeric table cells, IDs, JSON, metric keys |

Text formatting rules (each one is driven by how the backend stores or returns data):

1. **Numbers** use `font-variant-numeric: tabular-nums`, are right-aligned in tables, and group thousands per the business locale.
2. **Money** is shown as the ISO code plus amount, e.g. `BDT 2,500.00`, never a bare symbol. The backend isolates every
   amount to one currency per observation and never sums across currencies, so the UI must always show which currency a
   figure is in, and must never add figures of different currencies. The code also avoids depending on a currency glyph.
3. **Ratios** arrive from the Business Intelligence registry as **fractions** (0.17), not percentages. Multiply by 100 and
   show one decimal: `17.0%`. **Durations** arrive in **seconds**; format as `2d 4h`, `3h 12m`, `45s`.
4. **Dates and times** render in the **business timezone** (`Business.timezone`, default `Asia/Dhaka`), not the browser's.
   Format `DD MMM YYYY, HH:mm`. Recent times (< 24 h) may show relative text with the absolute value on hover.
   Date ranges are **half-open `[start, end)`**: label the end as "up to, not including".
5. **Missing data is never zero.** Absence renders as an em dash `—` with the tooltip "No data recorded". A measured
   zero renders as `0`. This mirrors the backend rule that unavailable metrics are never stored as 0.
6. **Enums** (statuses, severities, types) arrive in `UPPER_SNAKE_CASE`. Display as sentence case ("Out for delivery");
   keep the raw value in the tooltip and in `data-value` for tests. Unknown values must render verbatim in a neutral
   chip, never be hidden — the backend deliberately reports unrecognised statuses instead of dropping them.
7. **Identifiers** (IDs, metric keys such as `bi.metric.revenue_gross.v1`, request IDs, JSON) use `data` mono and are
   click-to-copy.
8. Headings and buttons use sentence case. One `h1` per page. Prose measure is capped at 72 characters.
9. Long text truncates with a single-line ellipsis plus tooltip; tables never wrap numeric columns.

### 2.3 Layout and component standards

**Grid and shell**

| Item | Value |
|---|---|
| Breakpoints | `sm` 640 · `md` 768 · `lg` 1024 · `xl` 1280 · `2xl` 1536 (minimum supported width 360) |
| Grid | 12 columns, gutter 24 px at ≥ 1024, 16 px below |
| Content max width | 1440 px, centred; page padding 24 px (16 px below `md`) |
| Sidebar | 256 px expanded, 72 px collapsed, fixed; becomes an overlay drawer below `lg` |
| Top bar | 56 px, sticky: business switcher · data-freshness indicator · theme toggle · user menu |
| Sidebar surface | `nav-bg` in **both** themes (dark navigation anchors the layout) |

**Spacing** (4 px base): `space-0` 0 · `1` 4 · `2` 8 · `3` 12 · `4` 16 · `5` 20 · `6` 24 · `8` 32 · `10` 40 · `12` 48 · `16` 64.
Card inner padding 20; section gap 24; form field gap 16; table cell padding 12 × 12 (compact) or 16 × 12 (comfortable).

**Radius**: `r-sm` 4 (chips, code) · `r-md` 8 (buttons, inputs, cards) · `r-lg` 12 (panels, modals, drawers) · `r-xl` 16 (hero cards) · `r-full` 999 (pills, avatars).

**Elevation** (light theme; in dark theme replace shadows with a 1 px `border` and a lighter `surface`):

| Level | Shadow | Use |
|---|---|---|
| `e0` | none, 1 px `border` | Flat cards, tables |
| `e1` | `0 1px 2px rgba(15,23,42,0.06)` | Raised cards, sticky headers |
| `e2` | `0 4px 12px rgba(15,23,42,0.10)` | Popovers, menus, tooltips |
| `e3` | `0 12px 32px rgba(15,23,42,0.18)` | Modals, drawers, command palette |

**Interaction patterns**

- Focus: a 2 px `focus` ring with a 2 px offset on every interactive element; never remove it. Minimum hit target 36 px
  (desktop) and 44 px (touch).
- Motion budget: state changes only. Hover 120 ms and panels or drawers 200 ms, ease-out, opacity or a short translate. No scroll-triggered
  animation, no parallax, no animated page transitions, no GSAP or similar timeline library, no looping decoration. Honour `prefers-reduced-motion`
  (no shimmer, no slide).
- Cards: prefer sections, dividers and tables. Use a card only when the container itself is interactive (a clickable item, a form, a
  KPI tile that drills down). Never stack a card inside a card.
- Loading: skeleton blocks that match the final layout; never a bare spinner for a page. Buttons show an inline spinner and
  stay the same width.
- Disabled: 50 % opacity, `not-allowed`, and a tooltip stating why (for example "Requires Manager role").
- Destructive or consequential actions (rejecting or executing an AI action, retrying a sync, replaying a webhook,
  rebuilding a graph, running the BI pipeline) open a confirmation dialog that names the target and the effect.
- Tables: server-side pagination, sticky header, sortable and resizable columns, column visibility menu, density toggle
  (row 40 compact / 48 comfortable), keyboard row navigation, row click opens a right-hand detail drawer.
- Forms: label above field, helper text below, inline validation on blur, the server's field errors mapped to fields, a
  single summary banner for non-field errors, unsaved-changes guard.
- Accessibility floor: WCAG 2.2 AA, semantic landmarks, one `h1`, labelled controls, colour is never the only signal
  (every status chip pairs colour with a label and an icon), charts expose a data-table alternative.

**Component inventory**: Button (primary / secondary / ghost / danger; sm 32, md 36, lg 44) · IconButton · Input · Textarea ·
Select · Combobox · DateRangePicker · Checkbox · Radio · Switch · Tabs · SegmentedControl · DataTable · StatusChip ·
SeverityChip · ConfidenceMeter · Card · KpiCard · DeltaIndicator · ChartCard · Drawer · Modal · ConfirmDialog · Toast ·
Banner · EmptyState · UnavailableState · Skeleton · Timeline · EvidencePanel · JsonViewer · GraphCanvas · Breadcrumbs ·
Avatar · Tooltip · Pagination · CommandPalette.

---

## 3. Module breakdown

Navigation groups in the app shell: **Overview · Operations · Intelligence · Data & identity · Integrations · Settings**.
Every module is tied to its backend domain, its specification headings and its endpoints. Endpoint ids (`D#`, `P#`, `E#`,
`BI-#`, `BG-#`, `CFG #`) are defined in [`frontend-api-reference.md`](frontend-api-reference.md). `B` = `/api/businesses/{businessId}/`.
All SPA routes are `/b/:businessId/…`.

**Role gating (verified).** Domain API: `VIEWER` reads; `OPERATOR`, `MANAGER`, `OWNER` write; `MANAGER`/`OWNER` only for identity,
action review and merge dry-run. AI business routes accept *any* active membership role; AI action routes need `OWNER`,
`ADMIN` or `OPERATOR`. Observability, Overview and Configuration use `BusinessAccess`: `READER` reads, `MANAGER` writes.
UI rule: `canWrite = role ≠ VIEWER`; `canManage = role ∈ {MANAGER, OWNER}`. The server is the authority; the UI hides and
disables, then handles `403`.

### 3.0 Page plan: nine workspaces (read this before the module list)

A backend module below is **not** a page. A page is a job a person does; modules share pages as tabs, rows open drawers, consequential
actions open dialogs. This is decision D-F18. The per-module routes in the module blocks map to a tab of the page shown here.

| # | Page | Route | Tabs and views | Modules |
|---|---|---|---|---|
| P1 | Sign-in and business choice | `/sign-in` | sign-in · choose business | M0 |
| P2 | Overview | `/b/:id/overview` | Overview · Trends · Health | M1 |
| P3 | Customers (with Customer 360) | `/b/:id/customers/:customerId?` | list + 360: Timeline · Orders and payments · Conversations and calls · Deliveries · Website and marketing · Graph · Identity | M2, part of M16 |
| P4 | Commerce | `/b/:id/commerce/:tab` | Orders · Payments and refunds · Deliveries · Products | M3, M4, M5, M11 |
| P5 | Support | `/b/:id/support/:tab` | Inbox · Queue · Calls, with assign and handover dialogs | M6, M7, M8, M12 |
| P6 | Growth | `/b/:id/growth/:tab` | Campaigns · Website | M9, M10 |
| P7 | Intelligence | `/b/:id/intelligence/:tab` | Facts and issues · Graph · Metrics and analysis · Pipeline | M13, M14 |
| P8 | AI | `/b/:id/ai/:tab` | Assistant · Recommendations and actions · Audit | M15 |
| P9 | Admin | `/b/:id/admin/:section` | Identity · Integrations · Configuration · Knowledge (design-only) · Simulation (design-only) | M16–M20 |

Demo story: P2 shows a problem → P7 Facts and issues shows the evidence → P7 Graph shows the connections → P8 explains and proposes →
a human approves in P8 (simulated). Build order for the code follows the same story, then P3, P5, P4, P6, P9. The feature-to-page
coverage table is in [`frontend-stitch-prompt.md`](frontend-stitch-prompt.md) §5.

### M0 — Shell, session and business context
| | |
|---|---|
| Spec | none (platform) |
| Route | `/sign-in`, `/b/:businessId/…`, `/403`, `/404` |
| Screens | Sign-in (hand-off to Django form, §1.4) · Business entry (type or deep-link a business id) · App shell (sidebar, top bar with business switcher, data-freshness indicator, theme toggle, user menu) · Session-expired, forbidden and not-found pages |
| Backend | `P1` `GET /api/` (public health) · `D8` `GET B overview/` returns `business{id,name,currency,timezone}` once the id is known · `POST /ops/logout/` |
| Readiness | **PARTIAL.** No "me", no "my businesses", no role (P2). The business currency and timezone are read from `D8` and drive all formatting. |

### M1 — Business overview and monitoring
| | |
|---|---|
| Spec | `business-oparations` §1; `overview-monitoring` §1–8 |
| Route | `/b/:businessId/overview` |
| Screens | Executive summary header · KPI cards (revenue, orders, customers, marketing, website, support, delivery) with period comparison · Performance trends (time series, dimension comparison) · Business health (per-domain state, evidence, trend) · Active issues (severity, confidence, entity) · Recent activity feed with filters · Recommendations feed (priority, evidence, approval status) · Cross-domain monitoring panels · Drill-down to entity and evidence |
| Backend (live) | `D8` canonical counts, recent activity (audit), `intelligence{…}`; `business_health` is **UNAVAILABLE-BY-DESIGN** |
| Backend (unmounted) | Overview module, prefix `B overview/`: `summary/`, `kpis/`, `trends/`, `health/`, `issues/` (+`{pk}/`), `activity/`, `recommendations/` (+`{pk}/`), `cross-domain/`, `catalog/`, `configuration/` (GET, PUT), `entities/{entity_type}/{pk}/`, `evidence/{facts\|snapshots\|relationships\|nodes\|edges\|knowledge}/{pk}/` |
| Readiness | `D8` **LIVE\***; the rest **UNMOUNTED**. The Overview code hard-codes `/api/businesses/<id>/overview/…` into every `drilldown`/`links` value, so it **must** be re-mounted at exactly that prefix. KPI values come from `MetricSnapshot` rows, which nothing records at runtime (P4): a `null` value with `status:"UNAVAILABLE"` means "no snapshot", never zero. |
| UI rules | Show `status`, `reason`, `freshness.age_seconds` and `sources[]` from the server rather than computing locally. Decimal strings (`"123.450000"`) are formatted per §2.2. |

### M2 — Customers and Customer 360
| | |
|---|---|
| Spec | `business-data` §2; `business-oparations` §2 |
| Route | `/b/:businessId/customers`, `/customers/:id` |
| Screens | Customer list (filters: `contact`+`contact_type`, `tag`, `q` on display name, `status`) · **Customer 360**: profile, contacts, tags, external identities, identity links, orders, payments, refunds, conversations, messages, calls, shipments, sessions, website events, marketing conversions, timeline, intelligence, graph view · Status change (modal) · Retargeting context |
| Backend | `D1`/`D3` `customers` (list/detail) · `D9` `customers/{pk}/360/` · `D22` `graph-context/customer/{pk}/` · `D20` `customers/{pk}/retargeting-context/` · `D4` transition (`ACTIVE`→`INACTIVE`/`BLOCKED`; `INACTIVE`→`ACTIVE`/`BLOCKED`; `BLOCKED`→`ACTIVE`) · `D2` `contacts`, `tags`, `customer-references` |
| Readiness | **LIVE\***. Each 360 section is capped at 50 rows with `truncated`; page the child list for more. **No edit of customer fields** (no PATCH). Post tags upper-case or `?tag=` filters will miss them. `recording_url`/`source_metadata` never appear. |

### M3 — Products and variants
| | |
|---|---|
| Spec | `business-data` §1; `business-oparations` §3 |
| Route | `/b/:businessId/products`, `/products/:id` |
| Screens | Catalog list (filters `status`, `category`, `sku`, `q`) · Product detail: variants, images, orders, external references, customers, shipments, calls, related conversations · Add variant (modal) · Map product to an external reference (modal) · Variant price/stock update (modal) · Pre-flight "assess product" before create |
| Backend | `D1`/`D3` `products`, `variants`, `product-images`, `product-references` · `D5` `variants/{pk}/update/` · `D25` `products/assess/` · `D4` transition (`ACTIVE/INACTIVE/ARCHIVED`) |
| Readiness | **LIVE\***. No product PATCH. A duplicate SKU without a source mapping returns `400 PRODUCT_REVIEW_REQUIRED`; a distinct product needs `MANAGER`/`OWNER` with `deduplication`. Performance, marketing and support context beyond the detail sections is Business Intelligence/Graph (**BLOCKED/UNAVAILABLE**). |

### M4 — Orders
| | |
|---|---|
| Spec | `business-data` §3; `business-oparations` §4 |
| Route | `/b/:businessId/orders`, `/orders/:id` |
| Screens | Order list (filters `customer`, `status`, `q` on order number, `since`/`until` on `ordered_at`) · Order detail: items, payments, refunds, shipments, calls, status history, related conversations, customer context · Status transition (modal, shows only legal next states) |
| Backend | `D1`/`D3` `orders` · `D4` transition with `expected_status` |
| Readiness | **LIVE\***. Orders are immutable after create; status moves only through `D4`. Legal moves: PENDING→CONFIRMED/CANCELLED · CONFIRMED→PROCESSING/CANCELLED · PROCESSING→SHIPPED/CANCELLED · SHIPPED→DELIVERED/RETURNED · DELIVERED→RETURNED/REFUNDED · RETURNED→REFUNDED. `→REFUNDED` needs completed refunds ≥ order total (`REFUND_LEDGER_REQUIRED`). Campaign attribution context is not exposed here. |

### M5 — Payments, refunds and financial timeline
| | |
|---|---|
| Spec | `business-data` §4; `business-oparations` §5 |
| Route | `/b/:businessId/payments`, `/payments/:id`, `/financial-timeline` |
| Screens | Payment list (filters `order`, `customer`, `payment_method`, `status`; **no text search** — `q` returns 400) · Payment detail with refunds · Refund (modal: amount ≥ 0.01, reason) · Financial timeline (rows keyed by `(entity_kind, id)` — `id` repeats across `PAYMENT`/`REFUND`) · Failure investigation = filter `status=FAILED` |
| Backend | `D1`/`D3` `payments`, `refunds` · `D6` `financial-timeline/` · `D4` transition · `D2` `refunds` (idempotent create) |
| Readiness | **LIVE\***. Payment `PARTIALLY_REFUNDED`/`REFUNDED` are derived from the refund ledger and cannot be set directly. Refund total may not exceed the payment (`EXCESSIVE_REFUND`). Send money as strings (`"12.50"`). |

### M6 — Unified inbox
| | |
|---|---|
| Spec | `business-data` §5–6; `business-oparations` §6 |
| Route | `/b/:businessId/inbox`, `/inbox/:conversationId` |
| Screens | Three-pane inbox: conversation list (filters `channel`, `priority`, `status`, `q` over subject/customer/message text) · conversation thread (messages ascending, attachments, delivery state, read state) · context panel (customer 360, order, internal notes, history, policy/AI-reply placeholders) · Reply composer (**saves a PENDING outgoing message; nothing is sent**) · Add note · Media reply · Mark message read |
| Backend | `D1`/`D3` `conversations`, `messages`, `notes`, `attachments`, `participants` · `D18` `conversations/{pk}/context/?order=` · `D16` `messages/{pk}/read/` · `D17` priority · `D2` `messages`/`notes` · `E2` AI suggested reply |
| Readiness | **LIVE\***. Customer message text arrives wrapped in `<untrusted_customer_data>`: strip for display, never render as HTML. `policy_context` and `suggested_reply` in `D18` are **UNAVAILABLE-BY-DESIGN**. The label on the composer must say "Saved — not sent". |

### M7 — Support queue
| | |
|---|---|
| Spec | `business-oparations` §7 |
| Route | `/b/:businessId/queue` |
| Screens | Queue table (open + pending conversations, urgent first then oldest) · filters `assigned` = `me`/`unassigned`/`team`, `priority`, `status`, `channel` · Capability tiles for overdue detection, AI escalation signals and queue metrics |
| Backend | `D10` `support-queue/` (fixed ordering, no `ordering` param; any other query key → 400) |
| Readiness | **LIVE\***; the three capability tiles are **UNAVAILABLE-BY-DESIGN**. `assigned=team` requires the caller to belong to a support team. |

### M8 — Assignment and AI ↔ human handover
| | |
|---|---|
| Spec | `business-oparations` §8–9 |
| Route | Actions inside the inbox thread (drawer/modal) |
| Screens | Assign (AGENT/TEAM/AI/UNASSIGNED + reason) · Release · Reassign · Assignment history · Hand over to human / return to AI (reason, summary) · Handover history |
| Backend | `D11` `conversations/{pk}/assign/` · `D12` `conversations/{pk}/handover/` · history sections in `D3` · AI-side equivalents `E3`–`E5` |
| Readiness | **PARTIAL.** There is **no endpoint listing agents or teams**, so the assignee picker cannot be populated (the old Django UI reads them straight from the database). Handover to `HUMAN` needs an agent `assignee_id` in practice. Customer notification on handover is `UNAVAILABLE_PROVIDER_TRANSPORT`. Automatic assignment hooks: **NO ENDPOINT FOUND**. |

### M9 — Marketing operations
| | |
|---|---|
| Spec | `business-data` §7; `business-oparations` §10 |
| Route | `/b/:businessId/marketing`, `/marketing/:campaignId` |
| Screens | Campaign list (filters `status`, `q`; **not** `provider`/`platform`) · Campaign detail: daily metrics, conversions, ad sets, ads, creatives · AI "explain campaign" · Suggested actions with approval (see M15) |
| Backend | `D1`/`D3` `campaigns`, `campaign-metrics`, `conversions`, `ad-accounts`, `ad-sets`, `creatives`, `ads` · `D20` · `E6` AI marketing explain · `D15`/`E13`–`E15` approval |
| Readiness | **LIVE\*** for canonical records. Attributed revenue, trends and issue indicators are Business Intelligence service-only → **BLOCKED**. Conversion attribution is limited to `PLATFORM_REPORTED`/`DIRECT_SOURCE_REPORTED`; label platform-reported figures as such. |

### M10 — Website performance
| | |
|---|---|
| Spec | `business-data` §8; `business-oparations` §11 |
| Route | `/b/:businessId/website`, `/website/visitors/:id` |
| Screens | Visitors, sessions and events lists · Visitor journey timeline (ascending) · Seven analysis panels (traffic source, funnel, cart abandonment, checkout drop-off, landing page, device, experience signals) |
| Backend | `D1`/`D3` `visitors`, `sessions`, `website-events` · `D19` `visitors/{pk}/journey/` · `D7` `website-performance/` |
| Readiness | Lists **LIVE\***. In `D7` the seven analysis keys always return **UNAVAILABLE-BY-DESIGN**, owner "Business Intelligence". |

### M11 — Delivery and shipments
| | |
|---|---|
| Spec | `business-data` §9; `business-oparations` §12 |
| Route | `/b/:businessId/delivery`, `/delivery/:shipmentId` |
| Screens | Shipment list (filters `customer`, `order`, `provider`, `status`, `q` on tracking code) · Shipment detail with tracking timeline · Failed-delivery queue (= `status=FAILED`) · Return tracking · Prepare submit/cancel (shows the prepared request, **not executed**) |
| Backend | `D1`/`D3` `shipments`, `shipment-events` · `D4` transition · `D21` `operations/shipment_submit\|shipment_cancel/{pk}/prepare/` (empty body; underscores) |
| Readiness | **LIVE\***. Courier and regional performance (Business Intelligence delivery) are service-only → **BLOCKED**. No live courier tracking; submission is `NOT_EXECUTED`. |

### M12 — Calls
| | |
|---|---|
| Spec | `business-data` §10; `business-oparations` §13 |
| Route | `/b/:businessId/calls`, `/calls/:id` |
| Screens | Call list (filters `customer`, `order`, `direction`, `status`; **no text search**) · Call detail: event timeline, transcript, summary · Callbacks list and schedule (modal) · Prepare outbound call |
| Backend | `D1`/`D3` `calls`, `call-events`, `transcripts`, `callbacks` · `D23` `callbacks/{pk}/schedule/` (future time only) · `D21` `call_initiate` · `E9` AI call summary |
| Readiness | **LIVE\***. `recording_access` is **UNAVAILABLE-BY-DESIGN** and recordings are never returned. |

### M13 — Business Intelligence (metrics, facts, issues, pipeline)
| | |
|---|---|
| Spec | `business-intelligence` §1–18 |
| Route | `/b/:businessId/intelligence/{metrics,facts,issues,pipeline}` |
| Screens | Metric catalogue (42 registered keys across Sales, Revenue, Customer, Marketing, Support, Website, Delivery) · Metric snapshot history chart · Facts list/detail with evidence · Issues list/detail with lifecycle (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`) · Pipeline run (shows relationship counts and `quarantined_records`) |
| Backend (unmounted) | `BI-1` `metrics/` · `BI-2` `metrics/{key}/snapshots/` · `BI-3`–`BI-6` `facts/` · `BI-7`–`BI-10` `issues/` · `BI-11` `pipeline/run/`. Live neighbour: `E12` `GET B issues/` (OPEN issues). |
| Readiness | **UNMOUNTED**, and as written every call returns 403 (nothing sets `request.business`). Large parts have **no HTTP surface**: relationship browsing, every metric calculation, attribution, anomaly rules, automatic fact/issue creation, fact/issue evidence rows. |
| UI rules | Ratios are fractions → percent. Durations are seconds. `GET metrics/` **writes** (syncs the registry). Facts: only `VERIFIED` in-window facts are visible, and a PATCH to any other status makes the fact vanish and un-editable — do not build a "history of invalidated facts". `POST` facts/issues are upserts: always send a distinct `rule_key`. Errors are generic by design (cannot tell causes apart). |

### M14 — Graph explorer and journeys
| | |
|---|---|
| Spec | `business-graph` §1–13 |
| Route | `/b/:businessId/graph`, `/graph/journeys/{customer,order,product,campaign}/:id`, `/graph/snapshots` |
| Screens | Graph canvas (root entity, direction, depth, node cap, filters) · Path finder between two entities with explanations · Customer and order journey timelines · Product and campaign journey summaries · Snapshot list/create/view · Rebuild graph (confirm dialog; `clean` is destructive) |
| Backend (unmounted) | `BG-1` `traversal/` · `BG-2` `paths/` (`explain=true`) · `BG-3` `query/` · `BG-4`–`BG-7` `journeys/{customer,order,product,campaign}/{id}/` · `BG-8`–`BG-10` `snapshots/` · `BG-11` `rebuild/`. Live neighbour: `D22` one-hop `graph-context/{kind}/{pk}/`. |
| Readiness | **UNMOUNTED**; imports fail on Python 3.12 (P3); and a graph built from real BI data has no edges (P3b). Journeys 400 with "has not been projected" until a rebuild has run. |
| UI rules | The API has **no server-side caps** on depth, nodes or limit, so the client enforces its own defaults (`max_depth` 2, `max_nodes` 200) and sends them explicitly. When `truncated` is true some edges reference missing nodes: drop them. Send datetimes with a timezone (`Z`). Filter lists are comma-separated. Edge names in the code (18 types, e.g. `PLACED_ORDER`, `HAS_PAYMENT`) differ from the spec's examples (`PAID_FOR`, `ATTRIBUTED_TO`, `PARTICIPATED_IN`, `CONTACTED`, `SHIPPED_AS`), which do not exist in code. |

### M15 — AI Intelligence
| | |
|---|---|
| Spec | `ai-intelligence` §1–18 |
| Route | `/b/:businessId/ai/{assistant,recommendations,actions}` |
| Screens | Business assistant chat (answer, grounding facts, open issues) · Support helpers inside the inbox (suggested reply, escalation check, handover summary, resume AI) · Campaign explainer · Issue diagnosis · Conversation and call summaries · Recommendations feed with evidence · Actions list with **approval flow** (approve/reject with a 3–1000 character note → execute) |
| Backend | `E1` assistant query · `E2`–`E5` support · `E6` marketing · `E7` diagnosis · `E8`–`E9` summaries · `E10` recommendations · `E11` actions · `E12` issues · `E13`–`E15` approve/reject/execute · `E16` second approval route (`MANAGER`/`OWNER`, requires verified evidence, never executes) |
| Readiness | **LIVE\*** but thin. Recommendations and actions are created only by service code no route calls, so `E10`/`E11` are empty. Without `BIZORA_LLM_URL` the LLM routes return canned text with HTTP 200 and still report a model name and token count — the UI cannot tell. Execution over HTTP is always **simulated**; a stuck `EXECUTING` has no recovery route. Two approval routes with different roles and rules exist (`OWNER/ADMIN/OPERATOR` vs `OWNER/MANAGER`). Calls block up to ~15 s: show progress. None accepts an idempotency key; escalate/handover/resume/summaries mutate data. |
| Action states | `SUGGESTED`, `APPROVED`, `REJECTED`, `EXECUTING`, `EXECUTED`, `FAILED` |

### M16 — Identity and resolution (MANAGER / OWNER only)
| | |
|---|---|
| Spec | `identity-resulation` §1–8 |
| Route | `/b/:businessId/identity/{canonical,external,links,conflicts,merge-candidates,history}` |
| Screens | Tables for canonical identities, external identities, links, conflicts, merge candidates, history · Register / link / unlink / resolve / verify-contact (forms) · Conflict review · Merge review and **dry-run plan** (fingerprint, safety errors, readiness, owner acknowledgements) · "Execute merge" is shown as **blocked by design** |
| Backend | `D13` `identity/{canonical\|external\|conflicts\|merge-candidates\|history\|links}/` · `D14` 16 POST commands · `D24` merge dry-run |
| Readiness | **LIVE\***. Physical merge is blocked by design (`BI_GRAPH_AI_MERGE_CONTRACT`). Link confidence may be `null` (manual). |

### M17 — Integrations and data observability
| | |
|---|---|
| Spec | `intregations` §1–8; `intrgration-data-observability` §1–8 |
| Route | `/b/:businessId/integrations/{connections,syncs,failed-records,webhooks,freshness,providers,errors,policies}` |
| Screens | Health summary · Connections (test) · Syncs with statistics and attempts (retry) · Failed records with grouping, lifecycle and retry · Webhooks with deliveries (replay) · Data freshness (`FRESH/DELAYED/STALE/UNAVAILABLE`) · Providers · Integration errors · Monitoring policies (manager) · Payload diagnostics (manager, redacted) |
| Backend (unmounted) | Observability module, original prefix `B observability/`: `summary/`, `connections/`(+test), `syncs/`(+`statistics/`, retry), `failed-records/`(+`groups/`, retry, PATCH), `webhooks/`(+replay), `freshness/`, `providers/`, `errors/`(+PATCH), `policies/` (GET, PUT), `payloads/{pk}/` |
| Readiness | **UNMOUNTED**; needs `BusinessAccess` (P2b). Operations are synchronous: HTTP 200 means *the attempt was recorded* — read `status` (`SUCCEEDED`/`FAILED`); `409` means `UNSUPPORTED`. No adapter is ever registered, so only mock connections run anything. Nothing in production writes observability data, so every list is empty until an integration owner publishes data. Live: `D26` contract calls, always UNAVAILABLE. |

### M18 — Configuration
| | |
|---|---|
| Spec | `business-configuration` §1–8 |
| Route | `/b/:businessId/settings/{profile,general,ai,knowledge,rules,policies,connections,sources,reprocessing,monitoring,freshness,effective,changes}` |
| Screens | Section forms (profile, general, AI, knowledge) with version-conflict handling · Rules and policies (create, edit, history) · Connections and sources (credentials as **references**, never raw secrets) · Reprocessing requests · Monitoring and freshness policy · Effective configuration · Change feed · Per-record revision history |
| Backend (unmounted) | Original prefix `B configuration/`; documented as 30 rows (`CFG #1`–`#30`) covering 29 URL patterns |
| Readiness | **UNMOUNTED**; needs `BusinessAccess` (P2b). Send the last-read `version` to get optimistic locking (`409` on mismatch); `freshness/` and `reprocessing/` do not support it. PUT is a **deep partial merge**: lists replace, keys cannot be removed. Credentials must be `env:BIZORA_BUSINESS_{id}_NAME` references; responses show only `{configured, fields}`. Do **not** echo a GET object back on PUT (output-only fields are rejected). The response scrubber rewrites ordinary text (e.g. "Basic delivery applies" → "Basic [REDACTED] applies"). Reprocessing only records a request (`worker_available:false`). |

### M19 — Business memory and knowledge
| | |
|---|---|
| Spec | `business-memory-knowledge` §1–19 |
| Readiness | **BLOCKED — NO ENDPOINT FOUND** for all 19 features (profile, policies, product/delivery/return knowledge, brand tone, support knowledge, goals, historical decisions, approved suggestions, sources, ingestion, processing, chunking, embeddings, vector/keyword/hybrid search, versioning). Everything is service-only. The only visible traces are `applied_policies` titles in `E2` and `active_goals` in `E6`, plus two live contract stubs that always return UNAVAILABLE. Design the screens; do not wire them. |

### M20 — Prototype simulation
| | |
|---|---|
| Spec | `prototype-simulation` §1–11 |
| Readiness | **BLOCKED — NO ENDPOINT FOUND** for all 11 headings. Simulation exists only as management commands (`simulate_configuration`, `simulate_observability`, `simulate_overview`, `demo_domains`, `demo_completion`, `preflight_domains`), each printing one JSON line. Nothing persists a report. Do not build a simulation UI until a backend surface exists. |

---

## 4. Backend connection and API matrix

The full, citation-level contracts (every route, parameter, body field, response field, enum and error) are in
[`frontend-api-reference.md`](frontend-api-reference.md). This section is the map and the rules a typed client must follow.

### 4.1 Domain-by-domain connection matrix

`B` = `/api/businesses/{business_id}/` (identical under `/api/v1/`).

| Backend domain | Mount today | Status | Authorization | Pagination | Error shape | Ref. part |
|---|---|---|---|---|---|---|
| Platform status | `/api/`, `/api/v1/` | LIVE\* | none (public) | – | – | A |
| Canonical domain API (Business Data, Operations, Identity) | `B` | LIVE\* | `BusinessMembership`: `VIEWER` reads; `OPERATOR+` writes; `MANAGER/OWNER` identity and review | `page`, `page_size` | `{code,detail}` + DRF field dicts | A |
| Contract seam (`bi`, `graph`, `ai`, `memory`, `configuration`, `monitoring`, `integrations`) | `B contracts/{owner}/{capability}/` | LIVE\*, **always UNAVAILABLE** | any role; write for `integrations` | – | `{code,detail}` | A |
| AI Intelligence | `B ai/…`, `actions/{pk}/{approve,reject,execute}/` | LIVE\* | membership of any role (calls); `OWNER/ADMIN/OPERATOR` (actions) | none (bare arrays) | `{detail}`, `{error}`, DRF dicts | B |
| Observability | **none**; original `B observability/` | UNMOUNTED | `BusinessAccess` `READER`/`MANAGER` | `page`, `page_size` | bare lists, `{query}`, DRF dicts | C |
| Overview & monitoring | **none**; original `B overview/` | UNMOUNTED | `BusinessAccess` | `page`, `page_size` | `{query}`, bare lists | C |
| Configuration | **none**; original `B configuration/` | UNMOUNTED | `BusinessAccess`; writes `MANAGER` | `page`, `page_size` | mixed (see §1.5) | D |
| Business Intelligence | **none, ever** | UNMOUNTED | `request.business` seam, never set → always 403 | `limit`, `offset` | `{error}` (generic) | E |
| Business Graph | **none, ever** | UNMOUNTED | `request.business` seam, never set → always 403 | none | `{error}` (specific) | E |
| Business memory & knowledge | – | BLOCKED | – | – | – | B |
| Prototype simulation | – (CLI only) | BLOCKED | – | – | – | D |

### 4.2 Verified request recipes

These are taken from the verified contracts, not invented. Replace ids with real ones. Every unsafe request also carries
`X-CSRFToken` (§1.4).

```http
# List with filters (orders: filters customer, status; control params page, page_size, q, since, until, ordering)
GET /api/businesses/42/orders/?status=CONFIRMED&ordering=newest&page=1&page_size=25&since=2026-11-01T00:00:00Z

# Move an order through its lifecycle (expected_status protects against a concurrent change -> 409 STALE_STATE)
POST /api/businesses/42/orders/7/transition/
{"status":"CONFIRMED","reason":"Payment verified","expected_status":"PENDING"}

# Assign a conversation (assignee_type: AGENT | TEAM | AI | UNASSIGNED)
POST /api/businesses/42/conversations/15/assign/
{"assignee_type":"AGENT","assignee_id":3,"reason":"Billing question"}

# Idempotent create-or-update: Idempotency-Key header is REQUIRED (1-180 chars), one UUID per user action
POST /api/businesses/42/refunds/
Idempotency-Key: ui-6f1c2b9e0d8a4c1f9e7b3a5d2c4e6f80
{"data":{"payment":12,"amount":"500.00","external_refund_id":"ui-6f1c2b9e0d8a4c1f9e7b3a5d2c4e6f80","reason":"Damaged item"}}
# 201 = created, 200 = replay/update. Money is sent as a string with at most 2 decimals.

# Prepare (never execute) an outbound operation: empty body; operation names use UNDERSCORES
POST /api/businesses/42/operations/shipment_submit/12/prepare/
{}

# Owner contract call: exactly request_id + payload. Today the answer is always the UNAVAILABLE envelope.
POST /api/businesses/42/contracts/bi/entity_context/
{"request_id":"customer-ctx-1","payload":{"entity_type":"CUSTOMER","entity_id":501}}
# -> {"version":"bizora.domain.v1","business_id":42,"owner":"Business Intelligence","capability":"entity_context",
#     "request_id":"customer-ctx-1","status":"UNAVAILABLE","result":null,"simulated":false,
#     "reason":"No owner adapter is configured."}
```

### 4.3 Rules the typed client must enforce

1. **Numbers.** Domain API returns decimals as JSON numbers **[LIB]**; BI, Overview and Configuration return **strings**. Parse
   both. Never `parseFloat` a money value for arithmetic; use a decimal library or integer minor units for display only.
2. **Timestamps.** DRF-rendered fields end in `Z`; service-built ones end in `+00:00`. Parse both as UTC instants and format
   in the business timezone. **Requests** must carry an offset (naive values inside `data` are rejected with `INVALID_TIME`).
   In a query string send `Z` or encode `+` as `%2B`, or the offset is lost.
3. **Foreign keys** are plain integers under the field name (`"customer": 5`), not nested objects. Detail routes expand
   `customer`/`order`/`conversation`/`product` once under the same key.
4. **Enums are case-normalised on write** (channel, priority, direction, etc. are trimmed, upper-cased, spaces→underscores).
   Always send upper-case. Customer tags posted via `tags/` keep their case but `?tag=` is upper-cased, so post upper-case.
5. **Filters are single exact values.** No ranges or multi-value filters except the documented `entity_types`/`relationship_types`
   (comma-separated) on the Graph API. Most list endpoints **reject unknown query keys with 400**, including `?format=` and
   cache-busters — never add stray parameters.
6. **`q` search is per-resource** and returns **400** for 18 resources (including `payments` and `calls`). The old Django UI
   showed a search box there and errored; the new UI must hide search where unsupported (list in reference Part A §2.1).
7. **Write-only fields:** `source_metadata`, `config`, `recording_url` never come back. Calls expose `recording_access`
   as UNAVAILABLE.
8. **A GET can write.** `BI-1 GET metrics/` syncs the metric registry. Treat it as a mutation for caching purposes.
9. **UNAVAILABLE is data.** Shape: `{"status":"UNAVAILABLE","owner":"<domain>","reason":"…"}`. It appears in the overview
   (`business_health`, `intelligence.*`), website performance (7 keys), support queue (`capabilities`), conversation
   context (`policy_context`, `suggested_reply`), retargeting (`audience_recommendation`), graph-context (`generation`),
   calls (`recording_access`), action review (`execution`), and every contract call. Render an empty state naming the owner.
10. **Simulated flag.** Contract results and mock transports carry `simulated: true`; show a `SimulatedBadge` and never
    present simulated output as real.

---

## 5. Backend prerequisites (to be done by the owning team)

These are **recommendations from verification, not changes made**. No backend code was modified. Suggested order is P0 → P2b
before any integration work; P3–P5 gate individual modules.

| ID | Prerequisite | Evidence / how to check | Unblocks |
|---|---|---|---|
| **P0** | Repair the merge `396593f`. Re-do it for the five damaged files (`app/models.py`, `app/urls.py`, `bizora/settings.py`, `app/admin.py`, `app/tests/test_status.py`): restore `import sys`/`copy`/`re`/`ValidationError`, the `admin` import, and the 14 dropped model classes (`BusinessMemory`, `HistoricalDecision`, `ApprovedSuggestion`, `SupportTeam`, `ProcessingReceipt`, `DomainAudit`, `ConversationEvent`, `IdentityHistory`, `CallbackRequest`, `AdAccount`, `CampaignAdSet`, `CampaignCreative`, `CampaignAd`, `ProductImage`) from `e487b0b`. Resolve the two competing `BusinessMembership` definitions (domain: roles `VIEWER…OWNER`; AI: default `MEMBER`) and merge the migration graph (three parallel lineages, two `CreateModel('BusinessMembership')`). | Done when `manage.py check`, `makemigrations --check --dry-run` and the test suite pass on Python 3.12. Last healthy `main` was `90e059e` (PR #4). | Everything |
| **P1** | Restore the three lost mounts in `app/urls.py` exactly as `fd41ea7` had them (`businesses/<int:business_id>/observability/`, `…/overview/`, `…/configuration/`). Decide and add mounts for Business Intelligence and Business Graph. Overview hard-codes `/api/businesses/<id>/overview/…` in its links, so it must keep that prefix. | `GET` on each prefix no longer 404s. | M1, M13, M14, M17, M18 |
| **P2** | Add the session endpoints a SPA needs: JSON login/logout, CSRF bootstrap, `me` (user, active businesses, role per business). Keep the app same-origin, or add CORS + `CSRF_TRUSTED_ORIGINS` + cookie settings. Add agent and team list endpoints for assignment pickers. | Sign-in works without the Django form; role-aware UI no longer guesses. | M0, M8 |
| **P2b** | Decide one authorization model. `BusinessMembership` and `BusinessAccess` currently disagree, and BI/Graph use a third seam (`request.business`) that nothing sets and that bypasses `IsAuthenticated`. | A user sees consistent access across all modules. | M1, M13, M14, M17, M18 |
| **P3** | Fix `app/business_graph/projection.py` annotation on Python 3.12 (`models.Model`). | `import app.business_graph.urls` succeeds on 3.12. | M14 |
| **P3b** | Align relationship keys: BI writes `bi.relationship.<name>.v1`, Graph accepts `<name>`. Add a test that runs BI `rebuild_relationships` then the graph rebuild and asserts edges exist. | Graph rebuild after a BI run yields edges. | M14 |
| **P4** | Provide something that actually runs the BI calculators (a scheduled job, management command, or endpoint) and make `pipeline/run/` truthful (it currently reports `"COMPLETED"` even when the whole rebuild rolled back, with `quarantined_records: 1`). | KPI/trend/BI endpoints return real snapshots. | M1, M13 |
| **P5** | Create AI recommendations/actions from a route or job; mark LLM fallback in the response; add conversation-history and audit read routes. | AI feeds are non-empty and honest about fallback. | M15 |
| **P6** | Missing read surfaces the specs describe: business memory & knowledge (all 19 features), relationship browsing, fact/issue evidence rows, graph node/edge lookup, simulation. | Per-module. | M19, M20, parts of M13/M14 |
| **P7** | Generate an OpenAPI schema (none exists). | Typed client can be generated instead of hand-written. | All |
| **P8** | Turn the inferred `500`s into `400`s (non-numeric `value`/`confidence`, bare `int()` on query params, naive datetimes, a missing `issue_type`, and `POST` to a detail URL / `PATCH` to a collection URL on Configuration). Unify the five error shapes. | The client needs one error path. | Hardening |

---

## 6. Live progress tracker

Updated by the orchestrator at the end of each session. ☐ not started · ◐ in progress · ☑ done.

### 6.1 Programme

- ☑ Preflight, kit installed and bound to the Django stack (2026-11-09)
- ☑ Documentation read (domain list, 12 specs, handoff, contracts)
- ☑ Backend verified by five code scans and independent reproduction (commit `5f176a2`)
- ☑ Design tokens computed and AA-checked (31 contrast pairs per theme, 0 failures); chart colours colour-blind-checked
- ☑ Palette changed to neutral slate + one cobalt primary (2026-11-09, D-F13) after the first indigo/teal draft failed review
- ☑ `frontend.md` drafted · ☑ `frontend-api-reference.md` assembled · ☑ Stitch prompt pack written for **9 workspace pages** plus the design-system screen (F0), with two recommended extra screens; every feature in the 12 specifications is mapped to a page and tab
- ☐ **Owner review of these three documents** ← current gate
- ☐ Team fixes P0 → P2b (backend)
- ☐ Designs generated in Stitch and reviewed
- ☐ Frontend scaffold created and gates wired
- ☐ Modules built and integrated (table below)

### 6.2 Foundation

| Task | Status |
|---|---|
| F1 Scaffold `frontend/` (Vite + React + TypeScript strict), commit lockfile | ☐ |
| F2 Generate `tokens.css` and Tailwind config from §2 | ☐ |
| F3 API client: fetch wrapper, CSRF, Idempotency-Key, `ApiError`, pagination adapter, Zod schemas | ☐ |
| F4 App shell, router, business/role guards, theme | ☐ |
| F5 Design-system primitives and `UnavailableState`, `EvidencePanel`, `SimulatedBadge` | ☐ |
| F6 Test harness: Vitest, MSW handlers generated from the reference, Playwright | ☐ |

### 6.3 Modules

| Module | Backend readiness | Spec'd | Designed | Built | Integrated | Verified |
|---|---|:-:|:-:|:-:|:-:|:-:|
| M0 Shell & session | PARTIAL | ☑ | ☐ | ☐ | ☐ | ☐ |
| M1 Overview & monitoring | LIVE\* + UNMOUNTED | ☑ | ☐ | ☐ | ☐ | ☐ |
| M2 Customers & 360 | LIVE\* | ☑ | ☐ | ☐ | ☐ | ☐ |
| M3 Products | LIVE\* | ☑ | ☐ | ☐ | ☐ | ☐ |
| M4 Orders | LIVE\* | ☑ | ☐ | ☐ | ☐ | ☐ |
| M5 Payments & refunds | LIVE\* | ☑ | ☐ | ☐ | ☐ | ☐ |
| M6 Unified inbox | LIVE\* | ☑ | ☐ | ☐ | ☐ | ☐ |
| M7 Support queue | LIVE\* | ☑ | ☐ | ☐ | ☐ | ☐ |
| M8 Assignment & handover | PARTIAL | ☑ | ☐ | ☐ | ☐ | ☐ |
| M9 Marketing | LIVE\* (BI parts BLOCKED) | ☑ | ☐ | ☐ | ☐ | ☐ |
| M10 Website performance | LIVE\* (analysis UNAVAILABLE) | ☑ | ☐ | ☐ | ☐ | ☐ |
| M11 Delivery | LIVE\* (analysis BLOCKED) | ☑ | ☐ | ☐ | ☐ | ☐ |
| M12 Calls | LIVE\* | ☑ | ☐ | ☐ | ☐ | ☐ |
| M13 Business Intelligence | UNMOUNTED | ☑ | ☐ | ☐ | ☐ | ☐ |
| M14 Graph | UNMOUNTED | ☑ | ☐ | ☐ | ☐ | ☐ |
| M15 AI Intelligence | LIVE\* (thin) | ☑ | ☐ | ☐ | ☐ | ☐ |
| M16 Identity & resolution | LIVE\* | ☑ | ☐ | ☐ | ☐ | ☐ |
| M17 Integrations & observability | UNMOUNTED | ☑ | ☐ | ☐ | ☐ | ☐ |
| M18 Configuration | UNMOUNTED | ☑ | ☐ | ☐ | ☐ | ☐ |
| M19 Memory & knowledge | BLOCKED | ☑ | ☐ | – | – | – |
| M20 Prototype simulation | BLOCKED | ☑ | ☐ | – | – | – |

**Suggested build order once P0–P2b land:** F1–F6 → M0 → M2/M4/M5 (canonical data, highest confidence) → M6/M7/M8 (support) →
M3/M11/M12 → M16 → M15 → M1 → M17/M18 → M13/M14 (after P3–P4).

---

## 7. Decisions, assumptions and open questions

### 7.1 Decisions taken (door type in brackets)

| ID | Decision | Reason | Door |
|---|---|---|---|
| D-F01 | ~~Vite + React + TypeScript SPA, not Next.js~~ (retired by D-F20: adopt the teammate's Next.js 16 app) | Cookie-session auth forces same-origin; an authenticated app needs no SSR; avoids a second server in the auth path | two-way |
| D-F02 | **Same-origin** deployment behind a reverse proxy | No CORS/CSRF-trusted-origin support exists in the backend | two-way until P2 |
| D-F03 | Frontend lives in `frontend/` at the repository root | Keeps one repo and one proxy; confirm with the owner | two-way |
| D-F04 | **Hand-written typed client with Zod** runtime validation | No OpenAPI schema exists; responses use five error shapes and four pagination styles | two-way |
| D-F05 | Business id in the **URL** (`/b/:businessId`), role in context | Backend scopes by URL id; no "me" endpoint | two-way |
| D-F06 | **Never show `UNAVAILABLE` as zero or as an error** | Backend contract; matches the "missing data is never zero" rule | one-way (semantics) |
| D-F07 | Labels say **"recorded"**, never "sent" | Nothing is transmitted to any provider | one-way (honesty) |
| D-F08 | Money shown as **ISO code + amount**, never summed across currencies | Backend isolates amounts per currency | one-way (finance) |
| D-F09 | Colour tokens are fixed in §2; **AA contrast verified by computation** | Accessibility floor in the kit's design law | two-way |
| D-F10 | Graph defaults chosen by the client (`max_depth` 2, `max_nodes` 200) | Backend enforces no caps | two-way |
| D-F11 | Poll only on operational screens; no push | No websocket/SSE exists | two-way |
| D-F12 | Handle `403` bodies by shape (auth vs CSRF vs role) | DRF returns 403, not 401, for anonymous | two-way |
| D-F13 | **Neutral palette**: cool-slate neutrals, one cobalt primary `#1D4ED8`, no second accent. Replaces the indigo + teal draft | Owner asked for a neutral, formal look; indigo is the commonest AI-design default; the old chart colours failed the colour-blind check (4 of 5 checks, both themes) | two-way |
| D-F14 | **Motion and cards budget**: state-change motion only (120 ms hover, 200 ms panels); no scroll animation, parallax or GSAP-style timelines; prefer sections, tables and dividers to cards | Owner: formal, no heavy animation; Refero guidance that cards-everywhere is a generic-design marker | two-way |
| D-F16 | Stitch prompts target **80–90% accuracy and stay generic**; exact fields and rules live in this file and the API reference and are applied at build time | Owner: prompts only visualise features now and will be changed when the real frontend is built | two-way |
| D-F17 | Defaults taken without a reply: pages for blocked modules (Memory and knowledge, Simulation) stay as **design-only**; UI language **English only** for v1 | Owner expects a page per module; Bangla can be added later (fonts already cover it) | two-way |
| D-F18 | **Nine workspace pages with tabs, drawers and dialogs**, not one page per backend module. A page is a job a person does (Overview, Customers, Commerce, Support, Growth, Intelligence, AI, Admin, plus sign-in). The earlier 53-page plan is withdrawn | Owner: 53 pages would never be finished; a hackathon demo needs about 10; modules can share a page | two-way |
| D-F20 | **Adopt the teammate's Next.js 16 (JavaScript) app** in `frontend/`; keep its same-origin proxy, session and CSRF design; no TypeScript migration, no CSS framework | The owner wants to improve it, not replace it; an overnight rewrite is riskier than a restyle | two-way |
| D-F15 | Stitch work is **page by page**: one design-system screen (F0), then one prompt per page, light theme first, dark as a later toggle | One long prompt produced one page; 15 screens in one paste is not how the tool is used (third-party guidance, official guide unread) | two-way |

### 7.2 Assumptions (to confirm)

- The deployed Python is 3.12 (`Dockerfile`, `AGENTS.md`); the Graph import issue is judged against that.
- "Stitch" is Google Stitch; the prompt is written as plain descriptive text, which any text-to-UI tool accepts.
- Latest npm versions in §1.2 are compatible with each other; this has **not** been tested.
- English first; the type stack includes Bengali glyph coverage because customer content and the business locale setting may be Bangla.

### 7.3 Open questions for the owner

1. **Who fixes P0–P2b, and when?** The frontend cannot integrate before then.
2. **Sign-in:** accept a redirect to the Django form for now, or have the team add JSON session endpoints?
3. **Which authorization table is canonical** — `BusinessMembership` or `BusinessAccess` (or a bridge)?
4. **Where does the frontend live** — `frontend/` in this repo, or a separate repository?
5. ~~Designs for BLOCKED modules?~~ Kept as design-only sections (Knowledge, Simulation) inside P9 Admin (D-F17, D-F18). Say if you want them dropped.
6. ~~Language scope~~ English only for v1 by default (D-F17). Say if Bangla strings are needed sooner.

---

## 8. Change log

| Date | Change |
|---|---|
| 2026-11-09 | Initial draft: analysis, architecture, verified design system, module breakdown, API matrix, prerequisites, tracker. Backend verified at `5f176a2`. |
| 2026-11-09 | **Page plan reduced to 9 workspace pages** (D-F18): the 53-page pack is withdrawn; sub-views become tabs, drawers and dialogs; Stitch pack and batch prompts regenerated (`build_pack9.py`); §3.0 added. |
| 2026-11-09 | (superseded by the row above) Prompt pack extended to 53 pages after a feature-by-feature coverage check against the 12 specifications (16 pages added: overview drill-downs, BI analysis, attribution, anomalies, relationships, graph snapshots and query, AI audit, identity conflicts, integrations catalogue, rules and policies, memory ingestion and search, simulation builder and validation); each page now has a short generic prompt plus an optional detail follow-up; prompting guide added (D-F16, D-F17). |
| 2026-11-09 | Palette replaced with neutral slate + cobalt (D-F13); chart colours switched to the colour-blind-validated order; motion and cards rules added (D-F14); Stitch prompt rewritten as a page-by-page pack (D-F15). |
