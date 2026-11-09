# Frontend audit report

Date: 2026-11-09. Subject: `frontend/` (Next.js 16.4.5, React 19.3, plain JavaScript) on `main` at 8010daa plus the local commit `1daa828` (demo sign-in). Method: three independent read-only code audits (CSS and colours, code and structure,
backend dependencies), my own live walk-through of the running app (screenshots), and the teammate's notes. **Confidence:** the CSS contrast numbers were computed by script; code findings cite file and line and were read, not run;
items marked (unverified) come from reading CSS or code only. I opened these pages in the browser: login, business choice, overview, customers list, customer record, orders, inbox, business insights, AI assistant, and overview at phone width.
The other sections were audited from code only.

## 1. Verdict
The skeleton is sound and worth keeping: the backend proxy, session and CSRF handling, role-aware navigation, mobile drawer, skip link, honest "unavailable" wording and a real test habit. Every endpoint path and method the UI calls matches our verified API reference, and all data on screen is real (no mocks).
It is **not yet a product UI**: it is a generic record browser (20 flat menu items, 32 identical lists, raw JSON dumps), styled in a teal palette of hard-coded colours with no dark theme, no loaded fonts, a few failing contrast pairs, and several real bugs (lost error information, retry duplicates, stale-state loop, misleading status colours).
The overhaul keeps Next.js and JavaScript, keeps the proxy semantics, and replaces the presentation, information architecture and data layer.

### Ten biggest problems (most damaging first)
1. **No product structure.** 20 flat sections plus 32 generic resource lists plus raw "views"; nothing is organised into the nine workspaces (`DESIGN_SPEC.md`); no tabs, drawers, dialogs, toasts or skeletons exist.
2. **Tables say nothing.** One 4-column `DataTable` for every resource; `recordTitle` heuristics (`src/lib/format.js:27-36`) produce "Record #id" for payments, refunds, messages, tags, contacts and timeline rows. The demo customer "Demo Buyer" shows as "Record #1". No amounts, dates, channels or message text.
3. **Raw data on screen:** `<pre>` JSON in Business insights, 360 views, AI answers and contract results; raw ISO timestamps (`2026-11-09T15:43:38.186907Z`); raw float money; the `<untrusted_customer_data>` wrapper printed literally.
4. **Palette and tokens:** 47 distinct colour literals (40 hex, 7 rgba), 67 of them outside `:root`; teal everywhere plus stray violet and indigo; four unrelated green-grey borders; no dark mode; `--accent` and `--surface-muted` unused; `--surface` bypassed by 13 literal whites.
5. **Failing non-text contrast:** form-control borders 2.05:1, button borders 1.52:1, focus ring on the sidebar 1.47:1, active nav fill 1.39:1, table hover invisible (1.03:1), disabled login inputs look enabled.
6. **Fonts not loaded:** `Inter` is named but nothing loads it (no `next/font`); Plus Jakarta Sans, JetBrains Mono and Noto Sans Bengali are absent; weights 530/650/750 need a variable font that is not there; no monospaced IDs or right-aligned numerics.
7. **Error layer drops information:** `src/lib/clientApi.js:29-30` throws a bare `Error`; status, code and field errors are lost; DRF answers expired sessions with 403 (never 401) so session expiry shows as a form error; the 401 branch in `[section]/page.js:69` is dead code; bare-list errors render as "0: msg".
8. **Writes are unsafe on retry:** idempotency keys regenerate on every submit (`RecordCommands.js:174,192,205`, `CreateRecord.js:40`, `ProductAssessment.js:77`); a retry after a timeout duplicates refunds, notes and callbacks. A `409 STALE_STATE` only prints text and never refreshes, so every retry fails the same way (`RecordCommands.js:244-245`).
9. **Misleading status colours:** `/ACTIVE/` also matches INACTIVE (shown green); RETURNED, REFUNDED, SENT, MISSED, BUSY, CLOSED are unmapped (`format.js:22`); tone is parsed from display text instead of exact codes.
10. **No boundaries or shell layout:** no `loading.js`, `error.js`, `not-found.js`, `global-error.js`; no `business/[businessId]/layout.js` so every page re-mounts `AppShell`, re-fetches the session and loses state; static metadata only.

