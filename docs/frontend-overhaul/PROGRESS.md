# Progress log (the agent updates this after every task)

Branch: `frontend-overhaul` · Started: 2026-11-09 23:11 (Asia/Dhaka) · Status key: todo, doing, done, blocked, skipped. Add the commit hash and how you verified each task.

## Tasks
| Task | Status | Commit | What changed and how it was verified |
|---|---|---|---|
| T0-1 Preflight | done | 14a21ce | Dev servers verified running with dev-status.sh, demo sign-in endpoint enabled and tested on /login. |
| T0-2 Baseline | done | 14a21ce | Gates verified (18/18 tests pass, format:check clean, build passes). Baseline report in ~/bizora-shots/baseline noted (288 issues). |
| T0-3 Remove hard-coded password | done | 14a21ce | Replaced hard-coded password in scripts/take_browser_tour.js with BIZORA_E2E_* env vars. git grep DemoPass returns empty. |
| T1-1 Tokens | done | 4b94009 | Copied tokens.css to src/styles/tokens.css, split globals.css into base.css, layout.css, components.css. Raw colour grep clean. verify-pages login+overview clean (0 issues, shot in ~/bizora-shots/t1-1-tokens). |
| T1-2 Fonts and type scale | done | cd67d98 | Configured next/font/google in layout.js for Plus Jakarta Sans, Inter, JetBrains Mono, Noto Sans Bengali. Verified Inter computed font on body, 0 issues on verify-pages. |
| T1-3 Themes | done | 911b382 | Added ThemeToggle with lucide Sun/Moon, inline head script to avoid flash, data-theme styling and color-scheme. Verified across 8 checks (1440 & 390, light & dark) with 0 issues in ~/bizora-shots/t1-3-themes. |
| T1-4 Native controls and states | done | 571396a | Styled input, select, option, textarea, checkbox, radio, date inputs, focus ring (2px/2px offset with nav token on rail), table hover, smooth-scroll reduced-motion guard. Verified 8 checks with 0 issues in ~/bizora-shots/t1-4-controls. |
| T1-5 Foundation review | done | 84f3608 | Ran all four reviewers (design-reviewer: SHIP, architect-reviewer: APPROVE, code-reviewer: SHIP, security-reviewer: SHIP). Fixed F-01 (theme-toggle inline styles -> tokens in components.css) and F-02 (localStorage try/catch guard). npm test 18/18, format:check clean, build passed. |
| T1-6 Formal theme: palette and typography | done | cb1d04b | Installed tokens.formal.css, next/font/google with IBM Plex Sans (400, 500, 600), IBM Plex Mono (400, 500), and Noto Sans Bengali. Removed negative letter-spacing, capped heading weights to 600, replaced monospace on money/dates with tabular-nums. Neutral secondary buttons, 10px 16px table padding. devIndicators: false. Fixed CR-01 to CR-05. verify-pages 44/44 checks clean (0 issues, computed font IBM Plex Sans). Design review SHIP (9.5/10). 43/43 tests green, build 3.5s. |
| T2-1 Formatters | done | 5b7dcea | Created src/lib/format/ (money, dateTime, date, duration, percent, enumLabel, stripUntrusted, statusTone, statusText) with format.js shim. Fixed INACTIVE -> neutral tone. Added 8 new unit tests (26/26 tests green). |
| T2-2 API client | done | b955442 | Created src/lib/api/ (ApiError, normalizeError parsing 7 backend shapes, clientApi with timeout/CSRF retry/403 session expiry redirect, serverApi with cached getSession). Added 4 unit tests (30/30 tests green). |
| T2-3 Safe writes | done | e83b7a2 | Created idempotency.js (v4 UUID fallback for non-secure origins, makeExternalId) and useActionForm hook (busy, ApiError, key reuse across retries, rotation on payload change, 409 reload flow). Added 4 unit tests (34/34 tests green). |
| T2-4 Resource config | done | fb049eb | Created src/lib/domain/resources.js with config for all 32 resources (columns, titles, tabs, workspaces, 14 searchable split, filterQueryParams allow-list). Fixed all 4 reviewer findings (isSafeRelativePath open-redirect hardening, stripUntrusted regex, getSession 503 fallback, 403 login-loop guard, recordTitle domain keys, future relativeTime, HTML error detection, useActionForm idempotency state). 39/39 tests pass, format:check clean, build green, 8 page checks 0 issues. |
| T3-1 Form basics | done | b894088 | Added Button (primary, secondary, ghost, danger, sizes sm/md, loading spinner, disabled), IconButton (accessible name enforced, title/tooltip), Field (accessible label, hint, role=alert error), Input (prefix/suffix groups), Select (chevron, options), Textarea, Checkbox, MoneyField (currency prefix, 2 decimals restriction), DateTimeField (timezone badge). 39/39 tests pass, format:check clean, build green. |
| T3-2 Feedback and status | done | 5a705a8 | Added Banner (info, success, warning, danger, dismissible), StatusChip (exact code mapping, icon + label required), SeverityChip, ConfidenceMeter (accessible meter), Skeleton (calm opacity pulse, zero gradient), EmptyState, UnavailableState ('Not connected' calm layout, owner, reason), SimulatedBadge, KpiTile (tabular numbers, trend, unavailable state), ToastProvider & useToast (ephemeral notifications, aria-live). 39/39 tests pass, format:check clean, build green. |
| T3-3 Overlays and navigation | done | fc2293d | Added Tabs (path-segment Link and role=tablist modes, active indicator, counts), Drawer (right-sliding, focus trap, Escape, scrim, body scroll lock), Dialog & ConfirmDialog (modal dialogs, danger variant, loading state), Pagination (range '1–25 of 1,284', accessible navigation), FilterBar (search, filter slots, removable pills, clear all), PageHeader (breadcrumbs, h1, actions, badge). 39/39 tests pass, format:check clean, build green. |
| T3-4 DataTable | done | fccf2ef | Created src/components/ui/DataTable.js with typed columns (text, money, datetime, status, severity, entity, mono, untrusted), sticky header, right-aligned mono numerics, density toggle (compact/default), skeleton rows, empty state, error banner with retry, pagination footer, and row click drawer (?open=res:id). Refactored components/DataTable.js to proxy to UiDataTable and upgraded StatusBadge to StatusChip (icon + label). 39/39 tests pass, format:check clean, build green. |
| T3-5 Evidence and time | done | ede18f7 | Added Timeline (thin guide line, small nodes, status chips, metadata), EvidencePanel (grounding facts, confidence meter, authoritative source bar, safe plain-text stripping), CopyableCode (inline/block modes with clipboard API and feedback). 39/39 tests pass, format:check clean, build green. |
| T3-6 Gallery | done | ae31e98 | Created /business/[businessId]/ui-kit developer gallery with interactive controls (theme switch, density toggle, modal triggers, toast triggers, drawer test, and full typed DataTable showcase). Verified across 12 page checks at 1440x900 and 390x844 light/dark with 0 issues. |
| T3-7 Chart components | done | 037c00c | Installed approved recharts@3.10.1 (0 audit vulnerabilities); created token-driven chart wrappers in src/components/ui/charts/ (ChartCard with accessible table toggle and calm empty/unavailable states, TrendLine area/line with responsive tick reduction on phones, BarCompare categorical comparison with rounded tops, Sparkline inline tile chart); zero hard-coded hex colors (uses --chart-1 through --chart-8); re-exported via src/components/ui; added chart gallery section to /ui-kit. Gates: npm test 47/47 passed, format:check clean, build 8.6s, matrix 14/14 checks clean (0 issues across all 7 sizes in light and dark). |
| T4-1 Shared layout and shell | done | 27df4a5 | Overhauled AppShell with collapsible 256px rail (72px collapsed with localStorage preference and bottom toggle), 6 enterprise nav groups (Overview, Operations, Intelligence, Data & identity, Integrations, Settings), active route matching for 9 workspaces and legacy routes, mobile drawer with focus trap, Esc dismiss, and scroll lock, sticky 56px topbar with business switcher, role chip, global search Ctrl+K trigger and QuickSearchDialog, context indicator, theme toggle, and user sign-out menu. Verified across 12 page checks (0 issues, verify-pages clean). |
| T4-2 Boundaries and metadata | done | b694377 | Added root global-error.js (html/body compliant, safe fatal boundary), root not-found.js (clear 404 message, illustration-free enterprise design, return to workspaces/login), business-level error.js (inline Banner variant=danger with server detail, retry button, links to Overview and workspace), business-level loading.js (skeleton shaped like final page with header, KPIs, filter bar, and table rows; zero white flash), business-level not-found.js, and route metadata template in root layout.js (%s · Bizora). Verified 404 response on /does-not-exist and gates clean. |
| T4-3 Route skeleton and redirects | done | ac1a5f4 | Created nine-workspace route skeleton (P2 Overview, P3 Customers, P4 Commerce, P5 Support, P6 Growth, P7 Intelligence, P8 AI, P9 Admin) with optional catch-all [[...tab]] segments, tab metadata, and backward-compatible redirects from legacy /records/[resource]/[id] (to tab + ?open=res:id), /resources/[resource] (to tab), and /[section] (to target workspace). 43/43 tests pass, build 5.3s, verify-pages 40/40 checks clean (0 issues). |
| T4-4 Sidebar redesign | done | 53610b8 | Redesigned sidebar rail per UX_POLISH_SPEC.md §2: 264px rail / 72px collapsed rail, 56px brand block aligned with topbar, 32px mark (--color-nav-indicator bg), informational workspace card with Radix Tooltip and circular initial when collapsed, group headers (11px uppercase / 1px divider in collapsed), 40px nav items with 3px left indicator bar, count pills, Radix Tooltip on collapsed rail, independent scrolling nav area, pinned footer with collapse toggle and user card opening Radix DropdownMenu (theme switcher + sign out), neutral dev badge, off-canvas mobile drawer (<1024px) with focus trap, inert background, and scrim. Hoisted AppShell to business/[businessId]/layout.js (ARCH-01), removed redundant AppShell wrappers across 9 workspace pages, installed approved Radix packages (@radix-ui/react-tooltip, @radix-ui/react-dropdown-menu, @radix-ui/react-popover) and clsx. Gates: npm test 43/43, format:check clean, build 1.4s, verify-pages 44/44 clean (0 issues, IBM Plex Sans, light/dark, 1440 & 390). |
| T4-5 Responsive foundation and layout primitives | done | e85fde2 | Added layout primitives in layout.css (.grid-kpi, .grid-2, .grid-main-aside, .stack, .stack-sm, .stack-lg, .section-gap, .card-padding) per UX_POLISH_SPEC.md §3; implemented mobile responsive patterns per §4 (modals to bottom sheets <=640px with 90dvh cap and stacked buttons, drawers 100vw, toast full-width, touch targets >=40px, form inputs min 44px height and 16px font to prevent iOS zoom); added table-col-priority-low for responsive table hiding and tabs scroll-snap; enhanced verify-pages.mjs with --matrix (7 viewports: 360x740, 390x844, 768x1024, 1024x768, 1280x800, 1440x900, 1920x1080), touch target validation, min font validation, and overflow detection. Gates: npm test 43/43, format:check clean, build 1.0s, matrix 42/42 checks clean (0 issues across all 7 viewports light/dark). |
| T5-P1 Sign-in and business choice | done | f7d1bfa | Overhauled /login (Suspense boundary, safe ?next= redirect via isSafeRelativePath, UI kit Field/Input with WCAG label associations, Banner variant=danger error state, token-driven Button submit/demo, zero credentials in bundle) and /workspace (WorkspacePickerClient with live workspace search filtering by name/role/currency, top bar with brand link, ThemeToggle, user chip, and Sign out button, enterprise workspace cards with monograms, StatusChip role badges, currency/timezone meta, and direct Open link, plus EmptyState for zero results). Gates: npm test 47/47 passed, format:check clean, build 6.8s, matrix 28/28 checks clean (0 issues across all 7 sizes in light and dark). |
| T5-P2 Overview | done | 1c4fe4d | Overhauled Overview workspace (`/business/[id]/overview/[[...tab]]` and `src/components/Overview.js`) with all 3 tabs (`overview`, `trends`, `health`); period controls bar (Day, Week, Month, Rolling 7, Rolling 30 and compare toggle); canonical entity counts in `.grid-kpi`; executive KPIs as calm `UnavailableState` naming owner and reason (never 0, never error style); `.grid-main-aside` with recent domain activity log and interactive domain filter chips (All, Commerce, Support, Identity, System), density toggle and formatted timestamps; aside operations snapshot definition list and AI governance advisory notice; Trends tab with `ChartCard` + `TrendLine` and `BarCompare` with "View as table" toggles and SIMULATED badges; Health tab with subsystem operational health grid and live Open Business Issues table; unit test `tests/overview.test.js`. Gates: npm test 50/50 passed, format:check clean, build 5.6s, matrix 42/42 checks clean across 7 viewports in light and dark (0 issues). |
| T5-P4 Commerce | done | eb62226 | Overhauled Commerce workspace (`/business/[id]/commerce/[[...tab]]` and `src/components/Commerce.js`) with all 4 tabs (`orders`, `payments`, `deliveries`, `products`); Customer Orders with status filter pills and Drawer with Customer 360 link, line items table, D4 legal status transition control (required reason and expected_status concurrency guard) and refund action; Payments ledger with D6 Financial Timeline switch and idempotent Refund Dialog (Idempotency-Key generated per dialog open); Deliveries list with carrier tracking numbers (CopyableCode) and "Prepared — not executed" carrier transport panel; Products & catalog with SKU, price, inventory and variants table; unit test `tests/commerce.test.js`. Gates: npm test 52/52 passed, format:check clean, build 5.7s, matrix 56/56 checks clean across 7 viewports in light and dark (0 issues). |
| T5-P3 Customers | done | ca2a2dc | Overhauled Customers workspace (`/business/[id]/customers/[[...tab]]` and `src/components/Customers.js`) with Customer directory (search, status filter pills, avatar monograms, registration dates) and Customer 360 profile view (header with monograms, quick KPI tiles, 7 sub-tabs: timeline, orders, conversations, deliveries, website, graph, identity; open integrity issues block; AI customer context as calm UnavailableState; D4 status transition dialog with required reason and expected_status concurrency guard; one-hop context graph topology with shape/icon differentiation). Unit test `tests/customers.test.js`. Gates: npm test 54/54 passed, format:check clean, build green, matrix 42/42 checks clean (0 issues). |
| T5-P5 Support | todo | | |
| T5-P8 AI | todo | | |
| T5-P7 Intelligence | todo | | |
| T5-P6 Growth | todo | | |
| T5-P9 Admin | todo | | |
| T6-1 Responsive and themes | todo | | |
| T6-2 Accessibility | todo | | |
| T6-3 Tests | todo | | |
| T6-4 Reviews | todo | | |
| T6-5 Gates | todo | | |
| T7-1 Final report | todo | | |

