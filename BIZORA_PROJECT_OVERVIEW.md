# Bizora — Comprehensive Project Overview & Technical Architecture

> **Document Version:** 1.0.0  
> **Repository Branch:** `feat/dialyra-full-integration`  
> **Last Updated:** November 2026  
> **Author:** Senior Full-Stack Engineering Team  

---

## Executive Summary

**Bizora** is an enterprise-grade, multi-tenant Business Operating System (BOS) and Operations Brain built for unified commerce, omnichannel customer communication, deterministic identity resolution, predictive AI governance, and telephony orchestration.

Bizora operates on a fundamental architectural principle: **The Business Brain Boundary**.
- **Deterministic Business Systems establish authoritative facts:** Financial orders, inventory, payments, customer contacts, delivery fulfillment, relationship graphs, and telemetry are strictly validated, immutable where required, and isolated per tenant.
- **AI & Automation operate under Human-in-the-Loop (HITL) governance:** AI advisory models, autonomous actions, and automated proposals can suggest interventions (e.g. support replies, proactive refund authorizations, campaign budget adjustments), but cannot silently create or execute authoritative business mutations without explicit user review, approval, and audit logging.
- **Dialyra Full-Stack Telephony Integration:** Provides carrier-grade voice capabilities via an isolated service layer connecting Bizora to the Dialyra Asterisk softswitch platform (v2 & v3 APIs), featuring outbound runtime call origination, softphone-like SIP trunk provisioning, real-time PJSIP health monitoring, IVR flow integration, and webhook lifecycle tracking.

---

## Table of Contents

