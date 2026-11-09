# Bizora — Stitch prompt pack: 9 pages

Status: **draft for owner review**, 2026-11-09 (third revision). **9 workspace pages plus one design-system screen.** This replaces the
earlier 53-page plan, which was too large to finish and treated every backend module as a page.
Source of truth for what each module contains: [`frontend.md`](frontend.md) §3. Colours: `frontend.md` §2.1 (same palette as the STYLE block).

**Accuracy target: about 80–90%.** These prompts exist to visualise the features quickly. Names and lists are generic and will change
when the real frontend is built; exact contracts live in `frontend.md` and [`frontend-api-reference.md`](frontend-api-reference.md).
All names and numbers in the prompts are **sample data**.

## 0. If you are an AI reading this file: generate EVERYTHING listed here

Produce **F0**, then the **9 pages P1 to P9**, then the **two starred extra screens**. That is 12 screens in total.

1. Do not ask which page to do and do not stop after the first one.
2. Each page is **one screen** showing its default tab. The other tabs appear in the tab bar but are not drawn, unless an "extra screen" asks for them.
3. Apply the STYLE block to every screen and use the page's **Short prompt** as the brief; add the **Detail follow-up** for depth.
4. Output each screen separately (or as a file named `P#-name`): desktop 1440 px, light theme, with exactly the same rail, top bar, colours and fonts.
5. Do **not** create more pages than are listed. Do not invent features that are not in this file.
6. If you cannot finish in one reply, produce as many as you can, list what is done and what remains, and continue when the user says "continue".

Stitch cannot take a file. For Stitch use the ready-made prompts in [`frontend-stitch-batches.md`](frontend-stitch-batches.md).

## 1. The decision: nine workspaces, not fifty-three pages

A backend module is **not** a page. A page is a job a person does. Several modules share one page as tabs, and details open in drawers
and dialogs. Nine is the smallest number that does not mix unrelated jobs: fewer would put orders next to AI approvals.

| # | Page | Route | Tabs and views | Modules (frontend.md §3) |
|---|---|---|---|---|
| P1 | Sign-in and business choice | `/sign-in` | Sign-in · Choose business | M0 |
| P2 | Overview | `/b/:id/overview` | Overview · Trends · Health | M1 |
| P3 | Customers (with Customer 360) | `/b/:id/customers/:customerId?` | List + 360: Timeline · Orders and payments · Conversations and calls · Deliveries · Website and marketing · Graph · Identity | M2, part of M16 |
| P4 | Commerce | `/b/:id/commerce/:tab` | Orders · Payments and refunds · Deliveries · Products | M3, M4, M5, M11 |
| P5 | Support | `/b/:id/support/:tab` | Inbox · Queue · Calls (+ assign and handover dialogs) | M6, M7, M8, M12 |
| P6 | Growth (marketing and website) | `/b/:id/growth/:tab` | Campaigns · Website | M9, M10 |
| P7 | Intelligence (facts, graph, metrics) | `/b/:id/intelligence/:tab` | Facts and issues · Graph · Metrics and analysis · Pipeline | M13, M14 |
| P8 | AI | `/b/:id/ai/:tab` | Assistant · Recommendations and actions · Audit | M15 |
| P9 | Admin (identity, integrations, configuration) | `/b/:id/admin/:section` | Identity · Integrations · Configuration · Knowledge* · Simulation* (*design-only) | M16, M17, M18, M19, M20 |

Rules: tabs for sibling views; a right-hand drawer for the detail of a table row; a dialog for a consequential action; a "Not connected"
state wherever the data does not exist yet. Routes follow pages plus a tab segment; the per-module routes in `frontend.md` §3 become tabs.

**The demo story** (what to polish first): **P2 Overview** shows a problem → **P7 Facts and issues** shows the evidence → **P7 Graph**
shows the connections → **P8 Assistant** explains it → **P8 Recommendations and actions** lets a human approve (simulated). **P3
Customers**, **P5 Support** and **P4 Commerce** show the daily work behind it. **P6 Growth** and **P9 Admin** complete the product.

## 2. How to use this pack

