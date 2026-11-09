# Plan: frontend overhaul (about 7.5 hours)

This is the only task list. Status lives in `PROGRESS.md`. Do tasks in order unless a dependency says otherwise; every task ends with `/verify` and `/checkpoint` (one local commit). Times are boxes, not promises: if a task overruns by double, cut it to its acceptance criteria and log the rest.
Reasons and evidence for each task are in `AUDIT_REPORT.md`; what to build is in `DESIGN_SPEC.md`. Frontend files only (`frontend/**`); backend problems go to `docs/backend-issues/`.

| Phase | Box | Goal |
|---|---|---|
| 0 | 0:15 | Baseline and safety |
| 1 | 1:00 | Foundation: tokens, fonts, themes, native controls |
| 2 | 0:50 | Data layer, formatters, safe writes |
| 3 | 1:00 | Shared UI kit with a gallery |
| 4 | 0:45 | Shell, navigation, routes, boundaries |
| 5 | 2:45 | The nine pages |
| 6 | 0:40 | QA, tests, reviews, hardening |
| 7 | 0:20 | Final report |
| Stretch | rest | Only if more than 45 minutes remain |

**Cut order if time runs short** (cut from the bottom): stretch tasks, P9 Knowledge and Simulation sections (leave them as `UnavailableState` stubs), P7 sample-data mode, P6 detail drawers, P3 Website and Identity tabs. Never cut: tokens, themes, shell, formatters, error layer, idempotency, P1, P2, P3, P4, P5, P8, the reviews, the final report.

## Phase 0: baseline and safety (0:15)
- **T0-1 Preflight.** Branch `frontend-overhaul`, servers up (`/start-servers`), demo sign-in works. *Done when:* `bash docs/frontend-overhaul/scripts/dev-status.sh` shows both OK and `/login` shows the demo button.
- **T0-2 Baseline.** Run `npm test`, `npm run format:check`, `npm run build` in `frontend/`; record the results. The baseline screenshots and the automatic check report of the **old** UI already exist in `~/bizora-shots/baseline/` (46 shots plus `report.json`, taken before the overhaul); do not regenerate them, read `report.json` and note the numbers. *Done when:* PROGRESS.md lists the gate results and the baseline folder.
- **T0-3 Remove the hard-coded password** in `frontend/scripts/take_browser_tour.js` (lines 28-29): read `BIZORA_E2E_USERNAME` and `BIZORA_E2E_PASSWORD` from the environment and fail with a clear message when missing. *Done when:* `git grep -n "DemoPass"` finds nothing in `frontend/`.

## Phase 1: foundation (1:00)
- **T1-1 Tokens.** Copy `docs/frontend-overhaul/assets/tokens.css` to `frontend/src/styles/tokens.css`; import it first in `layout.js`. Split `globals.css` into `base.css`, `layout.css`, `components.css` keeping the cascade order. Replace **every** raw colour with a token using the mapping table in `AUDIT_REPORT.md` section 4.6; delete `--accent`, violet and indigo.
  *Done when:* a grep for `#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(` in `frontend/src` finds matches only in `styles/tokens.css`; the app still renders; screenshots of login and overview (light) taken.
- **T1-2 Fonts and type scale.** `next/font/google` for Plus Jakarta Sans (600, 700), Inter (400, 500, 600), JetBrains Mono (400, 500), Noto Sans Bengali (400, 600, subset bengali); attach the CSS variables from `tokens.css` to `<html>`. Apply the type scale and 1.43 body line-height, spec tracking, tabular numerals on numeric cells, mono for IDs and codes; remove weights 530/650/750.
  *Done when:* the browser's computed font for body text is Inter, for page titles Plus Jakarta Sans, for IDs JetBrains Mono (check in dev tools); no request goes to a font CDN (network tab).