## Phase summaries
### Phase 0: Baseline and safety (completed 2026-11-09 23:19)
- Both dev servers verified OK (backend at 127.0.0.1:8000, frontend at 127.0.0.1:3000).
- Frontend tests 18/18 pass, format:check clean, production build green.
- Demo sign-in verified enabled on `/login`.
- Hard-coded password in `scripts/take_browser_tour.js` removed; now fails cleanly if `BIZORA_E2E_*` is unset.
- Next: Phase 1 (tokens, fonts, themes, native controls).

### Phase 1: Foundation (completed 2026-11-09 23:38)
- Tokens installed in `src/styles/tokens.css`; `globals.css` cleanly split into `base.css`, `layout.css`, `components.css`. Raw color grep across `frontend/src` clean (0 matches outside `tokens.css`).
- Fonts loaded via `next/font/google` for Plus Jakarta Sans, Inter, JetBrains Mono, Noto Sans Bengali with zero external CDN requests.
- Dark theme and ThemeToggle implemented with inline head script preventing flash of unstyled theme.
- Native controls (select, option, input, textarea, checkbox, radio, date, focus rings, hover, scrollbars) fully styled and verified across 12 page checks (0 contrast, overflow, focus or console issues).
- All 4 reviewers passed (design, code, security, architect); all findings resolved; gates green (18/18 tests, build 1.7s).
- Next: Phase 2 (Data layer and safe writes: formatters, API client, idempotency, resource config).

