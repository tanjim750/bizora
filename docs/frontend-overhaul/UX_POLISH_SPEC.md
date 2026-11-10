# UX polish spec: libraries, sidebar, layout formation, responsive (2026-11-10)

Owner decision D-F29 (2026-11-10, after seeing the first result): finish the whole frontend; apply the formal theme (task T1-6); use good libraries; make the sidebar clearly better; keep every page clean and well formed on phone, tablet and desktop. This file is the source of truth for tasks T3-7, T4-4 and T4-5 and for the "definition of done" of every Phase 5 page. Where it contradicts an older sentence in `MASTER_PROMPT.md`, `DESIGN_SPEC.md` or a rule, this file wins (those sentences were updated on the same day).

## 1. Libraries

The in-house, token-based UI kit stays the design system. Libraries complement it; they never replace it, and pages never import them directly (only wrapper components in `src/components/ui/`).

| Library | Exact version | Use |
|---|---|---|
| `recharts` | 3.10.1 | Every chart, through wrappers in `src/components/ui/charts/` (T3-7). Colours only from `--chart-*` tokens. |
| `@radix-ui/react-tooltip` | 1.4.1 | Collapsed-rail labels, reasons on disabled controls, full text of truncated names. |
| `@radix-ui/react-dropdown-menu` | 2.2.1 | User menu, row action menus, any menu of actions. |
| `@radix-ui/react-popover` | 1.3.1 | Filter popovers, date range, small forms attached to a button. |
| `clsx` | 2.1.1 | Building class names. |
| `zod` | 4.6.7 | Optional: validating form payloads and normalising API payloads at the boundary, only where it replaces hand-written checks. |
| `cmdk` | 1.1.1 | Optional: only if it clearly improves the existing `QuickSearchDialog` (Ctrl or Cmd K). Keep the same behaviour and tests. |

All are MIT licensed and declare React 19 compatible peer ranges (checked on the registry on 2026-11-10). Install with `cd frontend && npm install --save-exact <package>@<version>`.

For every install: check `npm ls <package>`, run `npm audit --omit=dev` and make sure it adds no high or critical finding, run `npm run build`, list it in `PROGRESS.md` under "Dependencies added" (name, version, why, audit result), and commit `package.json` and `package-lock.json` together with the first code that uses it. Radix primitives are unstyled: style them only with the existing token classes. Keep motion to the budget in `.agents/rules/20-design-system.md`.

**Not allowed** (record in "Blocked / questions for the owner" if you think one is needed): Tailwind, Bootstrap, shadcn/ui, MUI, Chakra, Ant Design, styled-components, emotion (a second styling system conflicts with the token CSS and would mean rewriting about 40 finished components); framer-motion, GSAP or any animation library (the owner wants calm UI); another icon set (lucide-react stays); another chart library; Redux, Zustand, TanStack Query or any state or data library (the data layer in `src/lib/api` exists); TypeScript migration; any package not on the list above.

## 2. Sidebar (task T4-4)

Current state: `AppShell.js` with a 256 px rail, a 72 px collapsed rail and a drawer below 1024 px. The rail works but looks plain, there are two workspace controls (a card in the rail and a switcher in the top bar), the collapsed rail has no labels, and the footer text collides with the Next.js dev badge. Redesign it as follows, using only the `--color-nav-*` tokens and the formal theme.

**Structure, top to bottom**
1. Brand block, 56 px high so its bottom edge lines up with the 56 px top bar: 32 px rounded-square mark (background `--color-nav-indicator`, letter in `--color-nav-bg`) and the wordmark.
2. Workspace card (informational, not a menu): business name (one line, ellipsis, full name in a Radix Tooltip), role chip, currency. The only workspace switcher is the one in the top bar; remove the duplicate.
3. Navigation groups. Group label: 11 px, weight 600, uppercase, tracking `--tracking-overline`, colour `--color-nav-muted`, 20 px above the label and 6 px below it.
4. Spacer, then the footer: a collapse toggle, then the user card (avatar with initial, name, role) that opens a Radix DropdownMenu with Theme and Sign out. Remove the loose environment text from the footer (a small neutral "Development" label is fine in development only).

**Nav item:** 40 px high, radius 8 px, 12 px horizontal padding, 12 px gap; icon 18 px lucide with stroke width 1.75; label 14 px weight 500. States: default `--color-nav-text`; hover background `--color-nav-active-bg`; active = that background plus a 3 px bar on the left edge in `--color-nav-indicator` (radius 0 2px 2px 0), text `--color-nav-text-active`, icon in `--color-nav-indicator`, `aria-current="page"`; focus-visible ring `--color-focus-on-nav` 2 px, inset. Count badge: pill, 18 px high, 18 px minimum width, background `--color-warning`, text `--color-on-primary`, 11 px weight 600, never colour alone (the number is the meaning).

**Collapsed rail (72 px):** icons only, 44 px hit area centred; group labels become a 1 px divider (`--color-nav-active-bg`) with the same vertical rhythm; every item has a Radix Tooltip on the right (150 ms delay, label and count); workspace card shows only a circular initial; user card shows only the avatar. No text may be clipped or half visible.

**Scrolling:** the navigation area scrolls on its own (`overflow-y: auto`, thin scrollbar coloured with nav tokens); brand block and footer stay pinned.

**Widths and breakpoints:** expanded 264 px, collapsed 72 px. Below 1024 px: the rail is hidden and replaced by an off-canvas drawer. 1024 to 1279 px: collapsed by default. 1280 px and up: expanded by default. The user's choice (collapsed or expanded) is stored in `localStorage` inside try and catch and is respected at 1024 px and up.