## 2. What exists (facts)
- **Stack:** Next.js 16.4.5 (app router, Turbopack), React 19.3.1, plain JS (`jsconfig.json`), one dependency (`lucide-react` 0.468), dev: Playwright 1.65, Prettier 3.9. No Tailwind, TanStack, Zod, chart or graph library. Scripts: `dev`, `build`, `start`, `test` (node:test), `test:e2e` (Playwright), `format:check`. No lint, no typecheck.
- **Proxy:** `src/app/api/backend/[...path]/route.js` allows roots `frontend`, `businesses`, `actions`; checks Origin on non-GET; forwards cookie, content-type, `x-csrftoken`, `idempotency-key`; rewrites pagination links to same-origin relative; forwards Set-Cookie. Server components call Django directly through `src/lib/serverApi.js`.
- **Auth:** Django session cookie plus CSRF header via `app/frontend_auth.py` (`/api/frontend/session`, `login`, `logout`); the role per business comes from the session payload; manager-only items are hidden and manager sections 404 for others; no middleware. Plus our demo sign-in (`src/lib/demoLogin.js`, `src/app/api/demo-login/route.js`).
- **Routes:** `/`, `/login`, `/workspace`, `/business/[id]/[section]` (20 sections in `src/lib/catalog.js`), `/business/[id]/resources/[resource]` (32 lists), `/business/[id]/records/[resource]/[id]`.
- **Components (13):** AppShell, Overview, DataTable (also holds StatusBadge and FieldGrid), ResourceList, ModuleExplorer, CreateRecord, RecordCommands, ReviewForms, AdvisoryTools, IdentityTools, IdentityEvidence, ContractTools, ProductAssessment. Libraries: catalog, clientApi, serverApi, format, productReview, demoLogin.
- **Tests:** 18 unit tests in 4 files (format 3, productReview 2, proxy 3, demoLogin 10; all pass) and 9 Playwright tests in 8 specs that **skip silently** without `BIZORA_E2E_*` variables (an unset environment is a false green); they expect `/usr/bin/google-chrome`; there is no `webServer` and no CI.
- **Page plan coverage (our nine workspaces):** P1 Sign-in present; P2 Overview partial (counts only, revenue hard-coded "—"); P3 Customers partial (list plus stacked 360 sections, no tabs); P4 Commerce partial (separate nav items, generic lists, detail commands exist); P5 Support partial (lists plus conversation commands, no thread view);
  P6 Growth partial; P7 Intelligence **missing** (Business Intelligence and Graph are not mounted in the backend); P8 AI partial (query, recommendations, proposals review; no audit); P9 Admin partial (identity, read-only configuration and health, contract probe).

## 3. Live walk-through (my screenshots)
| Page | What I saw |
|---|---|
| Login | Centred card, plain, works; demo button present. Disabled inputs look enabled while loading. |
| Business choice | One card list; fine but no sign-out and no `next`. |
| Overview | Dark teal rail with 20 items (needs scrolling), top bar 65 px (not sticky), customer-only search. Tiles: Revenue "—" with an "Unavailable" pill, Orders 1, Customers 1, Open cases 2. The "Analytics unavailable / Partial" panel is a paragraph, not the "Not connected" pattern. Cards inside cards, large empty areas. |
| Customers | Filter form with raw labels "Q", "Contact", "Contact Type", "Tag", "Status" as free-text boxes (no selects). Row reads "Record #1 / Stored record, ACTIVE, #1, Open record"; the customer's name is missing. A collapsed "All canonical resource lists" link wall under every list. |
| Orders | Same generic table: "Record #1, PENDING"; no total, no date, no customer. |
| Customer record | Title "Record #1" (the customer is "Demo Buyer"); "Stored fields" key-value grid with raw ISO timestamps; actions hidden inside a collapsed "Change recorded state". |
| Inbox | Two rows "Record #2", "Record #1", state OPEN; no subject, channel, last message or assignee. |
| Business insights | Ten pill buttons; the page body is raw JSON in `<pre>` blocks (window, health, KPI arrays). |
| AI assistant | Question box and an empty "Recorded recommendations" list; "AI suggestion" badge. Usable but bare. |
| Phone width (375) | Works: hamburger drawer, stacked tiles. The business `<select>` is truncated ("Bizora Domains D"), the header is cramped, tiles are heavy cards. |

## 4. Design system audit (CSS)
`src/app/globals.css` is the only stylesheet (about 1,175 lines). Helper scripts for these numbers lived in a scratch folder; the facts are reproduced here.

