# Bizora — Stitch batch prompts (9 pages)

Status: draft for owner review, 2026-11-09. Generated from [`frontend-stitch-prompt.md`](frontend-stitch-prompt.md) by
`.claude/memory/frontend-work/build_pack9.py`. Accuracy target about 80–90%; generic on purpose.

Each block is **self-contained**: paste it as it is. No file is needed.

**How to use**
1. Paste **F0** first and fix it until you like it.
2. Paste **ALL 9** (nine screens in one request). If Stitch makes fewer, or merges some, reply with exactly:
   `Create the missing screens from the list above as separate screens.`
   If that fails, use **Half A** (5 screens) and **Half B** (4 screens) instead.
3. Then paste the two **starred extras** (Graph, Recommendations and actions).
4. Check each screen with the five questions in the pack's §3.3, then bring screenshots back with the page numbers.

Not verified: how many screens Stitch makes from one request. No block has been run in Stitch yet.

---

## F0 · Design system and app shell (paste first, on its own)

```text
STYLE for this screen. Bizora, a formal enterprise web app for commerce businesses. Light theme, desktop 1440 px. Cool-slate neutrals with ONE cobalt-blue primary; no other accent, no gradients, no illustrations, no emoji.
Colours: canvas #F8FAFC; surface #FFFFFF; subtle surface #F1F5F9; border #E2E8F0; input border #76859B; ink text #0F172A; secondary text #334155; muted text #526278; primary #1D4ED8 (hover #1E40AF, soft fill #EFF6FF, text on soft fill #1E40AF, white label on primary); success #15803D on #F0FDF4; warning #B45309 on #FFFBEB; danger #B91C1C on #FEF2F2; info #0369A1 on #F0F9FF.
Navigation: left rail 256 px, background #0F172A, item text #CBD5E1, section labels #94A3B8, active item white on #1E293B with a 3 px #60A5FA bar; sticky top bar 56 px. Keep exactly the same rail and top bar as the app-shell screen.
Type: Plus Jakarta Sans for headings, Inter for text, JetBrains Mono for numbers, IDs and codes. Page title 28 px bold, body 14 px, table cells 13 px.
Shape: 8 px radius, 1 px borders, almost no shadow, simple 1.5 px line icons. Prefer sections, tables and dividers over cards; no cards inside cards. Every status chip has an icon and a label. Show money as "BDT 2,500.00", dates as "09 Nov 2026, 14:32", ratios as "17.0%", and missing data as "—", never 0.

Create the Bizora design-system sheet and the empty app shell, light theme, on one tall canvas.
Part 1, the sheet: colour swatches with their hex values and role names; the type scale (display 40, page title 28, section 22, card title 18, body 14, table 13, caption 12, overline 11 uppercase with letter spacing); buttons (primary, secondary, ghost, danger; default, hover, focus ring, disabled); inputs (text, select, date range, checkbox, switch) with label above and helper text below; status chips (Success, Warning, Danger, Info, Neutral, each with icon and label); severity chips (Low, Medium, High, Critical); a compact data table with sticky header, sortable columns, right-aligned monospaced numbers and a footer "1–25 of 1,284"; a KPI tile with value, delta arrow, previous value and a tiny sparkline; a right-hand detail drawer; a confirm dialog that names the target and the effect; a toast; a skeleton loader; an empty state with one action; and the special "Not connected" state: dashed border, info icon, title "Not connected", line "Owner: Business Intelligence", one-sentence reason.
Part 2, the shell: rail groups Overview · Operations · Intelligence · Data & identity · Integrations · Settings, with the page names Overview; Inbox, Support queue, Customers, Orders, Payments, Products, Delivery, Calls, Marketing, Website; Intelligence, Graph, AI assistant, Actions, Memory & knowledge, Simulation; Identity; Integration health; Configuration. Top bar: business switcher, "Updated 14:32" freshness label, user menu. Main area empty with a page-title placeholder.
```

## ALL 9 (nine screens in one request)