**Mobile drawer (below 1024 px):** opened by a menu button at the left of the top bar (44 px target); width `min(86vw, 300px)`; scrim; closes on route change, on Escape and on scrim click; focus moves into the drawer, is trapped there, and returns to the menu button on close; the page behind is `inert` and does not scroll; the drawer itself scrolls if the screen is short; respects `prefers-reduced-motion`.

**Also:** set `devIndicators: false` in `frontend/next.config.mjs` (development badge only) so screenshots and the footer are not covered. Keep the existing localStorage key and the existing tests green; update tests that name changed labels.

## 3. Layout formation (clean and consistent)

- **Page template** (every page, no exceptions): `PageHeader` = breadcrumb, then title row (h1 26/600 plus meta chips), then one-line description in secondary colour, with actions aligned right (wrapping below the title on phones), then `Tabs`, then the content.
- **Content width and gutters:** centred, maximum `--content-max` (1440 px); gutter 24 px from 1024 px up, 16 px below 1024 px, 12 px below 480 px.
- **8 px grid:** gap between sections 24 px; card padding 20 px (16 px on phones); grid gap 16 px (12 px on phones); table cell padding 10 px 16 px (8 px 12 px on phones).
- **One set of layout classes** defined once in `layout.css` and used everywhere: `.grid-kpi` (`repeat(auto-fit, minmax(220px, 1fr))`, `minmax(160px, 1fr)` on phones), `.grid-2` (two equal columns, one column below 1024 px), `.grid-main-aside` (2fr and 1fr, one column below 1024 px), `.stack` (vertical rhythm). No page defines its own ad hoc grid.
- **Card anatomy:** header row (title 16/600 on the left, chips or actions on the right), optional subtitle 13 px secondary, body, optional footer. Same radius, same border, same padding everywhere.
- **Alignment:** numbers right-aligned with tabular figures; labels left-aligned; centred text only in empty and unavailable states; icons vertically centred with their text; icon sizes 16 (inline), 18 (navigation), 24 (empty states).
- **Nothing overlaps or clips:** long names get an ellipsis plus a `title` or tooltip; long ids and URLs use `overflow-wrap: anywhere`; no fixed pixel widths that can overflow a 360 px screen.
- **Stable layout:** loading skeletons have the same height as the content they replace; error and unavailable states sit inside the same card.

## 4. Responsive behaviour (tasks T4-5, T6-1 and every page)

**Test sizes (width x height):** 360x740 (small phone), 390x844 (phone), 768x1024 (tablet portrait), 1024x768 (tablet landscape), 1280x800 (laptop), 1440x900 (desktop), 1920x1080 (large screen). Both themes.

| Part | Phone, below 640 px | Tablet, 640 to 1023 px | Desktop, 1024 px and up |
|---|---|---|---|
| Navigation | off-canvas drawer | off-canvas drawer | rail (see section 2) |
| Top bar | menu button, icon-only search, theme, user avatar; no timezone text, no user name | adds timezone | full |
| `DataTable` | rows become a card list: first column as title, two or three key fields as label and value, status chip, tap opens the drawer | table in a focusable scroll wrapper, columns marked `priority: 'low'` hidden | full table, sticky header |
| `Tabs` | one row, horizontal scroll with scroll snap, the active tab scrolled into view, the next tab partly visible as the cue | same | full row |
| `FilterBar` | one "Filters" button that opens a bottom sheet; active filters stay as chips below | inline | inline |
| `Dialog` | bottom sheet: full width, rounded top corners, `max-height: 90dvh`, sticky footer with full-width stacked buttons | centred, `max-width: 560px` | same |
| `Drawer` | full width | `min(560px, 92vw)` | same |
| `Toast` | bottom, full width minus 16 px | bottom right, 380 px maximum | same |
| KPI and card grids | `.grid-kpi` with 160 px minimum | two or three columns | auto-fit |
| Forms | one column, labels above, input height 44 px, font size 16 px (prevents zoom on iOS) | one column | two columns where it helps |
| Charts | 4:3, at most four axis ticks, legend below | 16:9 | 16:9 |
| Sticky parts | top bar only; `PageHeader` scrolls away; table header sticky only inside its own wrapper | same | same |

Rules for every size: no horizontal scrolling of the page (only inside tables and tab rows); touch targets at least 44 px on coarse pointers and 36 px otherwise; text never below 12 px (13 px for table text on phones); use `dvh` units and `env(safe-area-inset-*)` for anything fixed to a screen edge; modals never taller than the screen; landscape phone must not overlap or trap content.

**Verification tooling (part of T4-5):** extend `docs/frontend-overhaul/scripts/verify-pages.mjs` with (a) a touch-target check on viewports up to 480 px wide (visible links, buttons and inputs below 40 px high, ignoring inline links inside paragraphs), (b) a minimum font size check (text below 12 px), (c) a `--matrix` flag that expands `--sizes` to the seven sizes above. Document the flags in the script header. The existing checks stay.

## 5. Definition of done for every Phase 5 page

All of the common acceptance in `PLAN.md`, plus: uses `PageHeader`, the layout classes of section 3 and the UI kit only; formal theme tokens only; charts through the chart wrappers; complete at all seven sizes in both themes (checked with `verify-pages.mjs --matrix`, 0 issues) and the screenshots at 390, 768 and 1440 were looked at and nothing overlaps, clips or looks cramped; loading, empty, error, "Not connected" and role-disabled states all present; the keyboard path works.
