/**
 * Bizora Live Documentation & Pitch Deck Content
 * Structured sections matching YC Pitch Deck & Technical Whitepaper specifications.
 */

export const TEAM_MEMBERS = [
  {
    id: 'tanjim-abubokor',
    name: 'Tanjim Abubokor',
    role: 'Team Lead',
    email: 'abubokortanjim@gmail.com',
    avatar: '/team/tanjim.webp',
    initials: 'TA',
    bio: 'Leads product direction, delivery planning, and cross-functional execution across Bizora.',
    focusAreas: ['Team Leadership', 'Product Delivery', 'System Planning'],
  },
  {
    id: 'jihad-mia',
    name: 'Jihad Mia',
    role: 'Backend Engineer',
    email: 'jihadmia35@gmail.com',
    avatar: '/team/jihad-mia.webp',
    initials: 'JM',
    bio: 'Builds dependable backend services and API workflows that connect Bizora’s business domains.',
    focusAreas: ['Django', 'REST APIs', 'Backend Systems'],
  },
  {
    id: 'soyebuzaman-naim',
    name: 'Soyebuzaman Naim',
    role: 'Domain Expert',
    email: 'soyebuzamannaim@gmail.com',
    avatar: '/team/soyebuzaman-naim.webp',
    initials: 'SN',
    bio: 'Translates real business operations into clear domain rules, workflows, and product requirements.',
    focusAreas: ['Domain Research', 'Business Rules', 'Product Validation'],
  },
  {
    id: 'kazi-azmainur-rahman',
    name: 'Kazi Azmainur Rahman',
    role: 'Backend Engineer',
    email: 'kaziazmainurrahman@gmail.com',
    avatar: '/team/kazi-azmainur-rahman.webp',
    initials: 'KR',
    bio: 'Develops core backend capabilities with a focus on reliable data flows and maintainable service boundaries.',
    focusAreas: ['Backend Architecture', 'Data Workflows', 'Service Reliability'],
  },
  {
    id: 'ismail-hossen',
    name: 'Ismail Hossen',
    role: 'AI/ML Engineer',
    email: 'ismail.hossen.work@gmail.com',
    avatar: '/team/ismail-hossen.webp',
    initials: 'IH',
    bio: 'Designs AI and machine-learning capabilities that turn verified business context into useful decision support.',
    focusAreas: ['Machine Learning', 'Applied AI', 'Decision Intelligence'],
  },
]