```text
Create 9 separate screens in this project, one screen per item below, in the order given. Each screen is a full desktop page (1440 px, light theme) showing the page's default tab; the other tabs appear in its tab bar but are not drawn. Every screen must share exactly the same navigation rail, top bar, colours and fonts. Do not merge screens and do not skip any.

STYLE for every screen below. Bizora, a formal enterprise web app for commerce businesses. Light theme, desktop 1440 px. Cool-slate neutrals with ONE cobalt-blue primary; no other accent, no gradients, no illustrations, no emoji.
Colours: canvas #F8FAFC; surface #FFFFFF; subtle surface #F1F5F9; border #E2E8F0; input border #76859B; ink text #0F172A; secondary text #334155; muted text #526278; primary #1D4ED8 (hover #1E40AF, soft fill #EFF6FF, text on soft fill #1E40AF, white label on primary); success #15803D on #F0FDF4; warning #B45309 on #FFFBEB; danger #B91C1C on #FEF2F2; info #0369A1 on #F0F9FF.
Navigation: left rail 256 px, background #0F172A, item text #CBD5E1, section labels #94A3B8, active item white on #1E293B with a 3 px #60A5FA bar; sticky top bar 56 px. Keep exactly the same rail and top bar as the app-shell screen.
Type: Plus Jakarta Sans for headings, Inter for text, JetBrains Mono for numbers, IDs and codes. Page title 28 px bold, body 14 px, table cells 13 px.
Shape: 8 px radius, 1 px borders, almost no shadow, simple 1.5 px line icons. Prefer sections, tables and dividers over cards; no cards inside cards. Every status chip has an icon and a label. Show money as "BDT 2,500.00", dates as "09 Nov 2026, 14:32", ratios as "17.0%", and missing data as "—", never 0.

Screens:
Screen P1 · Sign-in and business choice: Two screens. First, a clean sign-in page: a centred panel with username, password and a Sign in button, plus an error version. Second, a choose-business page: a short list of businesses, each with name, currency, timezone, the user's role (Owner or Operator) and an Open button. Nothing decorative.
Screen P2 · Overview: The Overview home page with tabs Overview, Trends and Health. On the Overview tab: business name, a period selector and a compare toggle; six key-number tiles with change and sparkline (one tile shows a 'Not connected' state); a trend chart with a previous-period line; business health by area; active issues with severity and confidence; a recent activity feed; AI recommendations with approval status; and a small strip of cross-domain findings such as Marketing → Revenue.
Screen P3 · Customers (with Customer 360): A Customers workspace in master–detail layout. Left: a searchable customer list with status. Right: the selected customer's 360 view: profile header, linked identities across WhatsApp, Messenger and the website with confidence, and tabs Timeline, Orders and payments, Conversations and calls, Deliveries, Website and marketing, Graph, Identity. The Timeline tab is a vertical line of events mixing orders, payments, shipments, messages and calls. A side block shows open issues and an AI context block in a 'Not connected' state.
Screen P4 · Commerce: A Commerce workspace with tabs Orders, Payments and refunds, Deliveries and Products. Show the Orders tab: filters, a table of orders (number, customer, status, total, date), and a right-hand detail drawer for one order with items, payment, refund, shipment tracking timeline, status history, an AI context block in a 'Not connected' state, and a status control that offers only the allowed next steps.
Screen P5 · Support: A Support workspace with tabs Inbox, Queue and Calls. Show the Inbox tab as three panes: a conversation list (channel icon, priority, unread dot, assignee), a message thread with internal notes, an AI suggested reply and a reply box that says 'Saved — not sent', and a customer and order context panel. A toolbar offers Assign and Hand over to human or Return to AI.
Screen P6 · Growth (marketing and website): A Growth workspace with tabs Campaigns and Website. Show the Campaigns tab: a table of campaigns (platform, status, spend, clicks, conversions, marked as platform-reported) and a right-hand detail drawer with daily charts, a conversions table, ad sets, an 'Explain this campaign' AI panel and an 'Attributed revenue' tile in a 'Not connected' state.
Screen P7 · Intelligence (facts, graph, metrics): An Intelligence workspace with tabs Facts and issues, Graph, Metrics and analysis, and Pipeline. Show the Facts and issues tab: on the left a list of facts written as plain sentences with confidence and an Evidence button, on the right a list of issues with severity and status. A right-hand Evidence drawer is open, showing a vertical evidence thread of small nodes, Metric snapshot → Fact → Issue, each linking to its source.
Screen P8 · AI: An AI workspace with tabs Assistant, Recommendations and actions, and Audit. Show the Assistant tab: a chat with one question and its answer, a 'Grounded in' list of the facts used, related open issues, and a banner saying answers come from recorded facts. Beside the chat, show the latest recommendation with evidence count and confidence.
Screen P9 · Admin (identity, integrations, configuration): An Admin workspace with a left section list: Identity, Integrations, Configuration, Knowledge and Simulation. Show the Integrations section: a summary band, a catalogue of providers by category (Commerce, Communication, Marketing, Analytics, Courier, Calling) with status and a Test button, sync history, data-freshness chips (Fresh, Delayed, Stale, Unavailable), and sub-tabs for failed records, webhooks and errors.
```