1. Create **one** Stitch project called "Bizora".
2. Generate **F0** (design-system sheet and app shell). Fix it until you like it; every other screen copies it.
3. Generate the pages. Fastest: paste the **ALL 9** prompt from [`frontend-stitch-batches.md`](frontend-stitch-batches.md). If Stitch makes fewer
   screens or merges them, use the two half-batches there, or paste one page at a time (STYLE block, blank line, Short prompt).
4. Check each screen with the five questions in §3.3. Fix with one follow-up per change.
5. Add the two starred extra screens. Add other extras only if time is left.

What is and is not verified about Stitch: "one screen per prompt, list each screen, keep a design-system file, start simple then refine"
comes from third-party guides; Google's own prompting guide could not be read. No prompt here has been run in Stitch yet.

## 3. How to write a Stitch prompt (the guide)

### 3.1 The recipe: four parts, 30–110 words
1. **STYLE**: the block in §4, copied unchanged.
2. **Purpose**: one sentence, what the page is for.
3. **Regions**: the main areas in plain words, in reading order; name the tabs.
4. **One special state or action**: for example "a 'Not connected' tile" or "a confirm dialog".

### 3.2 Do and don't
| Do | Don't |
|---|---|
| Use the words people will see: button, tab and column names | Write API paths, field names, database words or code |
| Give one or two realistic sample rows | Paste long lists of values unless they are visible labels |
| Say what the main action is | Use vague praise ("beautiful", "stunning", "modern") |
| Name what is empty or "Not connected" | Put several pages in one message unless it is a batch prompt |
| Say "same navigation rail and top bar as the app-shell screen" | Introduce a colour or font that is not in the STYLE block |
| Ask for one change per follow-up | Ask for animation, gradients or illustrations |

### 3.3 The loop and the five-question check
Generate → check → one follow-up per fix → move on. After each screen ask:
1. Same navigation rail and top bar as F0?
2. Only one primary blue; no extra accent colours or gradients?
3. Numbers in a monospaced face, money shown as "BDT 1,234.00", missing data shown as "—"?
4. Every status chip has an icon and a label?
5. Nothing suggests something was sent, executed or paid when it was only saved or prepared?

### 3.4 Follow-up library (copy and paste)
```text
Use exactly the same navigation rail, top bar, colours and fonts as the app-shell screen.
```
```text
Make the table denser: 40 px rows, smaller cell padding, keep the header sticky.
```
```text
Add the empty state for this page: a short sentence and one primary action.
```
```text
Add the loading state as skeleton blocks that match this layout.
```
```text
Add a "Not connected" panel in place of the chart: dashed border, info icon, the owning area, one sentence.
```
```text
Show the same page at 390 px width: rail becomes a menu button, tables become stacked rows.
```
```text
Replace the cards with plain sections separated by thin dividers; keep cards only for clickable items.
```
```text
Remove all decoration: no gradients, no shadows beyond a 1 px border, no illustrations.
```

### 3.5 Blank template for any new feature
```text
[STYLE block]

[Purpose, one sentence: "A ___ page where users can ___."]
[Regions: "At the top ___. Below it ___. On the right ___."]
[Special state or action: "One ___ shows 'Not connected'." or "A confirm dialog appears for ___."]
```

### 3.6 What to bring back to me
Send the screenshot with the page number (for example "P7 Facts and issues"). I check it against `frontend.md`, the five questions and the design
rules, and tell you what to change. Do not ask Stitch to "make it look better"; tell it which question failed.

## 4. The design in one paragraph, and the STYLE block

Formal, calm and high-contrast. Cool-slate neutrals, **one** cobalt-blue primary, semantic colours only for status. No second accent, no
gradients, no illustrations, no emoji, no decorative animation. Text is near-black ink, never pale grey. Numbers use a monospaced face with
tabular figures. Pages are sections, tables and dividers, not boxes inside boxes. One signature detail: the **evidence thread**, a thin
vertical line with small nodes joining Data → Evidence → Fact → Issue → Recommendation. Light theme first; dark is a later toggle.

### STYLE block (paste before every page prompt)

