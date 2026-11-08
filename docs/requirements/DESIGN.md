# Bizora UI Design System — Clean Teal

> **Document:** `design.md`  
> **Version:** 1.0  
> **Date:** 7 November 2026  
> **Product:** Bizora Django backend and operational UI  
> **Design direction:** Clean Teal — calm, trustworthy, data-dense enterprise SaaS  
> **Status:** Proposed UI design specification. This is a design target, **not** a statement that every screen or API is implemented.

---

## 1. Design goals

Build a polished, practical, accessible multi-business operations interface with:

- **Clarity first:** dense business data organized into readable cards, tables, and drill-down views.
- **Operational trust:** distinguish actual records, generated suggestions, simulations, unavailable services, and pending actions.
- **Fast workflows:** persistent business context, quick search, logical filters, and state-appropriate actions.
- **Consistent hierarchy:** dark-teal navigation, soft-mint canvas, white content surfaces, clear typography.
- **Safe interaction:** human review for AI proposals; never imply that saving a record sends a message, places a call, ships an order, or executes a provider action.
- **Responsive behavior:** desktop-first for operational density, fully usable on tablet/mobile.

### Product truth constraints

This design must honor the as-built SRS:

1. The authenticated operations UI is mounted at `/ops/`; core APIs are mounted at `/api/` and `/api/v1/`.
2. Business Intelligence, Business Graph, Configuration, Observability, and Overview *separate API modules* are currently **not mounted**. Never make their full APIs appear live just because module code exists. The limited core overview and graph-context projections are distinct.
3. Current provider execution depends on trusted adapters. The UI records pending/internal operations and must not claim external delivery or completion without confirmed provider evidence.
4. AI advice is non-authoritative. Action proposals require explicit human review; real execution requires an executor.
5. Tenant scope, active membership, and roles determine data and actions. Do not display unauthorized controls.
6. Dashboard values shown in mockups are **illustrative**. Production figures must come from real authorized service responses; never fabricate KPI data.

---

## 2. Visual identity

### 2.1 Primary color palette

| Token | Hex | Usage |
| --- | --- | --- |
| `--color-sidebar` | `#115E59` | Main desktop sidebar, primary brand field |
| `--color-primary` | `#0F766E` | Primary buttons, active controls, focusable links; accessible on white |
| `--color-primary-hover` | `#115E59` | Primary hover/pressed emphasis |
| `--color-accent` | `#0D9488` | Charts, accent strokes, larger non-text surfaces |
| `--color-mint` | `#CCFBF1` | Icon backgrounds, subtle highlights |
| `--color-background` | `#F0FDFA` | App page canvas |
| `--color-surface` | `#FFFFFF` | Cards, tables, dialogs, popovers |
| `--color-surface-muted` | `#F8FAFC` | Table hover/alternate section |
| `--color-heading` | `#134E4A` | Primary headings and strong text |
| `--color-text` | `#1E293B` | Body text |
| `--color-muted` | `#475569` | Descriptive text and metadata |
| `--color-border` | `#D5EBE7` | Card borders, separators |
| `--color-border-strong` | `#A7DCD3` | Strong dividers and interactive borders |
| `--color-white` | `#FFFFFF` | Inverted text and card surfaces |

**Accessibility note:** The brighter teal `#0D9488` is excellent for decoration and charts but should **not** be used with small white text. Prefer `#0F766E` or darker for primary button backgrounds and standard-size linked text. Target WCAG 2.2 AA contrast.

### 2.2 Semantic status colors

Never indicate status by color alone. Pair color with a **text label**, and optionally an icon.

| Meaning | Foreground | Soft background | Example label |
| --- | --- | --- | --- |
| Success / Implemented | `#166534` | `#DCFCE7` | `Implemented`, `Paid`, `Healthy` |
| Warning / Partial / Pending | `#92400E` | `#FEF3C7` | `Partial`, `Pending`, `Needs review` |
| Danger / Blocked / Failed | `#991B1B` | `#FEE2E2` | `Blocked`, `Failed` |
| Unavailable / Missing adapter | `#475569` | `#F1F5F9` | `Unavailable` |
| Not mounted / Not exposed | `#3730A3` | `#E0E7FF` | `Not mounted` |
| Informational / Draft | `#1D4ED8` | `#DBEAFE` | `Draft`, `Internal only` |
| AI-generated / Advisory | `#6D28D9` | `#EDE9FE` | `AI suggestion` |