### 4.1 Colour inventory (47 distinct literals, 81 uses, 67 outside `:root`; 17 custom properties, 2 unused)
| Role | Values found |
|---|---|
| Canvas | `#f0fdfa` (L7; also L287, L719) |
| Surface | `#fff` x14; `#f8fafc` x4 (L613, L630, L791); `#f8fcfb` L635; `#e8faf5` x2 (L331, L400); `#f8f7ff` x2 (L541, L1101) |
| Text | `#134e4a` (18 uses); `#1e293b` (4); `#475569` x3 (18 uses; L440, L629); `#64748b` L595 |
| Border | `#d5ebe7` (10); `#a7dcd3` x2 (L14, L613); `#9bbcb6` L587; `#e4efec` L625; `#ddd6fe` L542 |
| Primary teal | `#0f766e` x2; `#115e59` x3 (L2, L4, L164); `#0d9488` unused; `#ccfbf1` x3; `#2563eb` L54 (focus) |
| Status | `#166534` x2; `#92400e` x2; `#991b1b` x3; `#dcfce7`; `#fef3c7`; `#fee2e2`; `#fef2f2`; `#fecaca`; `#fffbeb`; `#fde68a` |
| Extra accents | violet `#6d28d9`/`#ede9fe` L444; indigo `#3730a3`/`#e0e7ff` L1056 |
| Navigation | `#c7ece6` x3; `#d4f3ee`; `#e3f5f1`; `#5eead4`; `#79b4ad`; `rgba(255,255,255,.12/.2/.23)` |
| Shadow and scrim | `rgba(19,78,74,.05)` L15, `.09` L818; `rgba(0,0,0,.1)` L926; `rgba(15,43,39,.48)` L950 |

### 4.2 Contrast (63 pairs computed; no text pair fails 4.5:1, lowest is the placeholder at 4.76)
| Selector (line) | Colours | Ratio | Needs |
|---|---|---|---|
| input, select, textarea border (L587) | `#9bbcb6` on `#fff` | 2.05 | 3.0 |
| `.button` border (L378), `.top-search button` (L284) | `#a7dcd3` on `#fff` | 1.52 | 3.0 |
| focus ring on the sidebar (L53) | `#2563eb` on `#115e59` | **1.47** | 3.0 |
| `.nav-active` fill (L223) | `#0f766e` on `#115e59` | 1.39 | 3.0 (only the 3 px bar marks state) |
| table scroller thumb (L613) | `#a7dcd3` on `#f8fafc` | 1.45 | 3.0 |
| `tbody tr:hover` (L634) | `#f8fcfb` on `#fff` | 1.03 | hover is invisible |
| `.button:disabled` (L402) | `#fff` on `#7bb4af` | 2.34 | exempt but weak |

New tokens: documented pairs hold, except `--color-focus` on `--color-nav-bg` is **2.66:1**, so the rail must use `--color-focus-on-nav` (= nav indicator, 7.02:1). `nav-active-bg` against `nav-bg` is only 1.22:1, so the indicator bar plus `aria-current` carry the active state.

### 4.3 Native controls and dropdowns (owner priority)
No `option`, `::picker(select)`, `accent-color`, `color-scheme` or `appearance` rules exist. `select` shares L583-593 (white, `#1e293b`); the business switcher is `#134e4a` weight 650; desktop Chromium and Firefox option lists inherit these. Hover and selected rows of the option list and macOS or mobile popups are OS-drawn and ignore tokens.
Placeholder options ("All", "Choose a reviewed candidate") look like chosen values. Disabled login inputs look enabled (author styles beat UA disabled styles). The checkbox inherits the `input` box (40 px, padding) and Chromium's blue accent (unverified visually). Search cancel, `:-webkit-autofill` and textarea placeholder are unstyled.
A literal-white `select` stays white in dark mode. Fix: `select, option { background-color: var(--color-surface); color: var(--color-text) }`, `accent-color: var(--color-primary)`, an autofill override, explicit disabled/invalid styles, optionally `appearance: base-select` where supported, and check both themes in the browser.

### 4.4 Typography, spacing, radius, shadow, layout
- Declared `--font: Inter, ui-sans-serif, system-ui`; **nothing loaded** (`layout.js` only imports CSS). 13 font sizes (11, 12 x10, 13, 14, 15, 16, 17, 19, 20, 23, 24, 28, 30); off-scale: 15, 17, 19, 20, 23, 30. Weights 530, 600, 650, 700, 750, 800 (spec: 400, 500, 600, 700 for headings). Body line-height 1.55 (spec 1.43). Tabular numerals on 4 selectors only; no mono for IDs; `th` left-aligned for numbers.
- 43 distinct `padding` values and 12 `gap` values; off the 4 px grid: 3, 7, 9, 11, 13, 15, 17, 18, 22, 25, 35, 55. Radius 8, 10, 11, 12, 16, 999 (spec 4, 8, 12, 16, full; chips 4). Shadow on every card including nested ones. Focus ring 3 px/3 px (spec 2/2).
- Layout vs spec: top bar 65 px and not sticky (spec 56, sticky); content 1600 px (spec 1440); no collapsed sidebar; breakpoints 1100/850/650/360 (spec 640/768/1024/1280/1536); duplicate `@media` blocks appended after the reduced-motion block.

