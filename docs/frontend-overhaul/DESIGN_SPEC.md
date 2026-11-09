# Design spec: what to build

Status: 2026-11-09. This is the build target for the overhaul. Background and reasons: `docs/frontend.md` section 2 (design system) and section 3 (modules), contracts: `docs/frontend-api-reference.md`
(endpoint ids such as D8, E12, BG-1 are defined there). Where this file and an older doc disagree, this file wins.

## 1. Principles
Formal, calm, high-contrast, neutral. Cool slate neutrals, **one** cobalt primary, status colours only for status, tokens only (`docs/frontend-overhaul/assets/tokens.css`), no gradients, no illustrations, minimal motion.
Data is the hero: real columns, formatted values, monospaced numerals. Every page has loading, empty, error, "Not connected" and role-disabled states. Honesty wording is fixed (see `.agents/rules/00-project-law.md`).

## 2. Foundations (Phase 1 builds these)
- **Tokens:** copy `assets/tokens.css` to `frontend/src/styles/tokens.css`, import it first in `layout.js`. Split the old `globals.css` into `base.css` (reset, typography, focus, forms), `layout.css` (shell, grid) and `components.css`
  (or one file per component family); nothing outside `tokens.css` may contain a raw colour. Theme: `data-theme="light|dark"` on `<html>`, default follows the system, a toggle in the top bar remembers the choice (a cookie or localStorage holding only the word light or dark).
- **Fonts (`next/font/google`, self-hosted):** Plus Jakarta Sans 600 and 700 (`--font-jakarta`), Inter 400, 500, 600 (`--font-inter`), JetBrains Mono 400 and 500 (`--font-jetbrains`), Noto Sans Bengali 400 and 600, subset `bengali` (`--font-bengali`).
  Attach the variables to `<html>`. Weights are only those listed.
- **Formatters (`src/lib/format/`):** `money(amount, currency)` gives `BDT 2,500.00` (never a bare symbol, never summed across currencies); `dateTime(iso, timezone)` gives `09 Nov 2026, 14:32`; `date`, `relativeTime`, `duration(seconds)` gives `2d 4h`;
  `percent(fraction)` gives `17.0%`; `enumLabel(value)` gives sentence case; `missing()` gives `—`. All accept null and `UNAVAILABLE`. The business currency and time zone come from the session (`/api/frontend/session` lists them per business).
- **API layer (`src/lib/api/`):** `ApiError {status, code, detail, fields}`; one `request()` for client and server; error normaliser for the five backend shapes (see `docs/frontend-api-reference.md` Part A section 1d and `docs/backend-issues/platform.md` PL-05);
  `409` becomes a "changed, reloaded" flow; `403` shows the role hint; session expiry redirects to `/login?next=<same-site relative path>`; a pagination adapter (page and page_size, same-origin `next` and `previous` links); `newIdempotencyKey()` held in form state and reused on retry.
- **Shared UI (`src/components/ui/`):** Button (primary, secondary, ghost, danger; sm, md; loading), IconButton, Input, Select, Textarea, Checkbox, FormField (label above, hint, error), StatusChip (icon and label, exact-value map), SeverityChip, ConfidenceMeter, Tabs (path-segment links, `aria-current="page"`),
  Drawer (right side, `role="dialog"`, focus trap, Escape, scrim), Dialog and ConfirmDialog, Toast, Skeleton, EmptyState, UnavailableState ("Not connected": dashed border, info icon, owner, reason), SimulatedBadge, KpiTile, DataTable (typed columns, sticky header,
  right-aligned numerics, density, pagination footer, row click opens a drawer), Timeline (the evidence thread: thin line, small nodes), EvidencePanel, CopyableCode, Banner (info, success, warning, danger with icons), PageHeader (title, description, actions, breadcrumbs), ThemeToggle.
- **Shell:** rail 256 px (collapsible to 72 px, drawer below 1024 px), sticky top bar 56 px (business switcher, global search, data freshness text, theme toggle, user menu with sign out). The rail uses the nav tokens; its focus ring is `--color-focus-on-nav`; the active item has the 3 px indicator and `aria-current="page"`.
- **Boundaries:** `loading.js`, `error.js` and `not-found.js` at app, business and workspace level (read the Next.js docs for this version first). Route metadata titles.

## 3. Navigation and routes
Keep the teammate's `/business/[businessId]/...` prefix. Rail groups and items (items the role cannot use are hidden; the server still enforces):
**Overview** · Overview. **Operations** · Support, Customers, Commerce, Growth. **Intelligence** · Intelligence, AI. **Administration** (managers) · Identity, Integrations, Configuration, Knowledge (design-only), Simulation (design-only).