Do **not** collapse `Unavailable`, `Not mounted`, `Partial`, and `Blocked` into a single generic error state. They describe different technical and product conditions.

### 2.3 Chart palette

Use these in order when distinguishing multiple series:

`#0F766E` (deep teal), `#2563EB` (blue), `#7C3AED` (violet), `#C2410C` (orange), `#64748B` (slate).

- Revenue line: `#0D9488` stroke with a faint `#CCFBF1` area fill.
- Grid: `#DCEFEA` with low visual weight.
- Axis labels: `#475569`; legends include names and/or symbols.
- Offer exact values in tooltips **and** a summary table when feasible.
- Never imply a real trend from incomplete or unavailable data.

---

## 3. Typography

**Recommended font:** `Inter`, with system-font fallback. Support Bengali text with a suitable Unicode fallback such as `Noto Sans Bengali` if localized content is introduced. Avoid using multiple decorative font families.

| Role | Desktop | Mobile | Weight | Color |
| --- | --- | --- | --- | --- |
| Page title | 28px / 36px | 24px / 32px | 700 | Heading |
| Section title | 20px / 28px | 18px / 26px | 600 | Heading |
| Card heading | 16px / 24px | 16px / 24px | 600 | Heading |
| Body / form label | 14px / 22px | 14px / 22px | 400–500 | Text |
| Data table | 13–14px / 20px | 13–14px / 20px | 400–500 | Text |
| KPI value | 26–30px / 36px | 24px / 32px | 700 | Heading |
| Secondary metadata | 12px / 18px | 12px / 18px | 400 | Muted |

Use tabular numerals for dates, prices, counts, IDs, and metrics. Never make crucial operational status dependent on tiny text.

---

## 4. Spacing, shape, and elevation

- **Spacing scale:** `4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48px`.
- **Card padding:** 20–24px desktop; 16px mobile.
- **Card gap:** 16px; major section gap 24px.
- **Sidebar width:** 248–264px expanded; optional 72px icon-only collapse on desktop.
- **Top bar height:** about 64px.
- **Content max-width:** 1600px; content padding 24px desktop, 16px tablet/mobile.
- **Button height:** 40px regular, 44px for primary mobile actions.
- **Input height:** 40–44px.
- **Card radius:** 12px; **button/input radius:** 8px; **pill radius:** 999px.
- **Border:** typically 1px solid `#D5EBE7`.
- **Shadow:** subtle (`0 2px 8px rgba(19, 78, 74, 0.05)`); prioritize borders over heavy shadows.

Avoid large gradient blocks, glassmorphism, unnecessary animations, and high-saturation surfaces throughout the dashboard.

---

## 5. Application shell and information architecture

### 5.1 Desktop wireframe

```text
┌──────────────────────┬─────────────────────────────────────────────────────────────┐
│ [icon] bizora        │  [Business selector] [Search................] [Bell] [User]  │
│                      ├─────────────────────────────────────────────────────────────┤
│ WORKSPACE            │  Dashboard                                      [Date range]│
│ ▌ Overview           │  Business overview                                         │
│   Customers          │                                                             │
│   Orders             │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐│
│   Support            │  │ Revenue    │ │ Orders     │ │ Customers  │ │ Open cases││
│   Products           │  └────────────┘ └────────────┘ └────────────┘ └───────────┘│
│   ...                │                                                             │
│                      │  ┌──────────────────────────────────────┐ ┌────────────────┐│
│                      │  │ Revenue / activity trend             │ │ Support queue  ││
│                      │  │                                      │ │ snapshot       ││
│                      │  └──────────────────────────────────────┘ └────────────────┘│
│                      │                                                             │
│                      │  ┌─────────────────────────────────────────────────────────┐│
│                      │  │ Recent orders / customer activity table                 ││
│                      │  └─────────────────────────────────────────────────────────┘│
│                      │                                                             │
│ [Profile / Help]     │  [AI suggestions — advisory, review required]              │
└──────────────────────┴─────────────────────────────────────────────────────────────┘
```

### 5.2 Sidebar