## Half A: the story pages (5 screens)

```text
Create 5 separate screens in this project, one screen per item below, in the order given. Each screen is a full desktop page (1440 px, light theme) showing the page's default tab; the other tabs appear in its tab bar but are not drawn. Every screen must share exactly the same navigation rail, top bar, colours and fonts. Do not merge screens and do not skip any.

STYLE for every screen below. Bizora, a formal enterprise web app for commerce businesses. Light theme, desktop 1440 px. Cool-slate neutrals with ONE cobalt-blue primary; no other accent, no gradients, no illustrations, no emoji.
Colours: canvas #F8FAFC; surface #FFFFFF; subtle surface #F1F5F9; border #E2E8F0; input border #76859B; ink text #0F172A; secondary text #334155; muted text #526278; primary #1D4ED8 (hover #1E40AF, soft fill #EFF6FF, text on soft fill #1E40AF, white label on primary); success #15803D on #F0FDF4; warning #B45309 on #FFFBEB; danger #B91C1C on #FEF2F2; info #0369A1 on #F0F9FF.
Navigation: left rail 256 px, background #0F172A, item text #CBD5E1, section labels #94A3B8, active item white on #1E293B with a 3 px #60A5FA bar; sticky top bar 56 px. Keep exactly the same rail and top bar as the app-shell screen.
Type: Plus Jakarta Sans for headings, Inter for text, JetBrains Mono for numbers, IDs and codes. Page title 28 px bold, body 14 px, table cells 13 px.
Shape: 8 px radius, 1 px borders, almost no shadow, simple 1.5 px line icons. Prefer sections, tables and dividers over cards; no cards inside cards. Every status chip has an icon and a label. Show money as "BDT 2,500.00", dates as "09 Nov 2026, 14:32", ratios as "17.0%", and missing data as "—", never 0.

Screens:
Screen P2 · Overview: The Overview home page with tabs Overview, Trends and Health. On the Overview tab: business name, a period selector and a compare toggle; six key-number tiles with change and sparkline (one tile shows a 'Not connected' state); a trend chart with a previous-period line; business health by area; active issues with severity and confidence; a recent activity feed; AI recommendations with approval status; and a small strip of cross-domain findings such as Marketing → Revenue.
Screen P3 · Customers (with Customer 360): A Customers workspace in master–detail layout. Left: a searchable customer list with status. Right: the selected customer's 360 view: profile header, linked identities across WhatsApp, Messenger and the website with confidence, and tabs Timeline, Orders and payments, Conversations and calls, Deliveries, Website and marketing, Graph, Identity. The Timeline tab is a vertical line of events mixing orders, payments, shipments, messages and calls. A side block shows open issues and an AI context block in a 'Not connected' state.
Screen P5 · Support: A Support workspace with tabs Inbox, Queue and Calls. Show the Inbox tab as three panes: a conversation list (channel icon, priority, unread dot, assignee), a message thread with internal notes, an AI suggested reply and a reply box that says 'Saved — not sent', and a customer and order context panel. A toolbar offers Assign and Hand over to human or Return to AI.
Screen P7 · Intelligence (facts, graph, metrics): An Intelligence workspace with tabs Facts and issues, Graph, Metrics and analysis, and Pipeline. Show the Facts and issues tab: on the left a list of facts written as plain sentences with confidence and an Evidence button, on the right a list of issues with severity and status. A right-hand Evidence drawer is open, showing a vertical evidence thread of small nodes, Metric snapshot → Fact → Issue, each linking to its source.
Screen P8 · AI: An AI workspace with tabs Assistant, Recommendations and actions, and Audit. Show the Assistant tab: a chat with one question and its answer, a 'Grounded in' list of the facts used, related open issues, and a banner saying answers come from recorded facts. Beside the chat, show the latest recommendation with evidence count and confidence.
```