- **T1-3 Themes.** Dark theme from the tokens (`[data-theme]` plus system preference), `color-scheme` set, `ThemeToggle` (stores only "light" or "dark"), no flash on load (set the attribute in a small inline script or via cookie read in `layout.js`; follow the Next docs).
  *Done when:* toggling switches every visible surface; both themes screenshot cleanly for login and overview; scrollbars and native controls follow the theme.
- **T1-4 Native controls and states.** Style `input`, `select`, `option`, `textarea`, checkbox, radio, date inputs, placeholders, autofill, disabled, invalid and focus in both themes (`AUDIT_REPORT.md` section 4.3). Focus ring 2 px with 2 px offset everywhere, the rail uses `--color-focus-on-nav`. Table rows get a visible hover. `scroll-behavior: smooth` only under `prefers-reduced-motion: no-preference`. Controls 36 px high (44 px on `pointer: coarse`).
  *Done when:* open a real `select` in both themes and check the option list is themed; disabled login inputs look disabled; Tab through the login and overview pages and the ring is visible on every stop including the rail.
- **T1-5 Foundation review.** Run `/design-review` on login, workspace and overview in both themes, fix findings. *Done when:* verdict SHIP or only lows remain.

## Phase 2: data layer and safe writes (0:50)
- **T2-1 Formatters** in `src/lib/format/` (`money`, `dateTime`, `date`, `relativeTime`, `duration`, `percent`, `enumLabel`, `missing`, `stripUntrusted`, status tone by exact code incl. INACTIVE, RETURNED, REFUNDED, SENT, MISSED, BUSY, CLOSED) with unit tests (null, `UNAVAILABLE`, rounding, time zones, `<untrusted_customer_data>` wrapper). Keep `format.js` exports working as shims. *Done when:* tests pass and `INACTIVE` maps to a neutral tone.
- **T2-2 API client.** `src/lib/api/` with `ApiError {status, code, detail, fieldErrors, raw}`, an error normaliser for all backend shapes (`{code,detail}`, `{detail}`, `{error}`, DRF field dict, bare list, `{query}`/`{unknown}`, HTML 500), 403-without-session handling (redirect to `/login?next=` with a same-site relative path only), CSRF refetch-and-retry once, a request timeout, `React.cache`d `getSession`. Keep `clientApi.js` and `serverApi.js` as shims. *Done when:* unit tests cover every error shape and the 403 flow; a deliberately expired session in the browser sends you to login and back.
- **T2-3 Safe writes.** `idempotency.js` (works on non-secure origins), `useActionForm` (busy flag, ApiError, field errors, one idempotency key per intent reused on retry and rotated on success or payload change, `409` reload flow), applied to refunds, notes, messages, callbacks and creates. External ids that embed the key must stay stable across retries. *Done when:* a test shows two submits of the same payload send the same key; a simulated 409 refreshes the record and keeps the inputs.
- **T2-4 Resource config.** `src/lib/domain/resources.js`: for each of the 32 resources: title field, columns (with type: text, money, datetime, status, entity link, mono), filters (with enum options), whether `q` is supported (18 return 400), link target, workspace and tab. Per-resource query allow-list so unknown keys are never sent. *Done when:* every resource renders a meaningful row (name or number, amount where relevant, date, status) and no row says "Record #id" when a name exists.