### 4.5 Components and states
| Component | Problem |
|---|---|
| Buttons | No danger or ghost variant, no sizes; Reject is a secondary button (`ReviewForms.js:48`); `.top-search button`, `.account button`, `.menu-button` are ad hoc with no hover; no `:active`; primary hover colour equals the sidebar colour. |
| Inputs | 2.05:1 border; no hover, disabled or invalid styles; the label rule is duplicated 7 times with three different sizes (L573, L1064, L1089, L1158). |
| Tables | Not sticky, hover invisible, no density, no numeric alignment; the scroll wrapper is not focusable. |
| Badges | No icon (colour alone is a banned pattern), extra violet and indigo, pill radius. |
| Alerts | Danger and warning only, no icon; success and error are bare coloured text (L750-759). |
| Cards | Nested cards (`.advisory-tool` L1080, `.advisory-result`, `.plan-result` inside `.surface`); `.workspace-card:hover` translates with no transition (L875). |
| Details | Rows lack separators and double-pad inside `.surface`; primary actions hidden inside collapsed `<details>`. |
| Tabs | None; `.module-nav` is button-styled links without `aria-current`. |
| Sidebar and top bar | Focus ring 1.47:1, active 1.39:1, closed drawer links still tabbable, no theme toggle. |
| Drawer | 42 px targets, teal scrim, no `role="dialog"`. |
| Auth screen | Disabled inputs look enabled; `.auth-card button` margin leaks; h1 28 px. |
| States | Hover on buttons, nav, links, rows, workspace card only; no `:active`; disabled only for `.button`; one global `:focus-visible` rule (full coverage, wrong colour on the rail); reduced-motion override exists but `scroll-behavior: smooth` (L23) is unconditional; no `prefers-color-scheme`, `color-scheme`, `data-theme` or `forced-colors`; touch targets 38 to 42 px (spec 44 on touch). |

### 4.6 Old to new colour mapping
| Old | New token |
|---|---|
| `--sidebar`, L850 | `--color-nav-bg` |
| `--primary`, `--primary-hover` | `--color-primary`, `--color-primary-hover` |
| `--accent` | delete |
| `--mint` (selection, monogram) | `--color-primary-subtle` |
| `--canvas` | `--color-canvas` |
| `--surface`, `#fff` backgrounds (L102, 243, 264, 396, 589, 814) | `--color-surface` |
| `#fff` text (L389, 393) / (L131, 149, 219, 224, 851) | `--color-on-primary` / `--color-nav-text-active` |
| `--surface-muted`, `#f8fafc`, `#f8fcfb`, `#e8faf5`, `#f1f5f9`, `#f0fdfa` | `--color-surface-subtle` |
| `--heading`, `--text` | `--color-text` |
| `--muted`, `#475569` (labels, th) | `--color-text-secondary` |
| `--muted` (help text, `td small`), `#64748b` | `--color-text-muted` |
| `--border`, `#e4efec` | `--color-border` |
| `--border-strong`, `#a7dcd3`, `#9bbcb6` | `--color-border-input` |
| `#2563eb` | `--color-focus` (on the rail: `--color-focus-on-nav`) |
| `#166534` / `#dcfce7` | `--color-success-text` / `--color-success-subtle` |
| `#92400e` / `#fef3c7`, `#fffbeb` / `#fde68a` | `--color-warning-text` / `--color-warning-subtle` / `--color-warning` |
| `#991b1b` / `#fee2e2`, `#fef2f2` / `#fecaca` | `--color-danger-text` / `--color-danger-subtle` / `--color-danger` |
| violet `#6d28d9`/`#ede9fe`, `#f8f7ff`/`#ddd6fe` | `--color-primary-text`/`-subtle`, `--color-primary-subtle`/`--color-border` |
| indigo `#3730a3`/`#e0e7ff` | `--color-info-text` / `--color-info-subtle` |
| `#e3f5f1`, `#d4f3ee` | `--color-nav-text` |
| `#c7ece6`, `#79b4ad` | `--color-nav-muted` |
| `#5eead4`, L225 bar | `--color-nav-indicator` |
| L223 fill, `rgba(255,255,255,.12/.2/.23)` | `--color-nav-active-bg` |
| `rgba(19,78,74,..)`, `rgba(0,0,0,.1)` | `--shadow-e1` / `--shadow-e3` |
| `rgba(15,43,39,.48)` | `--color-scrim` |