export const YC_PITCH_SECTIONS = [
  {
    id: 'problem',
    title: '1. The Problem',
    tagline: 'Emerging Market E-Commerce is Bleeding Margins Across Fragmented Silos',
    summary:
      'In emerging economies like Bangladesh, 80%+ of transactions rely on Cash on Delivery (COD). Fragmented phone channels, unreliable couriers, and duplicate customer identities create severe operational drag.',
    points: [
      {
        title: '35% Return Rates on COD',
        detail:
          'Merchants lose millions in non-refundable courier dispatch fees due to fake orders, unreachable phone numbers, and lack of customer verification.',
      },
      {
        title: 'Identity Fragmentation Across Channels',
        detail:
          'The same customer shops via Facebook Messenger, WhatsApp, telephone calls, and web storefronts using different names and numbers. ERPs fail to link them.',
      },
      {
        title: 'Manual Logistics & Telephony Disconnect',
        detail:
          'Staff spend hours manually re-keying addresses into courier portals (Steadfast/Pathao) and calling customers on mobile phones without conversational context.',
      },
      {
        title: 'AI Hallucination Hazard in Operations',
        detail:
          'Standard LLMs hallucinate discounts, stock counts, and refund transactions when plugged directly into business operations without strict factual guardrails.',
      },
    ],
  },
  {
    id: 'solution',
    title: '2. The Solution',
    tagline: 'Bizora: The Autonomous Enterprise Business Brain',
    summary:
      'Bizora unifies all customer, order, telephony, and logistics signals into an authoritative Knowledge Graph. Deterministic systems establish facts; AI advisory proposes actions that humans approve.',
    points: [
      {
        title: 'Unified Customer 360 & Identity Graph',
        detail:
          'Automated entity resolution clusters phone numbers, delivery addresses, and social handles into single canonical customer profiles.',
      },
      {
        title: 'Deep Local Logistics & Telephony Adapters',
        detail:
          'First-class automated dispatch with Steadfast Courier (one-click booking, live status sync) and Dialyra Telephony (automated IVR, call recording, transcription).',
      },
      {
        title: 'Deterministic Facts + GraphRAG Advisory',
        detail:
          'Factual ground truth is held in PostgreSQL and the Business Graph. The AI Engine retrieves verified context before proposing business actions.',
      },
      {
        title: 'Zero-Risk Action Approval Queue',
        detail:
          'Every AI recommendation (discounts, refunds, priority shipments) requires explicit operator review. No silent mutations to money or records.',
      },
    ],
  },
  {
    id: 'why-now',
    title: '3. Why Now',
    tagline: 'The Perfect Storm of Digital Infrastructure & AI Maturity in South Asia',
    summary:
      'Three macro tailwinds make this the definitive moment to replace legacy ERPs and manual workflows with an autonomous business brain.',
    points: [
      {
        title: 'Courier & Mobile Payment API Standardization',
        detail:
          'APIs for regional logistics (Steadfast, Pathao) and digital wallets (bKash, Nagad) have reached enterprise reliability, enabling end-to-end programmatic automation.',
      },
      {
        title: 'Explosion of Multichannel Social Commerce',
        detail:
          'More than 150,000 merchants in Bangladesh now sell across 4+ digital touchpoints simultaneously, making manual coordination impossible.',
      },
      {
        title: 'Reliable Agentic AI with Deterministic Bounds',
        detail:
          'Modern LLM reasoning combined with knowledge graphs makes autonomous triage and operational dispatch feasible without hallucination risk.',
      },
    ],
  },
  {
    id: 'product-demo',
    title: '4. Product Architecture & Demo Walkthrough',
    tagline: '9 Purpose-Built Workspaces Connected by a Single Authoritative Graph',
    summary:
      'Bizora provides an enterprise-grade operator console designed with high-contrast tokens, WCAG AA compliance, and sub-50ms interaction latency.',
    modules: [
      {
        name: 'Executive Overview',
        description: 'Real-time revenue, order velocity, courier delivery ratios, and system issue triage.',
        badge: 'Executive',
      },
      {
        name: 'Customer 360',
        description:
          'Canonical profile view, linked accounts, retargeting signals, and historical shipments.',
        badge: 'Identity',
      },
      {
        name: 'Commerce & Logistics',
        description: 'Order pipeline with one-click Steadfast dispatch, tracking codes, and status refresh.',
        badge: 'Operations',
      },
      {
        name: 'Dialyra Telephony',
        description: 'Live call monitoring, audio playback, automated transcripts, and sentiment analysis.',
        badge: 'Voice AI',
      },
      {
        name: 'Context & Knowledge Graph',
        description: 'Multi-hop graph traversal, entity path finder, and verified factual evidence panels.',
        badge: 'Graph Engine',
      },
      {
        name: 'AI Studio & Action Review',
        description:
          'Queue of AI-suggested business actions with simulated previews and guardrailed execution.',
        badge: 'AI Safety',
      },
    ],
  },
  {
    id: 'market-opportunity',
    title: '5. Market Opportunity',
    tagline: '$4.2B Addressable Market Across Emerging South Asian Digital Commerce',
    summary:
      'South Asia represents the fastest growing digital commerce corridor in the world, with over 150,000 merchants and 35% YoY digital transaction growth.',
    metrics: [
      {
        label: 'Total Addressable Market (TAM)',
        value: '$4.2B',
        subtitle: 'SMB commerce tooling & operations in South Asia',
      },
      {
        label: 'Serviceable Available Market (SAM)',
        value: '$850M',
        subtitle: 'Multichannel merchants in Bangladesh, Pakistan & regional hubs',
      },
      {
        label: 'Serviceable Obtainable Market (SOM)',
        value: '$120M',
        subtitle: 'High-volume merchants with >500 monthly COD shipments',
      },
      {
        label: 'Active Target Merchants',
        value: '150,000+',
        subtitle: 'Registered online retailers and social commerce sellers',
      },
    ],
  },
  {
    id: 'business-model',
    title: '6. Business Model',
    tagline: 'Predictable SaaS Subscriptions + Value-Accretive Usage Expansion',
    summary:
      'Bizora operates a dual-revenue engine: fixed monthly workspace fees for core operations, combined with usage-based automated logistics and AI telephony credits.',
    tiers: [
      {
        name: 'Starter Workspace',
        price: 'BDT 4,999 / mo',
        subtitle: 'For emerging merchants up to 1,000 monthly orders',
        features: [
          'Up to 5 operator seats',
          'Customer 360 & Identity Resolution',
          'Steadfast Courier integration',
          'Standard Overview analytics',
        ],
      },
      {
        name: 'Growth Enterprise',
        price: 'BDT 14,999 / mo',
        subtitle: 'For scaling brands handling 5,000+ monthly orders',
        popular: true,
        features: [
          'Unlimited operator seats',
          'Dialyra Telephony & Call Transcripts',
          'Automated Fraud Prevention Engine',
          'AI Studio Action Proposals',
          'Full Knowledge Graph Traversal',
        ],
      },
      {
        name: 'Custom Platform',
        price: 'BDT 49,999 / mo',
        subtitle: 'For large retail chains and distributor networks',
        features: [
          'Dedicated high-throughput database clusters',
          'Custom ERP & WMS integrations',
          'SLA guaranteed 99.99% uptime',
          '24/7 dedicated engineering support',
        ],
      },
    ],
  },
  {
    id: 'traction',
    title: '7. Live Traction & Real-Time Telemetry',
    tagline: 'Live-Synced Platform Proof Driven by Authoritative Application Data',
    summary:
      'Bizora is currently handling live production workloads across multiple enterprise tenants in Bangladesh.',
    statsNote: 'Values below are synced in real time from the active platform state.',
  },
  {
    id: 'competition',
    title: '8. Competitive Landscape',
    tagline: 'Why Bizora Wins: The Only Localized Autonomous Graph Brain',
    summary:
      'Generic global ERPs ignore local payment and courier logistics. Point tools remain fragmented. Bizora is built from the ground up for emerging market reality.',
    matrix: [
      {
        feature: 'Unified Identity Graph across Phone & Social',
        bizora: 'Yes (Native)',
        shopify: 'No (Addon required)',
        sapOdoo: 'No (Siloed)',
        pointTools: 'No',
      },
      {
        feature: 'Native Steadfast Courier 1-Click Dispatch',
        bizora: 'Yes (Native)',
        shopify: 'No (Manual export)',
        sapOdoo: 'No',
        pointTools: 'Basic API',
      },
      {
        feature: 'Dialyra Telephony & Voice Transcripts',
        bizora: 'Yes (Native)',
        shopify: 'No',
        sapOdoo: 'No',
        pointTools: 'External call center',
      },
      {
        feature: 'Deterministic Business Guardrails for AI',
        bizora: 'Yes (Strict)',
        shopify: 'No (Chatbot only)',
        sapOdoo: 'No AI',
        pointTools: 'None',
      },
      {
        feature: 'BDT Currency & Local Tax Compliance',
        bizora: 'Yes (Built-in)',
        shopify: 'Partial',
        sapOdoo: 'Expensive customization',
        pointTools: 'Varies',
      },
      {
        feature: 'Sub-50ms Enterprise UI Interaction Latency',
        bizora: 'Yes (Next.js 16)',
        shopify: 'Moderate',
        sapOdoo: 'Slow legacy UI',
        pointTools: 'Varies',
      },
    ],
  },
  {
    id: 'unique-advantage',
    title: '9. Unique Advantage (Our Moat)',
    tagline: 'Defensible Technical & Operational Advantages',
    summary:
      'Our competitive moat deepens with every order, phone call, and delivery recorded in the Knowledge Graph.',
    moats: [
      {
        title: 'Proprietary Identity Resolution Engine',
        description:
          'Our phoneme-aware Bengali and English string distance algorithms link customer identities even across spelling variants and shared household numbers.',
      },
      {
        title: 'Deep Local Integration Infrastructure',
        description:
          'Native adapters for Steadfast Courier, Dialyra Telephony, and regional gateways remove friction that foreign competitors cannot bridge.',
      },
      {
        title: 'Deterministic GraphRAG Architecture',
        description:
          'By strictly isolating authoritative facts from speculative AI advisory, Bizora guarantees enterprise trust and zero unauthorized mutations.',
      },
      {
        title: 'High Switching Costs via Graph Data',
        description:
          'Once a merchant’s historical customer journeys, courier delivery scores, and conflict resolutions are recorded in Bizora, moving away is impossible.',
      },
    ],
  },
  {
    id: 'gtm',
    title: '10. Go-To-Market Strategy',
    tagline: 'A 3-Pillar Flywheel Focused on Merchant Density',
    summary:
      'We acquire merchants rapidly through courier logistics partnerships, developer ecosystem integrations, and community sales agencies.',
    pillars: [
      {
        phase: 'Phase 1: Logistics Partner Co-Selling',
        description:
          'Direct referral integrations with courier networks (Steadfast). High-volume merchants with high return rates are funneled into Bizora to reduce losses.',
      },
      {
        phase: 'Phase 2: App Ecosystem & Webhook Ingestion',
        description:
          'One-click sync for WooCommerce, Shopify, Facebook Shops, and WhatsApp Business API. Merchants onboard their catalog in under 5 minutes.',
      },
      {
        phase: 'Phase 3: Agency & Developer Network',
        description:
          'Certified implementation partners and digital agencies earning revenue share for deploying Bizora to retail clients across South Asia.',
      },
    ],
  },
  {
    id: 'team',
    title: '11. Team & Core Architects',
    tagline: 'World-Class Systems Engineers, Product Builders & Domain Specialists',
    summary:
      'Our team blends deep expertise in distributed systems, Next.js architecture, knowledge graph theory, and emerging market logistics.',
  },
  {
    id: 'vision',
    title: '12. Our Vision',
    tagline: 'The Autonomous Operating System for Global Emerging Market Commerce',
    summary:
      'We believe the next generation of global commerce will be powered by autonomous systems that eliminate human coordination bottlenecks. Bizora is building the infrastructure that powers that future.',
    quote:
      '“Commerce should move as fast as human thought, with software that resolves identity, handles logistics, and protects margins autonomously.”',
  },
]