## Phase 3: shared UI kit (1:00)
- **T3-1 Form basics:** Button (primary, secondary, ghost, danger; sm, md; loading), IconButton, Field, Input, Select, Textarea, Checkbox, MoneyField, DateTimeField.
- **T3-2 Feedback and status:** Banner (info, success, warning, danger, with icons), StatusChip and SeverityChip (icon and label), ConfidenceMeter, Skeleton, EmptyState, UnavailableState, SimulatedBadge, KpiTile, Toast.
- **T3-3 Overlays and navigation:** Tabs (path-segment links), Drawer (right, focus trap, Escape, scrim, `role="dialog"`), Dialog and ConfirmDialog (native `<dialog>` is fine), Pagination, FilterBar, PageHeader.
- **T3-4 DataTable:** typed columns, sticky header, right-aligned mono numerics, density toggle, empty and loading states, pagination footer (`1–25 of 1,284`), row click opens a drawer (`?open=resource:id`), scroll wrapper focusable and labelled, `UntrustedText` cell.
- **T3-5 Evidence and time:** Timeline (the evidence thread: thin line, small nodes), EvidencePanel, CopyableCode.
- **T3-6 Gallery.** A development-only page (404 in production) at `/business/[id]/ui-kit` showing every component in every state, both themes. *Phase done when:* the gallery looks right at 1440 and 390 px in light and dark, `/design-review` of the gallery is SHIP, `npm test` and `npm run build` pass. Commit components in small commits (one family per commit).

## Phase 4: shell, navigation, routes, boundaries (0:45)
- **T4-1 Shared layout.** `business/[businessId]/layout.js` fetches the session once, finds the business and role, renders the shell: rail (256 px, collapsible to 72 px, drawer below 1024 px with `inert` when closed, `role="dialog"` semantics), sticky 56 px top bar (business switcher that does not truncate, search, theme toggle, user menu with sign out), rail groups and items from `DESIGN_SPEC.md` section 3, role-based hiding, `aria-current="page"` with prefix matching. `/workspace` gets sign-out too.
- **T4-2 Boundaries and metadata.** `loading.js` (skeleton), `error.js`, `not-found.js`, `global-error.js` (read the Next docs for this version), titles via route metadata.
- **T4-3 Route skeleton.** Create the nine-workspace route tree with tab layouts (`DESIGN_SPEC.md` section 3), default-tab redirects, and **redirects from every old section route** (`AUDIT_REPORT.md` section 6). Pages can be thin at this point (header and tab bar); content comes in Phase 5. Update the unit and e2e tests that mention changed routes in the same commit.
  *Phase done when:* every rail item opens a page with the right tab bar; old URLs redirect; `npm test` passes; `npm run build` passes; `/design-review` of the shell is SHIP.

## Phase 5: the nine pages (2:45)
Use `/page-overhaul <id>` for each. Order and boxes: **P1 (0:15), P2 (0:25), P4 (0:35), P3 (0:30), P5 (0:35), P8 (0:15), P7 (0:25), P6 (0:15), P9 (0:30)** (this adds up to a little over the phase box; P6 and P9 are the first to be trimmed). Page content, endpoints and states are in `DESIGN_SPEC.md` section 4. Common acceptance for every page:
real columns and formatted values; no raw JSON, raw ISO date or "Record #id" title; all states (loading, empty, error with Retry, "Not connected", role-disabled with tooltip, 409 reload, session expiry); honest wording from `00-project-law.md`; keyboard path complete; desktop and 390 px screenshots in light and dark; console clean; tests for new pure helpers; backend problems logged.
- **T5-P1 Sign-in and business choice.** Restyle; `next` support (same-site relative only); disabled state looks disabled; business list with role chip; one business opens directly; sign-out on `/workspace`; keep the demo button and its tests.
- **T5-P2 Overview.** Real canonical-count tiles and recent activity from D8; KPI tiles as `UnavailableState` with the backend reason; trends and health tabs; activity feed with domain filter chips; no zeros for missing data.
- **T5-P4 Commerce.** Orders (drawer, legal-transition status control with reason and `expected_status`), Payments and refunds (refund dialog, financial timeline switch), Deliveries (tracking timeline, "Prepared — not executed" panels), Products (drawer, variants, assess before create). Replace the JSON create textarea with typed forms for orders, payments, products only if time allows (stretch S1); otherwise keep it but behind an "Advanced" disclosure.
- **T5-P3 Customers.** List with real names; 360 view with tabs and timeline; identities panel; context graph from `graph-context`; open issues block; "AI customer context" as `UnavailableState`; status change dialog.
- **T5-P5 Support.** Inbox (three panes, thread bubbles, notes, "Saved — not sent" composer, AI helper blocks), assign and handover dialogs, queue with capability tiles, calls with transcript and callback dialog.
- **T5-P8 AI.** Assistant with progress state and grounding list; recommendations and actions with the review flow (busy state, result shown after approval, note length rule); "Execution is simulated." banner; audit as `UnavailableState`.
- **T5-P7 Intelligence.** Facts and issues (real E12 issues, empty state), context graph tab (real one-hop data, legend by shape and icon, no colour-only meaning), metrics and pipeline as `UnavailableState`; build adapters that return `UNAVAILABLE` now and switch on when endpoints appear; the Evidence drawer built and covered by a fixture-based test. **Optional last step (off by default):** the "Sample data (SIMULATED)" switch described in the spec.
- **T5-P6 Growth.** Campaigns (table, drawer with two small charts, conversions "Platform-reported", AI explain), Website (tables, visitor journey drawer, seven `UnavailableState` panels).
- **T5-P9 Admin.** Identity (tabs, dialogs, dry-run card, "Blocked by design"), Integrations (health, connections with Test, syncs, failed records, webhooks, freshness; "Attempt recorded" wording; confirm dialogs), Configuration (sections, version chip, 409 banner, references only, diffs only), Knowledge and Simulation as `UnavailableState` layouts.
*Phase done when:* every page above meets the common acceptance, `npm test` and `npm run build` pass, and `/design-review` over all nine pages leaves no high findings.