### Phase 2: Data layer and safe writes (completed 2026-11-10 00:08)
- Complete formatter suite in `src/lib/format/` (money, dateTime, date, relativeTime, duration, percent, enumLabel, stripUntrusted, recordTitle, statusTone, statusText, missing). Exact enum matching prevents substring issues (INACTIVE is neutral, not active).
- Robust API client in `src/lib/api/` with unified ApiError, 7 backend error shapes, automatic CSRF token retry, safe same-origin redirect on session expiry with open-redirect guard, and React-cached server `getSession`. Segregated serverApi and clientApi to ensure server modules and cookies are never bundled into client components.
- Idempotency and safe writes via `newIdempotencyKey` and `useActionForm` hook supporting busy states, 409 stale-state detection with non-destructive reload flow, key reuse across identical retries, and automatic key rotation on success or payload alteration.
- Resource configurations for all 32 resources in `src/lib/domain/resources.js` with verified query param allow-lists, column definitions, search capability split (14 searchable / 18 exact), workspace mapping, and detail view config.
- All 4 phase reviewers completed (Architect: APPROVE, Design: SHIP, Security: SHIP with SEC-HIGH-1 & SEC-INFO-2 fixed, Code: SHIP with CR-01 to CR-07 fixed). All gates green: 39/39 tests passing, format clean, build clean in 5.1s, 0 page check issues.
- Next: Phase 3 (Shared UI kit: Form basics, Feedback, Overlays, DataTable, Evidence, and UI Kit gallery).