- Background `#115E59`, white brand label, muted-mint inactive icons/text.
- Selected nav row background `#0F766E` (use a subtle contrasting inset marker or clearly outlined selection); do not depend on hover alone.
- Group headings are small, uppercase, and visually secondary.
- Display **only accessible, mounted routes** in primary navigation.
- Potential groups: `Workspace`, `Business Data`, `Operations`, `Assistance`, `Administration`.
- Example labels drawn from actual Bizora domains: Overview, Customers, Orders, Products, Support, Campaigns, Website, Shipments, Calls, Identity Review, AI Assistant. **Map labels to the existing operations UI before implementation**; the SRS mentions thirteen areas but does not enumerate their exact menu labels.
- **Do not** create functional links to the separate BI, Graph, Configuration, Observability, or Monitoring API routes until those route trees are mounted and authorization is reconciled. An authorized internal capability notice may say `Not mounted` instead of providing a dead link.

### 5.3 Top bar

Left-to-right: current business selector, global search (only over authorized records), optional current date/window context, notifications, user menu.

- Switching business updates all data, filters, context, and requests.
- Never retain stale records from another tenant in the visible view.
- Provide clear active business label and user role where relevant.
- Notifications link only to reachable, authorized items.

### 5.4 Main dashboard layout

1. **Page header:** title, subtitle, optional time window and export (only when implemented).
2. **KPI row:** revenue, orders, customers, open support cases. Each card displays a value, timeframe, source/status, and a comparison only if data supports it.
3. **Activity chart:** available real data, visible axis and period label, accessible alternative.
4. **Operations snapshot:** queue workload, callbacks, attention-required records.
5. **Recent records:** actionable, filterable table with clearly labeled status chips.
6. **AI advisory block:** a teal/mint or lightly violet-tinted card for suggestions requiring human review; do not present advice as established fact.

If BI data is not currently available through an authorized mounted service, show **“Analytics unavailable”** and a short, accurate reason. Never fill absent analytics with demo data in production.

---

## 6. Responsive rules

| Viewport | Shell | Cards and table behavior |
| --- | --- | --- |
| `>= 1280px` | Expanded fixed/sticky left sidebar; content on right | KPI cards 4-up; chart + operations panel; full table |
| `1024–1279px` | Collapsible sidebar | KPI cards 2-up or 4-up depending on available width |
| `768–1023px` | Compact navigation/drawer | KPI cards 2-up; charts stacked; tables horizontally scroll with clear cue |
| `< 768px` | Top header and accessible nav drawer | KPIs 1-up or 2-up; charts full width; important table fields become stacked record cards |

- No horizontal page overflow at 320px; localized overflow may be used only for dense data tables.
- Mobile controls need approximately 44×44px tap targets.
- Drawer can be closed with Escape, has focus trapping, and returns focus to its trigger.
- Keep a persistent visible business context on small screens.

---

## 7. Core components

### 7.1 Buttons

- **Primary:** `#0F766E` background, white text; for the single dominant action in a section.
- **Secondary:** white or mint surface, teal border/text; for supporting actions.
- **Tertiary:** text/icon button, underline or stronger emphasis on focus.
- **Danger:** muted red with confirmation for destructive or high-impact changes.
- **Disabled:** visibly disabled, not clickable; include a reason in helper text when useful.
- Every async operation must show loading and an explicit success/failure result; never assume a provider operation succeeded.

### 7.2 Cards

White background, 1px pale border, 12px radius, restrained elevation. A typical card contains a title, value/content, time scope, status or secondary action, and optional source link.

### 7.3 Forms

- Labels above inputs, optional help text below, required marker visible.
- Error message beside the relevant field; also provide a form-level error summary when needed.
- Money fields include currency and precision constraints; statuses use constrained selectors rather than free text.
- Use validated date/time controls and clearly indicate business-local timezone when scheduling callbacks.
- Show tenant-context and source-reference metadata where relevant.
- Destructive identity operations must not be enabled merely because a merge dry-run exists.

### 7.4 Tables and lists

- White surface with subtle dividers; sticky header when many rows.
- Column headings, sorting affordance only if implemented, server-backed pagination.
- Filter/search area above the table with active filter chips and a clear/reset action.
- Use row-level actions appropriate to current state and role; hide or disable unauthorized actions.
- IDs should be copyable, with readable labels beside them.
- Empty, loading, error, filtered-empty, and access-denied states are distinct.

### 7.5 Status chips

Rounded label pills using Section 2.2 tokens. Text must spell out the meaning: e.g. `Pending approval`, `Unavailable — adapter missing`, `Not mounted`, `Blocked — preservation decision`.