```text
STYLE for this screen. Bizora, a formal enterprise web app for commerce businesses. Light theme, desktop 1440 px. Cool-slate neutrals with ONE cobalt-blue primary; no other accent, no gradients, no illustrations, no emoji.
Colours: canvas #F8FAFC; surface #FFFFFF; subtle surface #F1F5F9; border #E2E8F0; input border #76859B; ink text #0F172A; secondary text #334155; muted text #526278; primary #1D4ED8 (hover #1E40AF, soft fill #EFF6FF, text on soft fill #1E40AF, white label on primary); success #15803D on #F0FDF4; warning #B45309 on #FFFBEB; danger #B91C1C on #FEF2F2; info #0369A1 on #F0F9FF.
Navigation: left rail 256 px, background #0F172A, item text #CBD5E1, section labels #94A3B8, active item white on #1E293B with a 3 px #60A5FA bar; sticky top bar 56 px. Keep exactly the same rail and top bar as the app-shell screen.
Type: Plus Jakarta Sans for headings, Inter for text, JetBrains Mono for numbers, IDs and codes. Page title 28 px bold, body 14 px, table cells 13 px.
Shape: 8 px radius, 1 px borders, almost no shadow, simple 1.5 px line icons. Prefer sections, tables and dividers over cards; no cards inside cards. Every status chip has an icon and a label. Show money as "BDT 2,500.00", dates as "09 Nov 2026, 14:32", ratios as "17.0%", and missing data as "—", never 0.
```

## 5. Coverage: every feature in the 12 specifications → page

| Specification | Features → page and tab |
|---|---|
| Business data | Product P4 Products · Customer P3 · Order P4 Orders · Payment P4 Payments · Communication P5 Inbox · Customer support P5 Inbox, Queue · Marketing P6 Campaigns · Website behaviour P6 Website · Courier P4 Deliveries · Calling P5 Calls |
| Business operations | Overview P2 · Customer 360 P3 · Product, order, payment operations P4 · Unified inbox P5 · Support queue P5 · Assignment and handover P5 (dialogs) · Marketing operations P6 · Website performance P6 · Delivery operations P4 · Call operations P5 |
| Overview and monitoring | Overview and KPIs P2 · Trends P2 Trends · Active issues P2, P7 · Business health P2 Health · Recent activity P2 · Recommendations P2, P8 · Cross-domain P2 Health |
| Business intelligence | Relationships, attribution, conversion, revenue, product, campaign, customer, retention, support, website, delivery analysis, anomalies P7 Metrics and analysis · Metrics and snapshots P7 Metrics and analysis · Facts, fact evidence, issues, issue evidence P7 Facts and issues · Pipeline P7 Pipeline |
| Business graph | Nodes, edges, building, projection, traversal, query, filtering, snapshots, evidence-aware graph, all four journeys P7 Graph |
| AI intelligence | Assistant, diagnosis, context retrieval, memory retrieval, customer, product and order awareness P8 Assistant (AI blocks also on P3, P4) · Support AI P5 Inbox · Marketing assistant P6 Campaigns · Summaries P5 · Recommendations, evidence, actions, approval P8 Recommendations and actions · Audit and guardrails P8 Audit |
| Identity resolution | Canonical, external, linking, matching, anonymous linking, merge detection, conflicts, history P9 Identity (identities panel also on P3) |
| Integrations | All six categories, management, sync and webhooks P9 Integrations |
| Integration observability | Connection health, sync monitoring and history, failed records, webhooks, freshness, provider health, errors P9 Integrations |
| Business configuration | Profile, general, integration, rules, AI, knowledge, policy, monitoring configuration P9 Configuration |
| Business memory and knowledge | All 19 features P9 Knowledge (design-only) |
| Prototype simulation | All 11 features P9 Simulation (design-only) |

Not designed on purpose: nothing in the specifications is dropped. Sub-views become tabs, sections, drawers or dialogs. Each page is
one screen in Stitch (its default tab); the "extra screens" below are optional, and the two starred ones (★) are recommended.

---

## F0 · Design system sheet and app shell

If Stitch struggles with the length, send Part 1 and Part 2 as two messages.