### 4.7 CSS defect list (priority order; `tokens.css` now has the missing shadow, radius, spacing, type, scrim, disabled and nav-focus tokens)
1. L53 focus ring 1.47:1 on the rail: 2 px outline `--color-focus`, offset 2 px; inside the rail use `--color-focus-on-nav`. 2. L587 control border: `--color-border-input`. 3. L918-927 closed drawer is still tabbable: `visibility: hidden` with delay or `inert`.
4. L222-226 active nav: `--color-nav-active-bg`, inset 3 px indicator, `forced-colors` border. 5. L402 disabled: add `input:disabled`, `select:disabled` styles with disabled tokens. 6. No dark mode: install tokens, replace the 67 literals, theme `select, option`, `accent-color`, autofill.
7. Fonts: `next/font` for the four families. 8. L443, L537, L1055, L1098 violet and indigo: use primary-subtle/primary-text and info tokens. 9. Badges: icon, subtle fill, 1 px status border, radius 4. 10. L634 row hover: `--color-surface-subtle`; sticky `th`; right-aligned mono numerics.
11. L611 scroller: `tabindex="0"`, `role="region"`, labelled; thumb `--color-border-input`. 12. Add `.button-danger` and use it for Reject with a confirm dialog. 13. L282, L300, L931-946: `.button-ghost` and `.icon-button` with hover and active. 14. Targets: 36 px desktop, 44 px under `pointer: coarse`.
15. Alerts: info and success variants with icons; reuse for L750-759. 16. Nested cards (L789, L1080, L1098): flatten with subtle surface and a divider. 17. Shadows: flat cards with border; e1 to e3 tokens; L818 and L926 become e3. 18. Radius 10 and 11: use 8 or 12; chips 4.
19. Type: body 1.43, h2 22, h3 18, weights 400/500/600, spec tracking. 20. One label rule (13 px, 600, secondary text). 21. Off-grid spacing (L448, L468, L658, L707, L860). 22. L875 hover: border-colour change at 120 ms, no transform. 23. L23 smooth scroll only under `prefers-reduced-motion: no-preference`.
24. Layout: top bar 56 px sticky, content 1440, drawer breakpoint 1024, merge duplicate `@media` blocks. 25. `.module-nav`: `aria-current="page"`, underline-style active tab in `--color-primary`.

## 5. Code and structure audit
### 5.1 Bugs
**High**
- `DataTable.js:49-52` and `[section]/page.js:143`: the support queue passes `resource="support-queue"` (not in `RESOURCES`), so no row links to its conversation. Fix: column config carries `linkResource: 'conversations'`.
- `clientApi.js:29-30`: bare `Error(message)`; status, code and field map are lost; 201 vs 200 is lost. Expired sessions come back as 403 `{"detail":"Authentication credentials were not provided."}` (DRF library behaviour, not verified live), never 401, so session expiry is a form error. `[section]/page.js:69` (`status === 401`) is dead code; `serverApi.js:21` returns a 503 `{detail}` as a "session" (bounces to /login).
  Fix: `ApiError {status, code, detail, fieldErrors, raw}`; on that 403 go to `/login?next=`; on "CSRF Failed" refetch `frontend/session` and retry once.
- Idempotency keys regenerate on every submit: `RecordCommands.js:174` (also `external_refund_id` :205, `external_message_id` :192), `CreateRecord.js:40`, `ProductAssessment.js:77`. A retry after a timeout duplicates refunds, notes (:188, no source id) and callbacks. Fix: one key per user intent (`useRef`), reused on retry, rotated on success or payload change (else 409 IDEMPOTENCY_CONFLICT).
- `RecordCommands.js:244-245`: 409 STALE_STATE (`expected_status` :184, `expected_updated_at` :202) only prints text and never refreshes, so every retry fails with the same stale `record.status`. Fix: on 409 `router.refresh()`, show a notice, keep inputs.