### 7.6 Dialogs / side panels

- Use a right drawer for record detail and routine editing when it does not harm context.
- Use a centered confirmation dialog for destructive/high-impact decisions.
- Require reason/note fields for decisions wherever the underlying workflow requires them.
- Preserve server validation messages, do not silently discard them.

### 7.7 Toasts and alerts

- Toasts acknowledge ordinary internal actions: `Saved as pending draft` rather than `Message sent`.
- Persistent banners convey service unavailability, reconciliation requirements, or blocked functionality.
- Errors provide a retry option only when the operation is safe to retry.

---

## 8. Screen-specific guidelines

### Overview

Keep the page calm and scannable: top KPI cards, one primary timeline, operational summaries, and recent records. Never pretend the separately unmounted Overview & Monitoring API is live. Distinguish the mounted operations overview from that optional module.

### Customers and Customer 360

Use a summary header and tabs or stacked sections: profile, contacts, timeline, orders, conversations, source identities, and evidence where available. Tenant-safe links only. Mark data origin and uncertainty.

### Orders, payments, refunds

Make monetary fields, status, and outstanding/reconciliation state unambiguous. Separate internal status changes from external payment confirmation. Never enable invalid transitions or refunds exceeding capacity.

### Support queue and conversations

Queue list + detail panel on desktop; stacked views on mobile. Show assignee, owner (human/AI), priority, latest message, pending outbound drafts, and callbacks. Use `Draft / Pending — not delivered` labels for UI-created replies or media.

### Identity and merge review

Show evidence, sources, link history, confidence interpretation, conflicts, and an impact inventory. The merge **dry-run** should be labeled `Plan only — no records merged`. Final consolidation control stays absent/blocked until downstream preservation guarantees exist.

### AI assistant and action review

Visually separate **AI suggestion**, **human-approved**, **simulated execution**, **real execution confirmed**, and **execution failed**. Show source/evidence and approval actor/reason where available. `Approve` never means `provider action completed`.

### Integrations / observability / configuration / BI / graph / monitoring

If product navigation eventually exposes these modules, first mount routes, reconcile authorization, and verify service availability. Before that, prefer a clearly worded capability card (`Not mounted` / `Unavailable`) only when its placement makes sense and is authorized.

---

## 9. Interaction and state model

All data-bearing components must represent these states explicitly:

- `loading`: skeleton or inline spinner, stable layout.
- `ready`: real authorized data.
- `empty`: no records exist.
- `filtered_empty`: no records match filters.
- `error`: operation failed; show safe explanation and recovery option.
- `forbidden`: insufficient permission; no sensitive data leak.
- `unavailable`: required service/adapter is absent.
- `not_mounted`: module URL is not exposed.
- `partial`: some capability works; clarify missing dependency.
- `blocked`: explicit policy/preservation gate prevents proceeding.

### Action-state language

| Operation | Correct success language | Avoid |
| --- | --- | --- |
| Internal support reply | `Reply saved as pending` | `Message delivered` |
| Outbound request preparation | `Request prepared; executor unavailable` | `Request sent` |
| AI approval | `Proposal approved for execution` | `Action completed` |
| Merge dry-run | `Impact plan generated` | `Customers merged` |
| Simulated adapter response | `Simulation completed` | `Live sync succeeded` |

---

## 10. Accessibility and usability

- Target **WCAG 2.2 AA** for all new and revised UI.
- Normal text contrast at least **4.5:1**, large text/non-text UI indicators at least **3:1** as applicable.
- Visible keyboard focus ring (`2px` or stronger, with offset); no keyboard traps.
- Semantic page headings, labels, table headers, and landmark navigation.
- All menu items, dropdowns, tabs, dialogs, filters, and data-table actions keyboard operable.
- Do not encode meaning with color alone; pair with text, shapes, and icons.
- Use `aria-live` appropriately for non-disruptive success/error feedback.
- Honor reduced-motion preferences; animation optional and brief (typically 120–180ms).
- Do not use placeholder text as the only label.
- Format currency, dates, and timezones consistently and contextually.

---

## 11. CSS starter tokens