```text
Create the Bizora design-system sheet and the empty app shell, light theme, on one tall canvas.
Part 1, the sheet: colour swatches with their hex values and role names; the type scale (display 40, page title 28, section 22, card title 18, body 14, table 13, caption 12, overline 11 uppercase with letter spacing); buttons (primary, secondary, ghost, danger; default, hover, focus ring, disabled); inputs (text, select, date range, checkbox, switch) with label above and helper text below; status chips (Success, Warning, Danger, Info, Neutral, each with icon and label); severity chips (Low, Medium, High, Critical); a compact data table with sticky header, sortable columns, right-aligned monospaced numbers and a footer "1–25 of 1,284"; a KPI tile with value, delta arrow, previous value and a tiny sparkline; a right-hand detail drawer; a confirm dialog that names the target and the effect; a toast; a skeleton loader; an empty state with one action; and the special "Not connected" state: dashed border, info icon, title "Not connected", line "Owner: Business Intelligence", one-sentence reason.
Part 2, the shell: rail groups Overview · Operations · Intelligence · Data & identity · Integrations · Settings, with the page names Overview; Inbox, Support queue, Customers, Orders, Payments, Products, Delivery, Calls, Marketing, Website; Intelligence, Graph, AI assistant, Actions, Memory & knowledge, Simulation; Identity; Integration health; Configuration. Top bar: business switcher, "Updated 14:32" freshness label, user menu. Main area empty with a page-title placeholder.
```
Check: one primary colour only; every chip has an icon; the rail matches the STYLE block.

---

## P1 · Sign-in and business choice

Route `/sign-in` · Tabs: Sign-in · Choose business · Modules: M0

**Short prompt** (after the STYLE block):
```text
Two screens. First, a clean sign-in page: a centred panel with username, password and a Sign in button, plus an error version. Second, a choose-business page: a short list of businesses, each with name, currency, timezone, the user's role (Owner or Operator) and an Open button. Nothing decorative.
```

**Detail follow-up** (optional, as a second message):
```text
Sign-in error text: 'Sign-in failed. Check your username and password.' Business rows read like 'Dhaka Fashion House · BDT · Asia/Dhaka · Owner'. No illustration, no marketing copy, no social buttons.
```

## P2 · Overview

Route `/b/:id/overview` · Tabs: Overview · Trends · Health · Modules: M1

**Short prompt** (after the STYLE block):
```text
The Overview home page with tabs Overview, Trends and Health. On the Overview tab: business name, a period selector and a compare toggle; six key-number tiles with change and sparkline (one tile shows a 'Not connected' state); a trend chart with a previous-period line; business health by area; active issues with severity and confidence; a recent activity feed; AI recommendations with approval status; and a small strip of cross-domain findings such as Marketing → Revenue.
```

**Detail follow-up** (optional, as a second message):
```text
Header: business name, 'BDT · Asia/Dhaka', period (Day, Week, Month, Rolling 7, Rolling 30), a 'Compare with previous period' toggle. Tiles: Gross revenue, Net revenue, Total orders, Average order value, Successful delivery rate, Cart abandonment rate, each with a monospaced value, change with the previous value, a sparkline and a freshness chip. Health rows: Sales, Marketing, Support, Website, Delivery as Healthy, Warning or Critical (icon and label) with an evidence link. Issues: severity chip, confidence bar, affected entity. Activity: domain filter chips. Recommendations: priority and approval status. Cross-domain strip: 'Marketing → Revenue', 'Marketing → Delivery', 'Courier → Revenue'.
```

**Extra screens** (optional; paste STYLE block, then this):

*Trends tab*
```text
Show the same page with the Trends tab selected: a large time-series chart for a chosen metric with a dashed previous-period line, a metric dropdown and a dimension picker (Channel, Campaign, Courier, Region), and a breakdown table beneath with value, previous, change and share.
```

*Health tab*
```text
Show the same page with the Health tab selected: one row per area with a health state, a short reason and an evidence link, and four cross-domain finding rows, each with an arrow, the two areas, one sentence and a confidence bar.
```

## P3 · Customers (with Customer 360)

Route `/b/:id/customers/:customerId?` · Tabs: List + 360: Timeline · Orders and payments · Conversations and calls · Deliveries · Website and marketing · Graph · Identity · Modules: M2, part of M16