### Phase 3: Shared UI kit (completed 2026-11-10 00:40)
- Complete design-token-driven component library in `src/components/ui/` with zero raw color codes and zero heavy external UI libraries:
  - Form basics: `Button` (sm/md, primary/secondary/ghost/danger, loading spinner), `IconButton`, `Field`, `Input`, `Select`, `Textarea`, `Checkbox`, `MoneyField`, `DateTimeField`.
  - Feedback & Status: `Banner`, `StatusChip` (exact tone mapping with enforced icon and text label), `SeverityChip`, `ConfidenceMeter`, `Skeleton` (opacity pulse, no gradient), `EmptyState`, `UnavailableState` ('Not connected' calm layout with owner and reason), `SimulatedBadge`, `KpiTile`, `ToastProvider` & `useToast`.
  - Overlays & Navigation: `Tabs` (path-segment Link and role=tablist modes with count badges), `Drawer` (slide-over with focus trap, Esc, scrim, scroll lock), `Dialog` & `ConfirmDialog`, `Pagination` ('1–25 of 1,284'), `FilterBar` (accessible search, filter slots, removable pills), `PageHeader` (breadcrumbs, h1, actions, badges).
  - Data presentation: `DataTable` with typed column formatters (`text`, `money`, `datetime`, `status`, `severity`, `entity`, `mono`, `untrusted`), sticky header, density toggle (compact/default), skeleton rows, empty state, error retry, and row-click drawer trigger.
  - Evidence & Audit: `Timeline` (audit thread with status chips), `EvidencePanel` (grounding citations, confidence meter, authoritative source bar), `CopyableCode` (inline/block modes with clipboard API and visual feedback).
  - Dev gallery: `/business/[businessId]/ui-kit` interactive testbed verifying all components in every state at desktop (1440x900) and mobile (390x844), light and dark.