**Medium**
- The Previous link disappears: `ResourceList.js:36` (`.search` is `''` on DRF page 1) and `ModuleExplorer.js:16-19` (`get('page')` is null on page 1); e2e never clicks Previous. Fix: test `data.previous != null`.
- `format.js:22`: `/ACTIVE/` matches INACTIVE (green); RETURNED, REFUNDED, SENT, MISSED, BUSY, CLOSED unmapped; tone parsed from display text. Fix: map enum codes to tones.
- `ReviewForms.js:17-31,50,103`: `pending` covers only the refresh so Approve and Reject can both be fired; after approval the form unmounts so the success text never shows. Fix: busy around the POST; show the result outside the form.
- False empty states: `[section]/page.js:93,117` (issues and candidates become `[]` or null on failure) and `records/.../page.js:31-34` (failed extras dropped). Fix: per-panel error or UnavailableState.
- `clientApi.js:11-12`: only the first field error; a DRF bare list `["msg"]` renders `"0: msg"`; nested errors `[object Object]`. Fix: parse all six shapes (`docs/frontend.md` 1.5).
- `untrusted_customer_data` is never stripped: `DataTable.js:11-30` (FieldGrid) prints message `content` with the wrapper; message tables show only "Record #id". Fix: `stripUntrusted()` plus an `UntrustedText` component (labelled, pre-wrap, never HTML); send the wrapped text unchanged to the AI endpoints.
- Timezone: `RecordCommands.js:141,161` `scheduled_at` is free text; a naive value is read as UTC by DRF; `format.js:42-47` shows raw ISO; the business time zone is only printed. Fix: `datetime-local` converted with the business zone to an offset ISO; `formatDateTime(iso, tz)` with a fixed locale (hydration-safe).
- Money: `fieldValue` prints a raw JSON float; the refund amount is unvalidated (:134). Fix: `formatMoney(amount, currency)`, regex `^\d+(\.\d{1,2})?$`, never sum across currencies.
- `crypto.randomUUID()` (`RecordCommands:174`, `CreateRecord:40`, `ProductAssessment:77`, `ContractTools:45`) is undefined on non-secure origins (LAN `http://192.168.x.x`), so every write fails there. Fix: an `idempotency.js` fallback.
- `DataTable.js:123` derives a resource from the key: `external_references`, `related_conversations`, `marketing_conversions`, `internal_notes`, `visitor_journey` are not in `RESOURCES`, so no links; `:118-119` says "first 50 shown" without a link to the filtered child list; `:109` repeats `customer` on 360; `:126-135` drops the `owner` of UNAVAILABLE.
- The identity page has no pagination (`page.js:59-65` fixed 25; `ReviewForms.js:216`).
- `ResourceList.js:53` labels `q` as "Q"; enums (status, channel, priority, platform) are free text (:62-67); 23 of 32 resources have no filters (:6-21); `visitors: []` although the API allows `is_anonymous` and `customer`; all query keys are forwarded to Django (`[section]/page.js:39-43`, `resources/.../page.js:18-20`), which answers 400 for unknown ones.

**Low:** `AdvisoryTools.js:60` badges every 200 body "AI suggestion" even UNAVAILABLE and prints raw JSON; `IdentityTools.js:72-76` silently drops invalid IDs; `login/page.js` had no `next`; `workspace/page.js:12-15` has no sign-out; `AppShell.js:139` exact-match active nav and `ICONS` (:26-47) crashes render for a new section;
`RecordCommands.js:130,143-156` offers refund and prepare regardless of status; `route.js:2` allows root `actions` (including `execute`) and there are no fetch timeouts (`route.js:40`, `serverApi.js:8`); `scripts/take_browser_tour.js:28-29` hard-codes a demo password; key fallbacks can collide (`ModuleExplorer.js:61`, `AdvisoryTools.js:158`);
`DataTable.js:5` HIDDEN_FIELDS is a deny-list (a new secret field would render); hard-coded backend enums (`RecordCommands.js:9-47` matches `states.py` today but has no drift test; `ContractTools.js:9-17`; `IdentityTools.js:9-43`; review decisions omit REVIEWING).

### 5.2 Structure problems
- No `business/[businessId]/layout.js`: each business page repeats session lookup, business find, auth redirect and mounts `AppShell` (remounts, state lost); `getSession` is not `React.cache`d; session then data is a waterfall.
- `[section]/page.js` (163 lines) is a 9-branch switch over mixed data contracts; `ReviewForms.js`, `AdvisoryTools.js` (`AssistantWorkspace`) and `ContractTools.js` put page layout inside `'use client'` files; `StatusBadge` lives in `DataTable.js` and is imported by client files.
- Config is scattered: `SECTIONS` vs `ICONS` vs `FILTERS` vs `TRANSITIONS` vs `HIDDEN_FIELDS` vs `recordTitle` keys vs `CONTRACTS` vs `COMMANDS`; `BACKEND_ORIGIN` repeated 3 times; the same-origin check is duplicated (`route.js:13-30` and `demoLogin.isSameOrigin`).
- No `loading.js`, `error.js`, `not-found.js`, `global-error.js`; static metadata (`layout.js:3`); `login` is a client page so it has none; every navigation blocks with no skeleton.
- Routes: 20 flat sections plus 32 resource lists plus `?view=` modules plus records; duplicates (`/customers` and `/resources/customers`); a `MoreResources` link wall under every list; `ModuleExplorer.js:60-77` dumps each Observability and Configuration row as a raw FieldGrid.