**Short prompt** (after the STYLE block):
```text
A Customers workspace in master–detail layout. Left: a searchable customer list with status. Right: the selected customer's 360 view: profile header, linked identities across WhatsApp, Messenger and the website with confidence, and tabs Timeline, Orders and payments, Conversations and calls, Deliveries, Website and marketing, Graph, Identity. The Timeline tab is a vertical line of events mixing orders, payments, shipments, messages and calls. A side block shows open issues and an AI context block in a 'Not connected' state.
```

**Detail follow-up** (optional, as a second message):
```text
List rows: name, status chip (Active, Inactive, Blocked), last activity. Profile header: 'Nusrat Jahan (C18)', status chip, verified-contact badges, tags. Identities: WhatsApp, Messenger and website, each with a link confidence percentage and '—' for manually linked ones. The timeline is drawn along a thin vertical line with small nodes and channel icons. Side block: 'Open issues for this customer' and 'AI customer context' (Not connected).
```

**Extra screens** (optional; paste STYLE block, then this):

*Orders and payments tab*
```text
Show the same page with the Orders and payments tab selected: a table of this customer's orders and a table of payments with a refund status chip.
```

*Identity tab*
```text
Show the same page with the Identity tab selected: a table of linked identities (provider, id, confidence or '—', status) with Verify and Unlink actions.
```

## P4 · Commerce

Route `/b/:id/commerce/:tab` · Tabs: Orders · Payments and refunds · Deliveries · Products · Modules: M3, M4, M5, M11

**Short prompt** (after the STYLE block):
```text
A Commerce workspace with tabs Orders, Payments and refunds, Deliveries and Products. Show the Orders tab: filters, a table of orders (number, customer, status, total, date), and a right-hand detail drawer for one order with items, payment, refund, shipment tracking timeline, status history, an AI context block in a 'Not connected' state, and a status control that offers only the allowed next steps.
```

**Detail follow-up** (optional, as a second message):
```text
Order rows like '#1024 · Confirmed · BDT 2,500.00 · 09 Nov 2026, 14:32'; statuses Pending, Confirmed, Processing, Shipped, Delivered, Cancelled, Returned, Refunded. The status control shows only the legal next step (for example Pending → Confirmed or Cancelled). Orders cannot be edited, so no edit button. Show a toast 'This order changed. Reloaded.'
```

**Extra screens** (optional; paste STYLE block, then this):

*Payments and refunds tab*
```text
Show the Payments and refunds tab: filters (method COD, Card, Mobile banking, Bank transfer, Wallet; status), a table, a detail drawer with the refund ledger, a Refund dialog (amount, reason), and a switch to a financial timeline mixing payments and refunds by day. No free-text search box.
```

*Deliveries tab*
```text
Show the Deliveries tab: a shipments table (courier, status from Pending to Delivered, plus Failed and Returned), a Failed deliveries filter, and a drawer for '#S81 · Failed' with a tracking timeline and a 'Prepare submission' panel that says 'Prepared — not executed'.
```

*Products tab*
```text
Show the Products tab: a catalogue table (image, name, SKU, category, status, variants, price range, stock) and a drawer with variants, images and the actions 'Add variant' and 'Map to external reference'.
```

## P5 · Support

Route `/b/:id/support/:tab` · Tabs: Inbox · Queue · Calls (+ assign and handover dialogs) · Modules: M6, M7, M8, M12

**Short prompt** (after the STYLE block):
```text
A Support workspace with tabs Inbox, Queue and Calls. Show the Inbox tab as three panes: a conversation list (channel icon, priority, unread dot, assignee), a message thread with internal notes, an AI suggested reply and a reply box that says 'Saved — not sent', and a customer and order context panel. A toolbar offers Assign and Hand over to human or Return to AI.
```

**Detail follow-up** (optional, as a second message):
```text
Conversation rows: channel icon (Messenger, WhatsApp, Instagram, Telegram, Website chat), customer name, snippet, priority chip (Low, Normal, High, Urgent), unread dot, assignee avatar. Thread: message bubbles, attachments, delivery state, internal notes in a visibly tinted block, an 'AI suggested reply' block, and a composer whose button reads 'Save reply' with the note 'Saved — not sent'.
```

**Extra screens** (optional; paste STYLE block, then this):