- All 4 phase reviewers completed (Architect: APPROVE, Design: SHIP, Security: SHIP, Code: SHIP with FilterBar accessible name resolved). All gates green: 39/39 tests passing, format:check clean, build green, 12 page checks with 0 issues.
- Next: Phase 4 (Shell, navigation, routes, boundaries: T4-1 to T4-3).

### Phase 4: Shell, navigation, routes, boundaries (completed 2026-11-10 01:13)
- Overhauled enterprise AppShell: 256px rail (72px collapsed with persistent preference and clean toggle button), 6 enterprise nav groups with 9 workspaces mapping, mobile drawer (<1024px) with focus trap, Esc dismiss, and scroll lock, sticky 56px topbar with styled business switcher, role tag, global search `Ctrl+K` trigger and `QuickSearchDialog`, context tag (`BDT · Asia/Dhaka`), theme toggle, and user profile sign-out menu.
- Full Next.js 16 App Router error, loading, and not-found boundaries:
  - Root `global-error.js` with HTML/body shell, high-contrast action buttons (WCAG 2.2 AA compliant), and recovery flow.
  - Root `not-found.js` and business-scoped `not-found.js` with clear navigation back to authorized workspaces.
  - Business `error.js` with inline Banner (variant="danger"), server detail, and retry button with link fallbacks.
  - Business `loading.js` skeleton shaped like final page (header, KPIs, filter bar, table rows; zero white flash).
  - Title metadata template in `layout.js` (`%s · Bizora`).