## Half B: the other pages (4 screens)

```text
Create 4 separate screens in this project, one screen per item below, in the order given. Each screen is a full desktop page (1440 px, light theme) showing the page's default tab; the other tabs appear in its tab bar but are not drawn. Every screen must share exactly the same navigation rail, top bar, colours and fonts. Do not merge screens and do not skip any.

STYLE for every screen below. Bizora, a formal enterprise web app for commerce businesses. Light theme, desktop 1440 px. Cool-slate neutrals with ONE cobalt-blue primary; no other accent, no gradients, no illustrations, no emoji.
Colours: canvas #F8FAFC; surface #FFFFFF; subtle surface #F1F5F9; border #E2E8F0; input border #76859B; ink text #0F172A; secondary text #334155; muted text #526278; primary #1D4ED8 (hover #1E40AF, soft fill #EFF6FF, text on soft fill #1E40AF, white label on primary); success #15803D on #F0FDF4; warning #B45309 on #FFFBEB; danger #B91C1C on #FEF2F2; info #0369A1 on #F0F9FF.
Navigation: left rail 256 px, background #0F172A, item text #CBD5E1, section labels #94A3B8, active item white on #1E293B with a 3 px #60A5FA bar; sticky top bar 56 px. Keep exactly the same rail and top bar as the app-shell screen.
Type: Plus Jakarta Sans for headings, Inter for text, JetBrains Mono for numbers, IDs and codes. Page title 28 px bold, body 14 px, table cells 13 px.
Shape: 8 px radius, 1 px borders, almost no shadow, simple 1.5 px line icons. Prefer sections, tables and dividers over cards; no cards inside cards. Every status chip has an icon and a label. Show money as "BDT 2,500.00", dates as "09 Nov 2026, 14:32", ratios as "17.0%", and missing data as "—", never 0.

Screens:
Screen P1 · Sign-in and business choice: Two screens. First, a clean sign-in page: a centred panel with username, password and a Sign in button, plus an error version. Second, a choose-business page: a short list of businesses, each with name, currency, timezone, the user's role (Owner or Operator) and an Open button. Nothing decorative.
Screen P4 · Commerce: A Commerce workspace with tabs Orders, Payments and refunds, Deliveries and Products. Show the Orders tab: filters, a table of orders (number, customer, status, total, date), and a right-hand detail drawer for one order with items, payment, refund, shipment tracking timeline, status history, an AI context block in a 'Not connected' state, and a status control that offers only the allowed next steps.
Screen P6 · Growth (marketing and website): A Growth workspace with tabs Campaigns and Website. Show the Campaigns tab: a table of campaigns (platform, status, spend, clicks, conversions, marked as platform-reported) and a right-hand detail drawer with daily charts, a conversions table, ad sets, an 'Explain this campaign' AI panel and an 'Attributed revenue' tile in a 'Not connected' state.
Screen P9 · Admin (identity, integrations, configuration): An Admin workspace with a left section list: Identity, Integrations, Configuration, Knowledge and Simulation. Show the Integrations section: a summary band, a catalogue of providers by category (Commerce, Communication, Marketing, Analytics, Courier, Calling) with status and a Test button, sync history, data-freshness chips (Fresh, Delayed, Stale, Unavailable), and sub-tabs for failed records, webhooks and errors.
```

## ★ Extra: P7 Graph tab