*Queue tab*
```text
Show the Queue tab: a table of open and pending conversations, most urgent first then oldest, with priority, customer, channel, assignee and waiting time like '3h 12m'; filters Assigned (Me, Unassigned, Team), Priority, Status, Channel; above the table three tiles, 'Overdue detection', 'AI escalation signals' and 'Queue metrics', in a 'Not connected' state.
```

*Calls tab*
```text
Show the Calls tab: filters (customer, direction, status) with no search box, a calls table with duration, and a drawer with an event timeline, transcript, summary, a 'Recording' line in a 'Not connected' state, and a 'Schedule callback' button.
```

*Assign and handover dialogs*
```text
Show two dialogs over the dimmed Inbox tab: 'Assign conversation' (Agent, Team, AI or Unassigned, plus a reason) and 'Hand over to human' (reason and summary) with the note 'The customer is not notified automatically.'
```

## P6 · Growth (marketing and website)

Route `/b/:id/growth/:tab` · Tabs: Campaigns · Website · Modules: M9, M10

**Short prompt** (after the STYLE block):
```text
A Growth workspace with tabs Campaigns and Website. Show the Campaigns tab: a table of campaigns (platform, status, spend, clicks, conversions, marked as platform-reported) and a right-hand detail drawer with daily charts, a conversions table, ad sets, an 'Explain this campaign' AI panel and an 'Attributed revenue' tile in a 'Not connected' state.
```

**Detail follow-up** (optional, as a second message):
```text
Campaign drawer: spend and clicks as two small separate charts (never one chart with two axes), a conversions table labelled 'Platform-reported', tabs Ad sets, Ads and Creatives, and the AI panel with a button and an answer area.
```

**Extra screens** (optional; paste STYLE block, then this):

*Website tab*
```text
Show the Website tab: tabs Visitors, Sessions and Events with a table, a grid of seven analysis panels all in a 'Not connected' state (Traffic source, Funnel, Cart abandonment, Checkout drop-off, Landing page, Device, Experience signals), and a drawer showing one visitor's journey as a vertical event timeline from first visit to checkout.
```

## P7 · Intelligence (facts, graph, metrics)

Route `/b/:id/intelligence/:tab` · Tabs: Facts and issues · Graph · Metrics and analysis · Pipeline · Modules: M13, M14

**Short prompt** (after the STYLE block):
```text
An Intelligence workspace with tabs Facts and issues, Graph, Metrics and analysis, and Pipeline. Show the Facts and issues tab: on the left a list of facts written as plain sentences with confidence and an Evidence button, on the right a list of issues with severity and status. A right-hand Evidence drawer is open, showing a vertical evidence thread of small nodes, Metric snapshot → Fact → Issue, each linking to its source.
```

**Detail follow-up** (optional, as a second message):
```text
Fact example: 'Delivery failure rate in Gazipur increased from 9% to 17% during the current comparison period.' with a confidence bar and an Evidence button. Issue example: type HIGH_DELIVERY_FAILURE, severity chip, status (Open, Acknowledged, Resolved, Dismissed), and a Resolve button that asks for a note. The Evidence drawer ends with a short 'Why this is true' line.
```

**Extra screens** (optional; paste STYLE block, then this):

*Graph tab ★ recommended*
```text
Show the Graph tab: a large canvas of typed nodes (Customer, Order, Payment, Shipment, Campaign, Session, Conversation, Call) with labelled directed edges (PLACED_ORDER, HAS_PAYMENT, HAS_SHIPMENT, HAS_CALL); node types differ by shape and icon, not only colour. Left controls: root entity, direction (Outbound, Inbound, Both), depth, node limit, filters, confidence slider. Right panel: 'Why this edge exists', a path finder between two entities, a banner 'Showing 200 of 340 nodes', a Journey switch that turns the canvas into one timeline (Meta campaign → website session → product view → checkout → order → payment → shipment → delivery failure → WhatsApp conversation → support call), a Snapshots menu, and a 'Rebuild graph' button that opens a confirm dialog naming its effect.
```