- Nine-workspace route skeletons created with optional catch-all segments `[[...tab]]`:
  - P2 Overview (`/business/[id]/overview/[[...tab]]`)
  - P3 Customers (`/business/[id]/customers/[[...tab]]`)
  - P4 Commerce (`/business/[id]/commerce/[[...tab]]`)
  - P5 Support (`/business/[id]/support/[[...tab]]`)
  - P6 Growth (`/business/[id]/growth/[[...tab]]`)
  - P7 Intelligence (`/business/[id]/intelligence/[[...tab]]`)
  - P8 AI (`/business/[id]/ai/[[...tab]]`)
  - P9 Admin (`/business/[id]/admin/[[...tab]]` with `MANAGER_ROLES` guard)
- Backward-compatible redirects in `src/lib/domain/redirects.js` mapping all legacy routes and 32 resources:
  - Legacy `records/[resource]/[id]` redirects to the destination workspace tab with `?open=resource:id` drawer parameter.
  - Canonical `resources/[resource]` redirects to the destination workspace tab.
  - Legacy sections redirect to their mapped workspace tabs.
- Backward compatibility and heading normalization: added `hideHeading` to `ResourceList`, `Overview`, `ReviewForms`, `ModuleExplorer`, and `AdvisoryTools` to ensure exactly 1 authoritative `h1` per page.
- Hardened `Button` to support both component references and pre-rendered React elements for the `icon` prop.
- All 40 page checks across all 10 pages at desktop (1440x900) and mobile (390x844), light and dark: **TOTAL ISSUES: 0**.
- Gates green: 43/43 unit tests pass, format:check clean, build green in 5.3s.
- Next: Phase 5 (Workspaces and screens: T5-P1 to T5-P9).