```text
STYLE for this screen. Bizora, a formal enterprise web app for commerce businesses. Light theme, desktop 1440 px. Cool-slate neutrals with ONE cobalt-blue primary; no other accent, no gradients, no illustrations, no emoji.
Colours: canvas #F8FAFC; surface #FFFFFF; subtle surface #F1F5F9; border #E2E8F0; input border #76859B; ink text #0F172A; secondary text #334155; muted text #526278; primary #1D4ED8 (hover #1E40AF, soft fill #EFF6FF, text on soft fill #1E40AF, white label on primary); success #15803D on #F0FDF4; warning #B45309 on #FFFBEB; danger #B91C1C on #FEF2F2; info #0369A1 on #F0F9FF.
Navigation: left rail 256 px, background #0F172A, item text #CBD5E1, section labels #94A3B8, active item white on #1E293B with a 3 px #60A5FA bar; sticky top bar 56 px. Keep exactly the same rail and top bar as the app-shell screen.
Type: Plus Jakarta Sans for headings, Inter for text, JetBrains Mono for numbers, IDs and codes. Page title 28 px bold, body 14 px, table cells 13 px.
Shape: 8 px radius, 1 px borders, almost no shadow, simple 1.5 px line icons. Prefer sections, tables and dividers over cards; no cards inside cards. Every status chip has an icon and a label. Show money as "BDT 2,500.00", dates as "09 Nov 2026, 14:32", ratios as "17.0%", and missing data as "—", never 0.

P7 · Intelligence (facts, graph, metrics), Graph tab. Show the Graph tab: a large canvas of typed nodes (Customer, Order, Payment, Shipment, Campaign, Session, Conversation, Call) with labelled directed edges (PLACED_ORDER, HAS_PAYMENT, HAS_SHIPMENT, HAS_CALL); node types differ by shape and icon, not only colour. Left controls: root entity, direction (Outbound, Inbound, Both), depth, node limit, filters, confidence slider. Right panel: 'Why this edge exists', a path finder between two entities, a banner 'Showing 200 of 340 nodes', a Journey switch that turns the canvas into one timeline (Meta campaign → website session → product view → checkout → order → payment → shipment → delivery failure → WhatsApp conversation → support call), a Snapshots menu, and a 'Rebuild graph' button that opens a confirm dialog naming its effect.
```

## ★ Extra: P8 Recommendations and actions tab

```text
STYLE for this screen. Bizora, a formal enterprise web app for commerce businesses. Light theme, desktop 1440 px. Cool-slate neutrals with ONE cobalt-blue primary; no other accent, no gradients, no illustrations, no emoji.
Colours: canvas #F8FAFC; surface #FFFFFF; subtle surface #F1F5F9; border #E2E8F0; input border #76859B; ink text #0F172A; secondary text #334155; muted text #526278; primary #1D4ED8 (hover #1E40AF, soft fill #EFF6FF, text on soft fill #1E40AF, white label on primary); success #15803D on #F0FDF4; warning #B45309 on #FFFBEB; danger #B91C1C on #FEF2F2; info #0369A1 on #F0F9FF.
Navigation: left rail 256 px, background #0F172A, item text #CBD5E1, section labels #94A3B8, active item white on #1E293B with a 3 px #60A5FA bar; sticky top bar 56 px. Keep exactly the same rail and top bar as the app-shell screen.
Type: Plus Jakarta Sans for headings, Inter for text, JetBrains Mono for numbers, IDs and codes. Page title 28 px bold, body 14 px, table cells 13 px.
Shape: 8 px radius, 1 px borders, almost no shadow, simple 1.5 px line icons. Prefer sections, tables and dividers over cards; no cards inside cards. Every status chip has an icon and a label. Show money as "BDT 2,500.00", dates as "09 Nov 2026, 14:32", ratios as "17.0%", and missing data as "—", never 0.

P8 · AI, Recommendations and actions tab. Show the Recommendations and actions tab: recommendation rows with priority, evidence count, confidence and approval status; an actions table with states Suggested, Approved, Rejected, Executing, Executed and Failed; an approval dialog that requires a note of 3 to 1000 characters with a counter; a permanent banner 'Execution is simulated'; and Approve and Reject disabled with the tooltip 'Requires Operator role' for users without the role.
```