### 5.3 Target `frontend/src` (keep Next.js and JavaScript; no TypeScript, no CSS framework, no new heavy dependency)
```
app/ layout.js error.js global-error.js not-found.js
  login/  workspace/  api/{backend,demo-login}/   (paths unchanged)
  business/[businessId]/ layout.js loading.js error.js not-found.js
    overview/[[...tab]]  customers/  customers/[customerId]/[[...tab]]
    commerce/[tab]  support/[tab]  growth/[tab]  intelligence/[tab]  ai/[tab]  admin/[section]
    [section]/  resources/  records/            (legacy: redirects until tests migrate)
components/ ui/  form/  table/  shell/  domain/<page>/
lib/ api/  domain/  format/  auth/             (shims keep catalog.js, format.js, clientApi.js, productReview.js, demoLogin.js working)
styles/ tokens.css  base.css  layout.css  components.css
```
- `ui`: Tabs, Drawer and Dialog/ConfirmDialog (native `<dialog>`, no dependency), Toast, Skeleton, EmptyState, UnavailableState (with owner), SimulatedBadge, StatusBadge, KpiTile, Timeline, EvidencePanel, JsonView (for diagnostics only), Pagination, FilterBar, PageHeader, Banner, Button, ThemeToggle.
- `table`: column-driven `DataTable` (JSDoc `Column` type), cells `MoneyCell`, `DateTimeCell`, `StatusCell`, `EntityLink`, `UntrustedText`. `form`: Field, Select, Textarea, MoneyField, DateTimeField, IdField, `useActionForm` (busy, ApiError, field errors, idempotency, 409 reload).
- `lib/api`: `client.js` (ApiError), `server.js` (cached `getSession`), `errors.js`, `pagination.js`, `idempotency.js`, `query.js` (per-resource allow-list), `proxy.js`. `lib/domain`: `resources.js` (columns, filters, search support, link target, page), `states.js`, `enums.js`, `roles.js`. `lib/format`: money, datetime(tz), duration, enum labels, status tone by code, `stripUntrusted`.

## 6. Old route to new home
| Old section or route | Backend calls | New home |
|---|---|---|
| overview | `overview/`, `support-queue/?page_size=1` | P2 `overview` |
| customers | `customers/`; `customers/{id}/360/`, `graph-context/customer`, `retargeting-context` | P3 list and 360 |
| products | `products/`, `products/assess`, `product-references` | P4 `products` (assess and mapping as dialogs; mapping is manager only) |
| orders, payments, finance, delivery | `orders/`, `payments/`, `financial-timeline/` (key by entity_kind and id), `shipments/` | P4 `orders`, `payments`, `deliveries`; transition, refund and prepare as dialogs |
| insights | `overview/{summary,kpis,trends,issues,health,activity,recommendations,cross-domain,catalog,configuration}` | P2 `trends` and `health`; P7 `facts` and `metrics`; the `configuration` view moves to P9 |
| inbox | `conversations/`, `/context/`, priority, assign, handover, note, reply, `ai/support/*` | P5 `inbox` with thread drawer; assign and handover dialogs |
| queue, calls | `support-queue/`; `calls/`, `callbacks`, `ai/summarization/call` | P5 `queue`, `calls` with callback dialog |
| marketing | `campaigns/` (metrics, conversions, ad-sets, `ai/marketing/explain-campaign`) | P6 `campaigns` with drawer tabs |
| website, website-performance | `visitors/`, `visitors/{id}/journey/`, `website-performance/` (7 UNAVAILABLE keys) | P6 `website` |
| assistant | `ai/recommendations/`, `issues/`, `ai/assistant/query/`, diagnose | P8 `assistant` (issues also on P7) |
| actions | `ai/actions/`, `actions/{id}/review/` | P8 `actions` with approval dialog and SimulatedBadge |
| identity, contracts | `identity/*`, commands, `dry-run`; `contracts/{owner}/{capability}` | P9 `identity` (also P3 `identity` tab); contract probe inside P9 `integrations` |
| configuration, observability | module reads | P9 `configuration`, `integrations`; `?view=` becomes the tab, `?record=` a drawer |
| `/resources/[resource]`, `/records/[resource]/[id]` | list and detail | tab tables and drawers (`?open=resource:id`); record pages stay as deep links with the new look |