## Decisions I took
- Hoisted `AppShell` to `frontend/src/app/business/[businessId]/layout.js` (ARCH-01) so `AppShell` stays mounted during workspace navigation, error boundaries and loading skeletons render cleanly inside `<main>`, and redundant wrappers were removed from all 9 workspace pages.
- Wrapped `AppShell` in `TooltipProvider delayDuration={150}` and wrapped collapsed rail icons in Radix `Tooltip side="right"`.
- Added user menu trigger to rail footer with Radix `DropdownMenu` containing theme switch and sign-out actions, and guarded theme rendering with `mounted` state to prevent SSR/CSR hydration divergence.
- Used optional catch-all segments `[[...tab]]` in Next.js 16 App Router for clean handling of both base workspace URLs (`/business/[id]/commerce`) and tab segments (`/business/[id]/commerce/orders`) with query fallback.
- Added `hideHeading` prop to `ResourceList`, `Overview`, `ReviewForms`, `ModuleExplorer`, and `AdvisoryTools` to avoid duplicate `h1` headings when wrapped in modern `PageHeader`.
- Hardened `Button` to support both component classes/functions and pre-rendered React elements for the `icon` prop.
- Adjusted error card primary button contrast in `global-error.js` to WCAG 2.2 AA (4.5:1+).
- Sanitized `Tabs.js` to absorb `activeKey` and `tabs` without leaking unhandled props to underlying DOM containers.
- Kept `server.js` and `next/headers` completely separate from `src/lib/api/index.js` and `client.js` so client components never trigger Next.js server-only runtime bundler errors.
- Enforced strict allow-list on query parameters (`filterQueryParams`) in `resources.js` to guard against Django DRF 400 Bad Request on unrecognized filter parameters.
- Hardened `isSafeRelativePath` using WHATWG `new URL` parsing to reject backslashes and control characters, preventing open-redirect vulnerabilities when navigating login redirects.
- In `useActionForm`, maintained both a ref and React state for `idempotencyKey` so components re-render cleanly when keys rotate while preserving synchronous execution.

## Blocked / questions for the owner
(none yet)

## Baseline results (T0-2)
Old UI, measured by Claude on 2026-11-09 before any overhaul work: `~/bizora-shots/baseline/` (46 screenshots plus `report.json`; 23 pages at 1440x900 and 390x844, light theme, signed in as the demo owner).
- Automatic check totals (`verify-pages.mjs`): **288 issues in 46 checks** = 286 raw-content (raw JSON blocks, raw ISO timestamps, "Record #id" titles) + 2 contrast (the `/login` brand dot, 1.42:1). Console errors 0, failed requests 0, horizontal overflow 0, wrong h1 count 0, unnamed controls 0, invisible focus stops 0.
- Worst pages (both sizes added): identity 110, customer record 84, website-performance 30, business insights 26, configuration 12; inbox, queue and observability 4 each.
- Gates: `npm test` 18 of 18 pass and `npm run format:check` clean (run after the demo sign-in commit); `npm run build` passes (13.7 s; Next.js 16.4.5, run while the dev server was up: dev uses `.next/dev`, so the two do not collide); the Playwright suite was not run (no Chrome, and it skips without credentials).
- Reading this: the old UI already passes most structural checks, so the target is the **raw** column going to 0 and the contrast issue fixed, plus everything the script cannot measure (hierarchy, density, theme, consistency), which only the design review can judge.


## Dependencies added
- `recharts@3.10.1`: Every chart, through token-driven wrappers in `src/components/ui/charts/` (T3-7). `npm audit --omit=dev`: 0 vulnerabilities.
- `@radix-ui/react-tooltip@1.4.1`: Collapsed-rail labels, reasons on disabled controls, full text of truncated names. `npm audit --omit=dev`: 0 vulnerabilities.
- `@radix-ui/react-dropdown-menu@2.2.1`: User menu in rail footer and topbar, row action menus. `npm audit --omit=dev`: 0 vulnerabilities.
- `@radix-ui/react-popover@1.3.1`: Filter popovers, date range selection. `npm audit --omit=dev`: 0 vulnerabilities.
- `clsx@2.1.1`: Conditional class name composition for UI kit wrappers. `npm audit --omit=dev`: 0 vulnerabilities.