export const TECHNICAL_SECTIONS = [
  {
    id: 'tech-overview',
    title: 'Technical Whitepaper: System Overview & Architecture Philosophy',
    summary:
      'Bizora is structured around a strict engineering boundary: Deterministic business systems establish facts and metrics; AI advisory never silently creates authoritative records without human approval.',
  },
  {
    id: 'architecture-diagram',
    title: 'System Architecture & Component Topography',
    summary:
      'An end-to-end breakdown of the frontend client proxy, Django REST Framework services, PostgreSQL authoritative storage, and external partner APIs.',
  },
  {
    id: 'data-flow',
    title: 'Event Data Flow & Graph Traversal Pipeline',
    summary:
      'Tracing the exact path of an inbound event: Webhook Ingestion → Canonicalization → Graph Linkage → GraphRAG Contextualization → AI Proposal → Approval → Steadfast / Dialyra Dispatch.',
  },
  {
    id: 'tech-stack',
    title: 'Authoritative Technology Stack',
    layers: [
      {
        layer: 'Frontend Client & Presentation',
        technologies:
          'Next.js 16.4.5 (Turbopack, App Router), React 19, Vanilla CSS Design Tokens, Lucide Icons, Radix UI Primitives, Recharts.',
        rationale:
          'Sub-second compile times, zero client CSS bloat, WCAG 2.2 AA contrast compliance, pure JavaScript simplicity without compilation drift.',
      },
      {
        layer: 'API Gateway & In-Memory Proxy',
        technologies:
          'Same-origin Next.js Route Handler Proxy (/api/backend/[...path]), Cookie forwarding, CSRF token validation, Idempotency-Key handling.',
        rationale:
          'Prevents CORS issues, protects backend service endpoints, sanitizes query parameters against injection, and manages retry idempotency.',
      },
      {
        layer: 'Backend Application Services',
        technologies: 'Python 3.12, Django 4.2 LTS, Django REST Framework 3.15.2, Psycopg 3.',
        rationale:
          'Rock-solid transaction guarantees, enterprise ORM reliability, high performance with Python 3.12 runtime improvements.',
      },
      {
        layer: 'Authoritative Storage & Graph',
        technologies:
          'PostgreSQL 16 with relational indexing, JSONB attributes, and optimized recursive graph traversal queries.',
        rationale:
          'Authoritative facts remain strictly in ACID storage. SQLite is strictly used for lightweight local test suites.',
      },
      {
        layer: 'External Partner Ecosystem',
        technologies:
          'Steadfast Courier REST API, Dialyra SIP Telephony API, bKash & Nagad Payment Webhooks.',
        rationale:
          'Direct native adapters with payload masking, error normalization, and safe retry semantics.',
      },
    ],
  },
  {
    id: 'api-reference',
    title: 'API Documentation & Endpoint Contracts',
    summary:
      'Bizora provides an authenticated, role-guarded RESTful API designed with explicit query filtering and RFC 4122 v4 Idempotency.',
    endpoints: [
      {
        method: 'GET',
        path: '/api/businesses/{id}/overview/summary/',
        auth: 'Session / Token',
        role: 'VIEWER+',
        description: 'Retrieve executive KPIs, total revenue, order count, and active issue counts.',
        response: '{ "kpis": { "revenue": "48290400.00", "orders": 48290 }, "trends": [...] }',
      },
      {
        method: 'POST',
        path: '/api/businesses/{id}/shipping/steadfast/send/',
        auth: 'Session / CSRF',
        role: 'OPERATOR+',
        headers: 'Idempotency-Key: <UUIDv4>',
        description: 'Dispatch an order consignment to Steadfast Courier with automated COD calculation.',
        response: '{ "status": "CONFIRMED", "consignment_id": 842019, "tracking_code": "STDF-842019" }',
      },
      {
        method: 'GET',
        path: '/api/businesses/{id}/identity/canonical/',
        auth: 'Session',
        role: 'OPERATOR+',
        description: 'Query canonical customer profiles resolved by the identity graph engine.',
        response: '{ "count": 24190, "results": [ { "id": 1, "primary_phone": "01700000000", ... } ] }',
      },
      {
        method: 'POST',
        path: '/api/businesses/{id}/ai/actions/{action_id}/execute/',
        auth: 'Session / CSRF',
        role: 'OPERATOR+',
        headers: 'Idempotency-Key: <UUIDv4>',
        description: 'Execute an operator-approved AI action with deterministic execution bounds.',
        response: '{ "execution_state": "COMPLETED", "executed_at": "2026-11-20T16:00:00Z" }',
      },
      {
        method: 'GET',
        path: '/api/businesses/{id}/telephony/calls/',
        auth: 'Session',
        role: 'OPERATOR+',
        description: 'List recorded Dialyra telephony calls, customer sentiment, and duration.',
        response:
          '{ "results": [ { "call_id": "CALL-901", "duration_seconds": 142, "status": "COMPLETED" } ] }',
      },
    ],
  },
  {
    id: 'security-data-privacy',
    title: 'Security, RBAC & Customer Privacy Guardrails',
    summary:
      'Security is enforced at the server data layer. Customer privacy is preserved with automated PII masking and untrusted input sanitization.',
    points: [
      {
        title: 'Role-Based Access Control (RBAC)',
        detail:
          'Four strictly enforced tiers: OWNER (full tenant control), MANAGER (policy & configuration), OPERATOR (daily dispatch & customer actions), and VIEWER (read-only audit).',
      },
      {
        title: 'Untrusted Customer Data Wrappers',
        detail:
          'Customer message text from SMS, WhatsApp, and social chat is enclosed in `<untrusted_customer_data>` tags, sanitized, and stripped before rendering to prevent prompt injection and XSS.',
      },
      {
        title: 'Session Authentication & CSRF Protection',
        detail:
          'All mutations require HTTP-only secure session cookies and synchronized Django CSRF tokens forwarded through the same-origin Next.js proxy.',
      },
      {
        title: 'RFC 4122 v4 Idempotency Guarantees',
        detail:
          'Every creation and external mutation (Steadfast booking, refund, AI execution) attaches a persistent client-generated Idempotency-Key that is reused on network retry.',
      },
    ],
  },
  {
    id: 'roadmap',
    title: 'Product Roadmap & Engineering Milestones',
    milestones: [
      {
        quarter: 'Q1 2026',
        title: 'Foundation & Core Architecture',
        status: 'SHIPPED',
        deliverables: [
          'Next.js 16 + React 19 Frontend Overhaul',
          'Design Token System (WCAG AA)',
          'PostgreSQL Authoritative Domain Models',
          'Identity Resolution V1',
        ],
      },
      {
        quarter: 'Q2 2026',
        title: 'Deep Ecosystem Integrations',
        status: 'SHIPPED',
        deliverables: [
          'Native Steadfast Courier Dispatch',
          'Dialyra Voice Telephony & Transcripts',
          'Knowledge Graph Traversal UI',
          'AI Action Review Queue with Simulated Preview',
        ],
      },
      {
        quarter: 'Q3 2026',
        title: 'Autonomous Social Commerce & Multimodal Voice',
        status: 'IN_PROGRESS',
        deliverables: [
          'WhatsApp Business Conversational Agent',
          'Automated Bengali Dialect Speech Recognition',
          'Predictive Inventory Restocking',
          'Multi-tenant Webhook Ingestion Engine',
        ],
      },
      {
        quarter: 'Q4 2026',
        title: 'Multi-Agent Network & Cross-Border Expansion',
        status: 'PLANNED',
        deliverables: [
          'Cross-border settlements (bKash / Nagad / Stripe)',
          'Autonomous Supplier Bidding Agents',
          'Distributed Edge Caching for Multi-Country Latency <20ms',
        ],
      },
    ],
  },
  {
    id: 'changelog',
    title: 'Changelog & Semantic Version History',
    releases: [
      {
        version: 'v2.4.0',
        date: '2026-11-18',
        highlights: [
          'Shipped Live /docs module with YC Pitch Deck, Deep Technical Whitepaper, and Admin Scheduling Controls.',
          'Added Steadfast Courier consignment automated dispatch with COD validation.',
          'Enabled Dialyra Telephony audio call inspection and live status streaming.',
          'Resolved 100% of UI accessibility gates across all 8 workspaces.',
        ],
      },
      {
        version: 'v2.3.0',
        date: '2026-11-12',
        highlights: [
          'Engineered Knowledge Graph path finder and interactive traversal snapshots.',
          'Introduced Retargeting Context and Customer 360 unified journey views.',
          'Shipped Simulation & Sandbox mode for testing integrations safely.',
        ],
      },
      {
        version: 'v2.2.0',
        date: '2026-11-05',
        highlights: [
          'Refactored API client with robust normalizeError handling for all 7 DRF error shapes.',
          'Enforced strict RFC 4122 v4 Idempotency Key rotation on payload change.',
          'Standardized ISO currency formatting for BDT transactions.',
        ],
      },
    ],
  },
]