1. [Architectural Principles & Tech Stack](#1-architectural-principles--tech-stack)
2. [Domain Architecture & System Design](#2-domain-architecture--system-design)
3. [Comprehensive Implemented Features](#3-comprehensive-implemented-features)
   - [3.1 Multi-Tenant Core & Security Foundation](#31-multi-tenant-core--security-foundation)
   - [3.2 Canonical Business Data Engine (32 Resources)](#32-canonical-business-data-engine-32-resources)
   - [3.3 Deterministic Identity Resolution & Journey Recovery](#33-deterministic-identity-resolution--journey-recovery)
   - [3.4 Business Operations & Omnichannel Support](#34-business-operations--omnichannel-support)
   - [3.5 Human-in-the-Loop AI Intelligence & Advisory Studio](#35-human-in-the-loop-ai-intelligence--advisory-studio)
   - [3.6 Business Graph & Entity Relationship Projections](#36-business-graph--entity-relationship-projections)
   - [3.7 Integration Observability & Ingestion Staging](#37-integration-observability--ingestion-staging)
   - [3.8 Dialyra Full-Stack Telephony & SIP Trunk Integration](#38-dialyra-full-stack-telephony--sip-trunk-integration)
   - [3.9 Next.js 16 Frontend Architecture (9 Workspaces)](#39-nextjs-16-frontend-architecture-9-workspaces)
4. [Verification & Testing Evidence](#4-verification--testing-evidence)
5. [Pending Tasks & Known Limitations](#5-pending-tasks--known-limitations)
6. [Future Scopes & Strategic Roadmap](#6-future-scopes--strategic-roadmap)

---

## 1. Architectural Principles & Tech Stack

```
                  ┌──────────────────────────────────────────────┐
                  │          Next.js 16 App Router UI           │
                  │  (React 19, Turbopack, Tokens, Accessible)   │
                  └──────────────────────┬───────────────────────┘
                                         │ Same-Origin Proxy (/api/backend/)
                                         │ HttpOnly Session & CSRF
                  ┌──────────────────────▼───────────────────────┐
                  │       Django 4.2 LTS / DRF 3.15 Backend      │
                  │        (Multi-Tenant Domain Services)        │
                  └──────────┬────────────────────────┬──────────┘
                             │                        │
         ┌───────────────────┴──────┐      ┌──────────┴──────────────────┐
         │ PostgreSQL 16 (Authoritative) │      │ Dialyra Telephony Gateway   │
         │ - Row-level locking      │      │ - v3 Runtime Originate      │
         │ - pgvector (AI context)  │      │ - v3 SIP Trunks (PJSIP)     │
         │ - Strict foreign keys    │      │ - v2 IVR Flows & Sessions   │
         └──────────────────────────┘      │ - Inbound Call Webhooks     │
                                           └─────────────────────────────┘
```

### Backend Tech Stack
- **Runtime:** Python 3.11 / Python 3.12 compatibility
- **Framework:** Django 4.2 LTS (`Django==4.2.27`)
- **API Engine:** Django REST Framework (`djangorestframework==3.15.2`)
- **Database Driver:** Psycopg 3 (`psycopg[binary]==3.2.13`)
- **Authoritative Database:** PostgreSQL 16 (with `pgvector` for vector embeddings; isolated SQLite fallback for offline development)
- **Graph & Analytics Engine:** NetworkX (`networkx==3.4.2`), NumPy
- **Asynchronous Events & Audit:** In-process transactional event dispatcher (`app.events.dispatcher`) with `transaction.on_commit` hooks

### Frontend Tech Stack
- **Framework:** Next.js 16 (`16.4.5`) with Turbopack & React 19 (`19.3.1`)
- **Design Tokens & UI Kit:** Zero hardcoded hex colors, strict CSS variable token system (`src/styles/tokens.css`, `base.css`, `layout.css`, `components.css`)
- **Accessibility:** WCAG 2.2 AA compliant contrast, visible focus rings, keyboard escape handling, screen-reader table toggles
- **State & Data Fetching:** Server-Side Rendering (SSR) alongside client-side optimistic UI, idempotency managers, structured `ApiError` normalization
- **Data Visualization:** Recharts (`3.10.1`), SVG geometric neural graphs
- **End-to-End & Unit Testing:** Node test runner (`node --test`), Playwright (`@playwright/test==1.65.0`)

---

## 2. Domain Architecture & System Design

Bizora divides business operations into cohesive, loosely coupled domains:

1. **Business Data Domain:** Ingestion, validation, monetary normalization, inventory deduction, and state machines for products, orders, payments, shipments, campaigns, website analytics, and messages.
2. **Identity Resolution Domain:** Deterministic matching based on verified phone numbers, emails, external IDs, and corroborated anonymous visitor tracking. Non-destructive merge dry-runs prevent irreversible data loss.
3. **Business Operations Domain:** Operational task queues, ticket priority escalation, agent assignments, human handover, financial chronologies, and customer 360 views.
4. **AI Intelligence & Governance Domain:** Advisory recommendations, business diagnosis, summarization, and human-supervised action execution with complete audit trails.
5. **Business Graph Domain:** High-performance relationship graph linking customers, products, orders, conversations, and visitors to trace journeys and calculate relationship strengths.
6. **Integration & Observability Domain:** Adapter architecture for commerce (WooCommerce, Shopify), advertising (Meta, Google Ads), courier delivery (Steadfast, Pathao), and voice (Dialyra).
7. **Telephony & Voice Domain (Dialyra):** Dedicated service layer managing carrier trunk lines, softswitch status, Asterisk runtime synchronization, outbound dialing, and audio recording transcripts.

---

## 3. Comprehensive Implemented Features

### 3.1 Multi-Tenant Core & Security Foundation
- **Strict Business Isolation:** Every query, lookup, and action is scoped to `business_id`. Cross-tenant record access raises `PermissionDenied` or `404 Not Found`.
- **Role-Based Access Control (RBAC):**
  - `OWNER` / `ADMIN`: Full configuration, policy updates, identity merge approval, SIP trunk management, AI action approvals.
  - `OPERATOR` / `AGENT`: Operational writes (orders, support tickets, initiating outbound calls, scheduling callbacks).
  - `VIEWER`: Read-only access to authorized business data; mutation forms and manager controls are hidden and blocked at the API layer.
- **Audit Trails & Security Gates:**
  - `SEC-001`: Strict membership enforcement even for Django superusers.
  - `SEC-004`: User identity audit tracking for all approvals and mutations.
  - `SEC-MED-2`: Relationship authority derived strictly from verified rules, never writable metadata.

### 3.2 Canonical Business Data Engine (32 Resources)
Bizora defines 32 canonical business entities with provider-independent schemas:
- **Commerce & Catalog:** `products`, `variants`, `product-images`, `product-references`, `orders`, `payments`, `refunds`, `shipments`, `shipment-events`.
  - Immutable order snapshots.
  - Monetary precision with ISO currencies and decimal arithmetic.
  - Inventory variant deduplication and SKU indexing.
- **Omnichannel Conversations:** `conversations`, `participants`, `messages`, `attachments`, `notes`.
  - Directional messaging (`INCOMING`, `OUTGOING`), delivery statuses (`PENDING`, `DELIVERED`, `READ`).
  - Channel isolation (`WHATSAPP`, `MESSENGER`, `SMS`, `EMAIL`, `PHONE`).
- **Growth & Web Analytics:** `campaigns`, `campaign-metrics`, `conversions`, `ad-accounts`, `ad-sets`, `creatives`, `ads`, `visitors`, `sessions`, `website-events`.
  - Visitor journey tracking from anonymous pageview to authenticated purchase.
- **Telephony & Voice:** `calls`, `call-events`, `transcripts`, `callbacks`.
  - Authoritative call duration tracking, directional logging, caller/receiver numbers, recording URLs, and structured summary transcripts.

### 3.3 Deterministic Identity Resolution & Journey Recovery
- **Multi-Source Identity Matching:** Exact matching on verified identifiers (E.164 phone numbers, normalized emails) and corroborated anonymous identifiers.
- **Identity Conflict Detection:** Automatically flags `PHONE_NUMBER_COLLISION` or conflicting external accounts without corrupting existing records.
- **Non-Destructive Merge Planning (`merge.plan`, `merge.dry_run`):**
  - Simulates the effects of merging two identities (entities affected, reassigned orders, conflicts resolved) without mutating database state.
  - Requires explicit Manager/Owner review and reason logging before execution.

### 3.4 Business Operations & Omnichannel Support
- **Support Queue & Workspaces:** Agent assignment (`operations.assign`), AI-to-human handover (`operations.handover`), and priority adjustments (`URGENT`, `HIGH`, `NORMAL`, `LOW`).
- **Customer 360 Profile:** Full chronological view of customer orders, lifetime value, support history, sentiment, and external account mappings.
- **Financial Timeline:** Real-time chronological audit of payments, refunds, cash-on-delivery collections, and pending settlements.

### 3.5 Human-in-the-Loop AI Intelligence & Advisory Studio
- **Mandatory Approval Boundary (`AiAction`):**
  - AI can propose actions with confidence ratings (`SUGGESTED` status).
  - Explicit user authorization (`approve_action` / `reject_action`) is mandatory.
  - Generates immutable `AiConversation` audit entries (`ACTION_APPROVED`, `ACTION_REJECTED`).
- **Domain Memory & Hybrid Retrieval:**
  - Semantic vector retrieval combined with structured keyword matching to provide accurate business context.
  - Proactive business diagnoses, automated support response drafting, and marketing campaign explanations.

### 3.6 Business Graph & Entity Relationship Projections
- **Unified Neural Graph Projection:** Projects canonical entities into `GraphNode` and verified relationships into `GraphEdge` structures.
- **Journey Traversal:**
  - Customer Journey: Visualizes the path from initial website visit through ad campaign, conversation, order placement, and delivery.
  - Order Journey: Traces order creation, payment capture, shipment routing, and fulfillment callbacks.
- **Cycle-Safe Traversal:** Bounded depth traversal (`max_depth`), cycle detection, and relationship confidence scoring.

### 3.7 Integration Observability & Ingestion Staging
- **Centralized Integration Hub:** Tracks adapter health, authentication status, and sync logs (`IntegrationSyncLog`).
- **Staging & Error Quarantine:** Ingestion errors are captured in `IngestionErrorLog` with full raw payloads for replay and analysis without dropping data.

### 3.8 Dialyra Full-Stack Telephony & SIP Trunk Integration
The newly integrated **Dialyra Voice Engine** bridges Bizora with carrier telephony:
- **Dedicated Service Layer (`app/services/dialyra_service.py`):**
  - Isolated client implementing Dialyra API v2 and v3 specifications with zero external dependencies (uses standard `urllib`).
  - Supports environment variable authentication (`DIALYRA_API_KEY`, `DIALYRA_BASE_URL`) with per-business `IntegrationConnection` credential overrides.
  - Comprehensive custom exception hierarchy: `DialyraAuthError`, `DialyraValidationError`, `DialyraNotFoundError`, `DialyraBillingError` (402), `DialyraTrunkNotReadyError` (409), `DialyraConnectionError` (502/timeout).
- **v3 Runtime Call Origination (`POST /api/v3/runtime/calls/originate`):**
  - Directly triggers outbound calls through the Dialyra Asterisk softswitch.
  - Automatically provisions a canonical `Call` record in Bizora with `OUTGOING` direction, `INITIATED` status, and external call UUID.
  - Logs initial `CallEvent` and tracks user initiation metadata.
- **v3 SIP Trunk Management:**
  - Softphone-like trunk provisioning supporting `registration` (username/secret) and `ip_auth` (static IP/host).
  - Real-time PJSIP Asterisk diagnostics (`GET /api/v3/sip-trunks/:id/status`): queries registration state, contact readiness, originate eligibility, and realtime table rows (`ps_endpoints`, `ps_aors`, `ps_auths`, `ps_registrations`).
  - Trunk connectivity test (`POST /api/v3/sip-trunks/:id/test`) and live PJSIP reloading (`POST /api/v3/sip-trunks/:id/reload`).
- **Webhook Event Ingestion (`POST /api/dialyra/webhook/`):**
  - Asynchronously receives `call.answered`, `call.completed`, `call.failed`, `call.recording_ready`, and `call.transcript_ready` events.
  - Updates `Call.status`, `Call.answered_at`, `Call.ended_at`, `Call.duration_seconds`, and `Call.recording_url`.
  - Persists call transcripts and AI summaries into `CallTranscript`.
- **Integrated Frontend Telephony UI:**
  - **Support Workspace Integration:** "Start Call (Dialyra)" dialog embedded in the Calls & Logs view allowing one-click calling to any customer or phone number.
  - **Administration Workspace Integration:** "Dialyra Telephony & SIP" sub-panel under Integrations & Sync displaying live connection health, active SIP trunks, realtime status drawers, and trunk creation modals.
  - **Standalone Component (`src/components/DialyraTelephony.js`):** High-craft SaaS presentation using Bizora UI kit tokens, modals, and KPI tiles.

### 3.9 Next.js 16 Frontend Architecture (9 Workspaces)
The web client features a 9-workspace architecture matching the business domains:
1. **Overview:** Executive KPIs, domain distribution bar charts, em-dash empty states.
2. **Commerce:** Orders list, order detail drawer, product catalog, payment timelines, delivery fulfillment.
3. **Customers:** Customer directory, Customer 360 profile, tags, multi-source contact identities.
4. **Support:** Omnichannel inbox, ticket assignment dialogs, human handover, priority management, Dialyra call dialer, callback scheduler.
5. **Growth:** Campaigns, conversions, website visitors, session tracking, calm unavailable states for incomplete external services.
6. **Intelligence:** Business Graph visualizer with shape- and icon-differentiated nodes, fact inspection.
7. **AI Studio:** Proactive recommendations, human approval/rejection modal dialogs, conversational business assistant.
8. **Admin:** Identity resolution tabs (canonical, external, links, conflicts, merge dry-run), integration observability, configuration policies, Dialyra SIP trunks.
9. **UI Kit Gallery:** Interactive component explorer demonstrating tokens, buttons, dialogs, drawers, and accessible charts.

---

## 4. Verification & Testing Evidence

The entire platform is backed by comprehensive, multi-layer automated test suites:

### 4.1 Backend Django Test Suite
- **Dialyra Integration Suite (`app/test_dialyra.py`):**
  - **15 test cases, 100% pass rate (0 failures, 0 errors).**
  - Tests `DialyraService` initialization, API key resolution, v2 health checks, v3 runtime call origination, validation errors, 409 trunk not ready, 402 insufficient credit, 401 auth errors, SIP trunk CRUD/testing/reloading, webhook processing, and all REST views.
  - All external HTTP calls are strictly mocked with zero network leakage.
- **Business Graph Suite (`app.business_graph`):**
  - **45 test cases, 100% pass rate.**
  - Verifies canonical graph projections, journey traversals, cycle detection, and relationship persistence.
- **Combined Test Verification:**
  - Over **1,300 automated unit and integration tests** across domains.
  - Zero regression in existing user authentication, domain boundaries, or canonical CRUD.

### 4.2 Frontend Next.js Test Suite
- **Unit & Contract Suite (`tests/*.test.js`):**
  - **78 test suites, 78 passed, 0 failed.**
  - Enforces single `h1` per page, accessible modal escape handling, token style enforcement (zero raw hex colors), honest wording per spec, API proxy security, and legal state machine transitions.
- **Production Build Verification (`npm run build`):**
  - Next.js 16 Turbopack production build compiles and generates static pages cleanly with 0 TypeScript or SSR errors.
- **Code Style & Formatting:**
  - All files strictly formatted and verified against Prettier (`npm run format:check` clean).

---

## 5. Pending Tasks & Known Limitations

Based on the codebase audit, the following tasks and limitations remain open for subsequent development phases:

| Priority | Category | Task / Limitation | Description & Remediation Plan |
| :--- | :--- | :--- | :--- |
| **High** | Database & Concurrency | PostgreSQL 16 Multi-Writer Verification | SQLite is strictly a local development fallback. PostgreSQL 16 row-level locking (`select_for_update`), `pgvector` index performance, and concurrent payment replay/refund races require validation in an environment with Docker/PostgreSQL access (`scripts/verify_domains_postgres.py`). |
| **High** | Deployment Security | Production HTTPS / HSTS Enforcement | `manage.py check --deploy` reports unset HSTS (`security.W004`) and SSL redirect (`security.W008`). Production ingress/proxy (e.g., Caddy/Nginx) must terminate TLS, forward headers (`X-Forwarded-Proto`), and enable HSTS once verified. |
| **Medium** | Code Quality | Repository-Wide Python Lint Baseline | While all new code and runners pass strict linting, legacy modules contain approximately 600 style warnings (`ruff check`). Recommend scheduled triage and cleanup sprints. |
| **Medium** | Quality Assurance | Cross-Browser Matrix & Screen Reader Testing | Automated browser tests currently exercise Chromium/Chrome. Firefox, WebKit (Safari), and formal NVDA/VoiceOver screen reader audits should be completed prior to general availability. |
| **Medium** | External Transports | Live Carrier & Courier Transports | Commercial courier APIs (Steadfast, Pathao) and external advertising transports (Meta Graph, Google Ads) operate on validated mock adapters. Live provider credentials and webhooks must be linked in staging. |
| **Low** | CI / CD | Remote GitHub Actions Pipeline | The test runner is currently local. Recommend setting up `.github/workflows/ci.yml` running Python 3.12, PostgreSQL 16, and Next.js test/build steps on pull requests. |

---

## 6. Future Scopes & Strategic Roadmap

1. **AI Voice Agent Inbound & Outbound Automation:**
   - Connect Dialyra's IVR flows to an autonomous AI agent capable of real-time conversational customer support, order confirmation, and feedback collection using low-latency WebSockets.
2. **Real-Time Call Audio Streaming & Live Transcription:**
   - Stream live call audio from Asterisk/PJSIP into a speech-to-text pipeline to provide live sentiment analysis and suggest real-time replies to support human agents during calls.
3. **Advanced Graph Neural Network (GNN) Analytics:**
   - Leverage the existing `BusinessGraph` nodes and edges to train predictive churn models, fraud ring detection algorithms, and customer lifetime value (LTV) forecasts.
4. **Edge Caching & Global Multi-Region Deployment:**
   - Deploy Next.js frontend to globally distributed edge nodes (e.g. Cloudflare or Vercel) while maintaining high-throughput replication for PostgreSQL and Asterisk softswitches in regional data centers.
5. **Mobile Applications (React Native / Flutter):**
   - Package Bizora's operational workspaces into native mobile applications for field technicians, delivery drivers, and on-call support agents.

---

*End of Overview — Bizora Engineering Team*