Resource grouping: products, variants, product-images, orders, payments, refunds, shipments, shipment-events go to P4; customers, contacts, tags and the `*-references` resources to P3; conversations, participants, messages, attachments, notes, calls, call-events, transcripts, callbacks to P5; campaigns, campaign-metrics, conversions, ad-accounts, ad-sets, creatives, ads, visitors, sessions, website-events to P6.

## 7. Tests: what exists and what will break
Untested today: components, columns, pagination, `TRANSITIONS` drift, idempotency reuse, session expiry, untrusted text, money and dates, tone edge cases, roles.
Would break during the overhaul (update in the same commit as the change):
- `format.test`: `catalog.js` exports and the `/business/{id}/...` and `/records/...` shapes; `errorMessage` output format; `label`, `statusText`, `statusTone` strings.
- `proxy.test`: path and exports of `api/backend/[...path]/route.js`; plain-object headers (`options.headers.cookie`); the `/api/backend/...` link rewrite. Do not change proxy semantics, only add.
- `demoLogin.test`: reads `src/app/login/page.js` as text (moving `/login` breaks it).
- Playwright: iterates `SECTIONS`, `MODULE_VIEWS`, `RESOURCES`; expects h1 text equal to each section label, a `table` role on every list, `.alert-danger`, `.workspace-card`, `.disclosure`, `.plan-result`, `.form-error`, `#contract-*`, `#callback-reason`, labels such as "Entity Type *", names (Sign in, Apply filters, Open record, Next, Products), copy ("Internal change saved.", "Request prepared; execution remains unavailable.", "A shared SKU is not proof of identity."), URLs `/workspace`, `/login`, `/business/\d+/overview`, `platform=META`, `view=connections&record=`, the default Next 404 heading, and no horizontal scroll at 320 px. `scripts/take_browser_tour.js` also hard-codes `/business/1/...` URLs.
- The 9 Playwright tests skip when `BIZORA_E2E_*` is unset (false green) and need `/usr/bin/google-chrome`; there is no CI.

## 8. Risks for an unattended overhaul
- Keep legacy redirects and shims until the tests are migrated; migrate tests in the same phase as each route or label change.
- Do not alter proxy semantics (cookie, `x-csrftoken`, `idempotency-key`, origin check, 403 instead of 401); only add.
- Idempotency key reuse must rotate when the payload changes; keep the `expected_*` tokens.
- Honesty copy ("recorded", "Pending — not delivered", execution UNAVAILABLE, Simulated) regresses easily when restyling.
- `UNAVAILABLE` and unmounted Business Intelligence, Graph and Knowledge tabs must render `UnavailableState`, never an error.
- Next 16 differs from memory: read `frontend/node_modules/next/dist/docs/` first; `serverApi` must never reach client bundles; date formatting needs a fixed time zone and locale on server and client.
- Native dialog focus, 320 px width and the mobile nav need manual checks; there are no screenshot tests.
- Split `globals.css` in cascade order; replace raw hex with tokens.
- Docs conflict: `docs/STACK.md` says "not scaffolded" and `docs/frontend.md` decision D-F01 says Vite; both are superseded by "adopt the teammate's Next.js 16 JavaScript app" (decision D-F20).
- Per-phase gate: `npm test`, `npm run format:check` (no semicolons, 110 columns), `npm run build`, e2e with credentials on an isolated SQLite database when possible, grep for `dangerouslySetInnerHTML` and `.env`, one commit per task.

## 9. Backend dependencies
The UI depends on backend work that is not the frontend's job. The full per-domain lists are in `docs/backend-issues/` (8 blockers, 28 high). The ones that shape the UI most: Business Intelligence and Graph are not mounted and cannot be (BI-01, BI-02, BG-01 Python 3.12 import, BG-02, BG-03 rule keys), so P7 shows
"Not connected"; nothing runs the BI calculators (BI-03) so KPIs, trends and health are UNAVAILABLE; no recommendations or actions are ever created (AI-01); no agent or team list (PL-08) so assignee pickers use ids; one error shape does not exist (PL-05); no edit endpoints (BD-01) so detail pages are read-only apart from the documented commands.