*Metrics and analysis tab*
```text
Show the Metrics and analysis tab: on the left, metric groups (Sales, Revenue, Customer, Marketing, Support, Website, Delivery); in the main area a metrics table with name, key like 'bi.metric.revenue_gross.v1' with a copy button, unit chip and latest value; selecting one shows a history chart. Sub-tabs Revenue, Conversion, Attribution, Anomalies and Relationships each show a headline number, one chart, a table and two insights with Evidence buttons.
```

*Pipeline tab*
```text
Show the Pipeline tab: a 'Run pipeline' button with a confirm dialog, relationship counts (created, updated, unchanged, invalidated), a last-run line and a table of quarantined records with reasons.
```

## P8 · AI

Route `/b/:id/ai/:tab` · Tabs: Assistant · Recommendations and actions · Audit · Modules: M15

**Short prompt** (after the STYLE block):
```text
An AI workspace with tabs Assistant, Recommendations and actions, and Audit. Show the Assistant tab: a chat with one question and its answer, a 'Grounded in' list of the facts used, related open issues, and a banner saying answers come from recorded facts. Beside the chat, show the latest recommendation with evidence count and confidence.
```

**Detail follow-up** (optional, as a second message):
```text
Example question: 'Why did delivery failures rise in Gazipur?'. The answer is short, followed by 'Grounded in' with three facts and a link to the related issue. The question box has a Send button and a progress state for slow answers.
```

**Extra screens** (optional; paste STYLE block, then this):

*Recommendations and actions tab ★ recommended*
```text
Show the Recommendations and actions tab: recommendation rows with priority, evidence count, confidence and approval status; an actions table with states Suggested, Approved, Rejected, Executing, Executed and Failed; an approval dialog that requires a note of 3 to 1000 characters with a counter; a permanent banner 'Execution is simulated'; and Approve and Reject disabled with the tooltip 'Requires Operator role' for users without the role.
```

*Audit tab*
```text
Show the Audit tab: a log (time, user, request type, grounded facts, outcome) and a read-only list of guardrail rules with a 'Managed in Configuration' link.
```

## P9 · Admin (identity, integrations, configuration)

Route `/b/:id/admin/:section` · Tabs: Identity · Integrations · Configuration · Knowledge* · Simulation* (*design-only) · Modules: M16, M17, M18, M19, M20

**Short prompt** (after the STYLE block):
```text
An Admin workspace with a left section list: Identity, Integrations, Configuration, Knowledge and Simulation. Show the Integrations section: a summary band, a catalogue of providers by category (Commerce, Communication, Marketing, Analytics, Courier, Calling) with status and a Test button, sync history, data-freshness chips (Fresh, Delayed, Stale, Unavailable), and sub-tabs for failed records, webhooks and errors.
```

**Detail follow-up** (optional, as a second message):
```text
Provider rows show name, category, status (Connected, Needs attention, Not connected) and last sync. Results after an action read 'Attempt recorded — Succeeded', 'Attempt recorded — Failed' or 'Unsupported'. Secrets are never shown, only references. Failed records are grouped by error with a Retry button; webhooks have a Replay button that opens a confirm dialog.
```

**Extra screens** (optional; paste STYLE block, then this):

*Identity section*
```text
Show the Identity section, visible to Managers and Owners: tabs Canonical, External, Links, Conflicts, Merge candidates and History; the Conflicts view with two candidate identities, matching evidence and a confidence meter with Confirm link, Reject and Mark for review; and a merge review with a dry-run plan (fingerprint, safety checks, readiness) and an 'Execute merge' button that is permanently disabled with the note 'Blocked by design'.
```

*Configuration section*
```text
Show the Configuration section: a section list (Profile, General, AI, Knowledge, Rules and policies, Monitoring, Changes), the General form with a version chip, a banner 'Someone else changed this. Reload to continue.', a credential field that only shows 'Configured', and a Revision history drawer; also a rules and policies list with Name, Type, Status, Version.
```

*Knowledge and Simulation sections (design-only)*
```text
Show the Knowledge section and the Simulation section as layout only, each in a 'Not connected' state. Knowledge: knowledge areas on the left, a document list with the steps Ingested, Processed, Chunked and Embedded, and a search box with Keyword, Vector and Hybrid modes. Simulation: a scenario picker, a seed field, flaws to inject, a Run button, and an expected-versus-actual results table with pass or fail; every number carries a SIMULATED badge.
```