| Page | Route (tabs are path segments; the first tab is the default and the bare route redirects to it) | Tabs |
|---|---|---|
| P1 Sign-in | `/login`, `/workspace` (business choice) | |
| P2 Overview | `/business/[id]/overview/[tab]` | `overview` (default), `trends`, `health` |
| P3 Customers | `/business/[id]/customers` (list) and `/business/[id]/customers/[customerId]/[tab]` | `timeline` (default), `orders`, `conversations`, `deliveries`, `website`, `graph`, `identity` |
| P4 Commerce | `/business/[id]/commerce/[tab]` | `orders` (default), `payments`, `deliveries`, `products` |
| P5 Support | `/business/[id]/support/[tab]` | `inbox` (default), `queue`, `calls` |
| P6 Growth | `/business/[id]/growth/[tab]` | `campaigns` (default), `website` |
| P7 Intelligence | `/business/[id]/intelligence/[tab]` | `facts` (default), `graph`, `metrics`, `pipeline` |
| P8 AI | `/business/[id]/ai/[tab]` | `assistant` (default), `actions`, `audit` |
| P9 Admin | `/business/[id]/admin/[section]` | `identity` (default), `integrations`, `configuration`, `knowledge`, `simulation` |

Filters, search and paging stay in the query string (`?status=`, `?page=`). A row's detail drawer opens with `?open=<resource>:<id>` so it survives refresh and can be linked. Use a shared layout per workspace (`layout.js`) that renders the page header and the tab bar, so switching tabs keeps the shell.

Record detail pages stay at `/business/[id]/records/[resource]/[recordId]` (deep links, linked from tables) but get the new look and real titles. Every old section route (`/business/[id]/inbox`, `/queue`, `/orders`, `/insights` and so on) redirects to its new home
with the right tab, so bookmarks and the existing Playwright specs keep working until those specs are updated in the same commit.

## 4. Page specs
Common to all: `PageHeader`, tabs as path segments, a table or list whose columns carry meaning (name, amount, date, status), a drawer for row detail, `UnavailableState` where data is not connected, skeletons, empty states with one action, honest wording.

**P1 Sign-in.** Centred panel, wordmark, username, password, **Sign in**; in development also **Continue as demo owner** (already built; keep and restyle). Error banner for 401 ("Invalid username or password."). `/workspace`: list of the user's businesses (name, currency and time zone,
role chip) with an Open button; one business opens directly. Honour `?next=`.

**P2 Overview.** Header (business, "BDT · Asia/Dhaka", period selector Day, Week, Month, Rolling 7, Rolling 30, compare toggle). **Real tiles from `GET overview/` (D8) canonical counts:** customers, orders, payments, open conversations, shipments, calls, campaigns.
KPI tiles (gross revenue, net revenue, orders, average order value, delivery success, cart abandonment) come from the overview module `kpis/`; today they are UNAVAILABLE, so show `UnavailableState` tiles with the reason; never zero. Recent activity feed from D8 (`recent_activity`),
with domain filter chips. Health and issues from `health/` and `issues/` (UNAVAILABLE until Business Intelligence runs). Trends tab: chart or `UnavailableState`. Health tab: per-domain rows. Endpoints: D8, overview module (`summary`, `kpis`, `trends`, `health`, `issues`, `activity`, `recommendations`, `cross-domain`).
Charts: hand-built SVG or a tiny helper (no chart library unless justified in PROGRESS.md); direct labels; a data-table alternative.

**P3 Customers.** List: search, filters (status, tag, contact), columns name (display name or first and last name), status, primary contact, tags, order count, last activity. Row opens the 360 view (master-detail on wide screens). 360: profile header, linked identities with confidence (`—` when manual),
tabs as in the table above using D9 `customers/{pk}/360/` sections and the child list endpoints. Timeline tab merges orders, payments, shipments, messages and calls on one vertical line. "AI customer context" block: `UnavailableState`. Open issues block from E12. Graph tab: the one-hop context from D22 `graph-context/customer/{pk}/`.
Status change as a dialog (D4, legal transitions only).

**P4 Commerce.** Orders tab: filters (status, customer, date range, order number), table (order number, customer, status chip, total, ordered at), row opens a drawer: items, payments, refunds, shipment tracking, status history, customer link, status control offering only legal next states
(Pending to Confirmed or Cancelled; Confirmed to Processing or Cancelled; Processing to Shipped or Cancelled; Shipped to Delivered or Returned; Delivered to Returned or Refunded; Returned to Refunded) with `expected_status`, `409` handling and a reason field. Payments and refunds tab: filters (method, status; no text search, `q` returns 400),
detail with refund ledger, Refund dialog (amount of at least 0.01, reason, reused idempotency key), switch to the financial timeline (D6; rows keyed by entity kind and id). Deliveries tab: shipments with status chips, failed deliveries filter, detail with tracking timeline and "Prepare submission / cancellation" panels worded "Prepared — not executed" (D21).
Products tab: catalogue, drawer with variants, images, add variant, map to an external reference (manager), assess before create (D25), variant price and stock (D5).