```css
:root {
  --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;

  --color-sidebar: #115e59;
  --color-primary: #0f766e;
  --color-primary-hover: #115e59;
  --color-accent: #0d9488;
  --color-mint: #ccfbf1;
  --color-background: #f0fdfa;
  --color-surface: #ffffff;
  --color-surface-muted: #f8fafc;
  --color-heading: #134e4a;
  --color-text: #1e293b;
  --color-muted: #475569;
  --color-border: #d5ebe7;
  --color-border-strong: #a7dcd3;

  --color-success: #166534;
  --color-success-bg: #dcfce7;
  --color-warning: #92400e;
  --color-warning-bg: #fef3c7;
  --color-danger: #991b1b;
  --color-danger-bg: #fee2e2;
  --color-unavailable: #475569;
  --color-unavailable-bg: #f1f5f9;
  --color-not-mounted: #3730a3;
  --color-not-mounted-bg: #e0e7ff;
  --color-ai: #6d28d9;
  --color-ai-bg: #ede9fe;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  --radius-input: 8px;
  --radius-card: 12px;
  --radius-pill: 999px;
  --shadow-card: 0 2px 8px rgba(19, 78, 74, 0.05);
  --sidebar-width: 256px;
  --topbar-height: 64px;
}

body {
  background: var(--color-background);
  color: var(--color-text);
  font-family: var(--font-sans);
}

.app-sidebar {
  background: var(--color-sidebar);
  color: #ffffff;
}

.app-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}

.btn-primary {
  background: var(--color-primary);
  color: #ffffff;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-input);
  min-height: 40px;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}

:where(button, a, input, select, textarea, [tabindex]):focus-visible {
  outline: 3px solid #2563eb;
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Illustrative component recipe

```text
DashboardCard
  surface: white
  border: pale teal
  padding: 20px
  radius: 12px
  header: label + optional icon
  main: real metric value or explicit unavailable state
  footer: timeframe / source / evidence link

StatusBadge
  label: required
  semantic variant: success | warning | danger | unavailable | not-mounted | info | ai
  icon: optional, not sole source of meaning
```

---

## 12. Implementation guidance for Django

- Use a shared base template for `/ops/` with consistent sidebar, business selector, topbar, toasts, and layout slots.
- Introduce CSS variables centrally; avoid scattered per-template hard-coded colors.
- Build reusable template partials for `card`, `badge`, `table`, `empty_state`, `error_state`, `confirmation_dialog`, and `form_field`.
- Pass effective role, mounted capabilities, and business context from trusted server logic; do **not** trust client-supplied flags for authorization.
- Reuse existing DRF and domain APIs. Do not add client-side endpoints to unmounted modules or bypass membership checks.
- Use POST + CSRF for mutations; keep provider operations separate from internal-save flows.
- Persist table filters in query parameters when practical without leaking private information across business switches.
- Use loading/disabled/confirmation states to avoid duplicate submissions and accidental high-impact actions.
- Verify generated links against actual `bizora/urls.py`, `app/urls.py`, and `app/operations_urls.py` before shipping.

---

## 13. UI acceptance checklist

- [ ] The application shell visibly matches the Clean Teal palette.
- [ ] Page, section, card, field, and data-table hierarchy is consistent.
- [ ] All text and interactive controls meet required contrast and focus visibility.
- [ ] Mobile drawer, keyboard navigation, dialogs, and form error states work.
- [ ] Every screen shows the active business; cross-business stale data never appears.
- [ ] User roles and server-side permission gates control actions.
- [ ] Unmounted modules are not advertised as functioning REST screens.
- [ ] Unavailable, partial, blocked, not-mounted, and simulated are distinct states.
- [ ] No mock KPI values appear in a production view as though they were real.
- [ ] AI suggestions remain clearly advisory and require explicit review.
- [ ] UI-created replies and outbound requests never claim provider delivery absent evidence.
- [ ] Identity merge dry-runs are accurately described as planning, not physical merges.
- [ ] Source, timeframe, and currency are visible for important metrics.
- [ ] CSRF, tenant scoping, audit context, and safe transition handling remain intact.

---

## 14. Reference visual summary

**Look:** deep-teal sidebar (`#115E59`) + off-white/mint canvas (`#F0FDFA`) + white cards + teal action controls (`#0F766E`) + mint icon highlights (`#CCFBF1`).  
**Mood:** modern, approachable, highly legible, professional enterprise operations.  
**Avoid:** purple-first branding, neon-heavy charts, crowded gradients, fictitious live analytics, and ambiguous execution statuses.  
**North star:** **“One coherent workspace, clear facts, safe actions.”**