## Phase 6: QA, tests, reviews, hardening (0:40)
- **T6-1 Responsive and themes.** Walk every page at 1440, 1024 and 390 px in light and dark; fix overflow, clipped selects, tiny targets.
- **T6-2 Accessibility.** Keyboard-only pass on every page (Tab order, Escape closes overlays, focus returns, no traps), labels on every control, one `h1` per page, landmarks, a computed contrast check of every colour pair you introduced, reduced-motion check.
- **T6-3 Tests.** Update the Playwright specs to the new routes and labels (they must still skip cleanly when `BIZORA_E2E_*` is unset, and say so loudly); add unit tests for the API client, formatters, idempotency, resource config, status tones; add a test that TRANSITIONS in the UI match the documented order and payment transitions. Run `python tests/run_full_stack.py` only if `.venv` and Chrome exist; otherwise record that e2e was not run.
- **T6-4 Reviews.** `/code-review`, `/security-review`, `/architect-review` and a final `/design-review`; fix every critical, high and medium finding.
- **T6-5 Gates.** `npm test`, `npm run format:check`, `npm run build` all green; `git grep -n "dangerouslySetInnerHTML"` empty; no credential strings in tracked files; `npm audit` result recorded; `node docs/frontend-overhaul/scripts/verify-pages.mjs --strict --label final --theme light,dark` over every page of the nine workspaces (all tabs) at both sizes reports **0 issues** (or each remaining one is explained in PROGRESS.md).

## Phase 7: final report (0:20)
- **T7-1** Write `FINAL_REPORT.md` (per page: before and after, screenshot names; gates; what is still rough; backend issues per domain with counts and the five most important; how to run the app). Update `docs/backend-issues/README.md` counts. Ensure `git status` is clean apart from ignored files and everything is committed locally. **Do not push.**

## Stretch (only with more than 45 minutes left)
- **S1 Typed forms** for creating customers, products, orders, refunds (replacing the JSON textarea), using the field rules in `docs/frontend-api-reference.md` Part A.
- **S2 Sample-data mode for P7** (SIMULATED) so the demo story (problem, evidence, graph, AI proposal, approval) can be shown.
- **S3 Command palette** (open with Ctrl or Cmd K) that jumps between pages and records.
- **S4 Visual regression baseline**: a script that takes the standard screenshots and diffs them.