**P5 Support.** Inbox tab: three panes (conversation list with channel icon, priority, unread, assignee; thread with bubbles, attachments, delivery state, internal notes in a tinted block, the AI suggested reply block as `UnavailableState` or the E2 helper; context panel D18). The reply composer is labelled
**"Saved — not sent"**. Toolbar: Assign (dialog, D11), Hand over to human or return to AI (dialog with reason and summary, D12; "The customer is not notified automatically."), Priority (D17). Queue tab (D10): urgent first, filters, three capability tiles as `UnavailableState`.
Calls tab: list (no search; `q` returns 400), drawer with event timeline, transcript, summary, "Recording" as `UnavailableState`, Schedule callback dialog (future times only, D23), Prepare outbound call (D21).

**P6 Growth.** Campaigns tab: table (platform, status, spend, clicks, conversions headed "Platform-reported"), drawer with daily metrics (two small charts, never one chart with two axes), conversions, ad sets, ads, creatives, the "Explain this campaign" helper (E6), and an "Attributed revenue" tile as `UnavailableState`
(filters: status and search only; `platform` is allowed, `provider` is not). Website tab: visitors, sessions, events tables; visitor journey in a drawer (D19, oldest first); the seven analysis panels from D7 as `UnavailableState` naming Business Intelligence.

**P7 Intelligence.** Facts and issues tab: real open issues from E12 (empty in the demo: show the empty state, not an error); facts and metrics come from Business Intelligence which is not mounted: `UnavailableState` with the owner and reason; the Evidence drawer (the evidence thread) is built and ready, driven by fixtures only in tests.
Graph tab: a one-hop **context graph** from D22 for a chosen customer, order or product (real data), with a node and edge legend (shape and icon per type, not colour alone), direction and depth are fixed at one hop, and a clearly separate "Full graph traversal, paths, journeys, snapshots" `UnavailableState`. Metrics and analysis tab: metric catalogue and analysis sections as `UnavailableState`.
Pipeline tab: `UnavailableState`. Business Intelligence and Graph endpoints (BI-1 to BI-11, BG-1 to BG-11) are unmounted today (see `docs/backend-issues/business-intelligence.md` and `business-graph.md`); build the screens so they switch on when the endpoints appear (adapter functions that return `UNAVAILABLE` for now).
**Optional demo mode (last phase, off by default):** a visible switch "Sample data (SIMULATED)" that feeds clearly badged sample facts, issues and a sample graph so the demo story can be shown; every sample number carries the SimulatedBadge and the page header says so. Never mixed with real rows.

**P8 AI.** Assistant tab: question box and answer (E1), "Grounded in" facts and open issues, banner that answers are advisory and come from recorded evidence, progress state (calls can take about 15 s), no claim of AI if the backend reports fallback (the backend cannot say yet: AI-02, so word the banner carefully).
Recommendations and actions tab: recommendations (E10; empty until generated), actions (E11) with status chips (Suggested, Approved, Rejected, Executing, Executed, Failed), the review flow with a 3 to 1000 character note (E16 `review`), banner **"Execution is simulated."** Never call execute from the UI. Audit tab: `UnavailableState` (no read route, AI-07).

**P9 Admin (managers).** Identity: tabs Canonical, External, Links, Conflicts, Merge candidates, History; commands in dialogs with id lookups where possible; the merge dry-run plan card; **Execute merge** permanently disabled with "Blocked by design." Integrations: summary band, connections with Test, syncs with retry (confirm dialogs), failed records grouped with Retry, webhooks with Replay, freshness chips,
providers, errors; results worded "Attempt recorded — Succeeded", "Attempt recorded — Failed", "Unsupported". Configuration: sections (profile, general, AI, knowledge, rules, policies, connections, sources, reprocessing, monitoring, freshness, effective, changes), forms with version chip and `409` banner "Someone else changed this. Reload to continue.",
credentials shown only as references and "Configured", send diffs only (PUT deep-merges; do not echo GET objects back). Knowledge and Simulation: layout only, whole section `UnavailableState`.

## 5. Quality bar for "done"
Looks like one product (same header, tabs, drawers, tables, chips everywhere) · every page works at 1440, 1024 and 390 px in light and dark · keyboard path complete · zero console errors · no raw JSON, raw ISO dates or "Record #id" titles · honest wording everywhere · tests and build green · screenshots reviewed by `/design-review`.
