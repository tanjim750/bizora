'use client'

import React, { useState } from 'react'
import { Server, Database, Cpu, Globe, ArrowRight, Layers, Workflow, Shield } from 'lucide-react'

export function DocsArchitectureDiagram() {
  const [activeNode, setActiveNode] = useState('nextjs')

  const nodes = {
    nextjs: {
      title: 'Next.js 16.4 Enterprise UI',
      tech: 'React 19, Turbopack, App Router, CSS Tokens',
      desc: 'High-contrast enterprise UI running at sub-50ms interaction latency. Uses same-origin route handlers to proxy backend calls securely.',
    },
    proxy: {
      title: 'Same-Origin Gateway Proxy',
      tech: '/api/backend/[...path] Route Handler',
      desc: 'Protects backend origin, handles cookie forwarding, enforces CSRF token synchronization, and attaches client-generated RFC 4122 v4 Idempotency keys.',
    },
    drf: {
      title: 'Django REST Framework 3.15 Core',
      tech: 'Python 3.12, Django 4.2 LTS',
      desc: 'Authoritative transaction layer. Enforces strict schema validations, RBAC permissions, and domain constraints. Zero direct client mutations.',
    },
    services: {
      title: 'Domain Engine Subsystems',
      tech: 'Identity Graph, Steadfast Courier, Dialyra Voice, AI Review Queue',
      desc: 'Modular business logic engines. Deterministic facts are separated from AI advisory proposals. No silent mutations to money or orders.',
    },
    postgres: {
      title: 'PostgreSQL 16 Authoritative ACID DB',
      tech: 'Relational Models, JSONB Graph Nodes, Tracing Indexes',
      desc: 'The single source of truth for all business entities, customer relationships, order history, and audit logs.',
    },
    partners: {
      title: 'External Partner Ecosystem',
      tech: 'Steadfast Courier API, Dialyra Telephony SIP, bKash / Nagad',
      desc: 'Native adapters for emerging market commerce logistics and telephony. Automatically records attempts and handles idempotent retries.',
    },
  }

  return (
    <div className="docs-diagram-container">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-4)',
          borderBottom: '1px solid var(--color-border)',
          paddingBottom: 'var(--space-3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Layers size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
          <strong style={{ fontSize: 'var(--text-body-sm)' }}>
            Interactive Architecture Topography (UI → Gateway → Core Services → DB)
          </strong>
        </div>
        <span
          style={{
            fontSize: 'var(--text-caption)',
            color: 'var(--color-text-muted)',
            fontFamily: 'var(--font-plex-mono)',
          }}
        >
          Click a node to inspect
        </span>
      </div>

      {/* Interactive SVG Diagram */}
      <svg
        viewBox="0 0 860 300"
        className="docs-diagram-svg"
        role="img"
        aria-label="Bizora End-to-End System Architecture Diagram"
      >
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="6"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 8 5 L 0 9 z" fill="var(--color-border-strong)" />
          </marker>
          <filter id="card-shadow" x="-5%" y="-5%" width="110%" height="115%">
            <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.08" />
          </filter>
        </defs>

        {/* Connecting Lines */}
        <line
          x1="130"
          y1="90"
          x2="190"
          y2="90"
          stroke="var(--color-border-strong)"
          strokeWidth="2"
          markerEnd="url(#arrow)"
        />
        <line
          x1="330"
          y1="90"
          x2="390"
          y2="90"
          stroke="var(--color-border-strong)"
          strokeWidth="2"
          markerEnd="url(#arrow)"
        />
        <line
          x1="530"
          y1="90"
          x2="590"
          y2="90"
          stroke="var(--color-border-strong)"
          strokeWidth="2"
          markerEnd="url(#arrow)"
        />
        <line
          x1="660"
          y1="130"
          x2="660"
          y2="180"
          stroke="var(--color-border-strong)"
          strokeWidth="2"
          markerEnd="url(#arrow)"
        />
        <line
          x1="460"
          y1="130"
          x2="460"
          y2="180"
          stroke="var(--color-primary)"
          strokeWidth="2"
          strokeDasharray="4 4"
          markerEnd="url(#arrow)"
        />

        {/* Node 1: Next.js Frontend */}
        <g onClick={() => setActiveNode('nextjs')} style={{ cursor: 'pointer' }} className="docs-svg-node">
          <rect
            x="10"
            y="50"
            width="120"
            height="80"
            rx="8"
            fill={activeNode === 'nextjs' ? 'var(--color-primary-subtle)' : 'var(--color-surface)'}
            stroke={activeNode === 'nextjs' ? 'var(--color-primary)' : 'var(--color-border)'}
            strokeWidth={activeNode === 'nextjs' ? '2' : '1'}
            filter="url(#card-shadow)"
          />
          <text x="70" y="82" textAnchor="middle" fill="var(--color-text)" fontWeight="600" fontSize="12">
            Next.js 16 UI
          </text>
          <text x="70" y="98" textAnchor="middle" fill="var(--color-text-muted)" fontSize="10">
            React 19 Tokens
          </text>
          <text x="70" y="112" textAnchor="middle" fill="var(--color-primary)" fontSize="9" fontWeight="600">
            Port 3000
          </text>
        </g>

        {/* Node 2: Route Handler Proxy */}
        <g onClick={() => setActiveNode('proxy')} style={{ cursor: 'pointer' }} className="docs-svg-node">
          <rect
            x="190"
            y="50"
            width="140"
            height="80"
            rx="8"
            fill={activeNode === 'proxy' ? 'var(--color-primary-subtle)' : 'var(--color-surface)'}
            stroke={activeNode === 'proxy' ? 'var(--color-primary)' : 'var(--color-border)'}
            strokeWidth={activeNode === 'proxy' ? '2' : '1'}
            filter="url(#card-shadow)"
          />
          <text x="260" y="82" textAnchor="middle" fill="var(--color-text)" fontWeight="600" fontSize="12">
            API Gateway Proxy
          </text>
          <text x="260" y="98" textAnchor="middle" fill="var(--color-text-muted)" fontSize="10">
            CSRF + Idempotency
          </text>
          <text x="260" y="112" textAnchor="middle" fill="var(--color-primary)" fontSize="9" fontWeight="600">
            /api/backend/*
          </text>
        </g>

        {/* Node 3: Django REST Framework Core */}
        <g onClick={() => setActiveNode('drf')} style={{ cursor: 'pointer' }} className="docs-svg-node">
          <rect
            x="390"
            y="50"
            width="140"
            height="80"
            rx="8"
            fill={activeNode === 'drf' ? 'var(--color-primary-subtle)' : 'var(--color-surface)'}
            stroke={activeNode === 'drf' ? 'var(--color-primary)' : 'var(--color-border)'}
            strokeWidth={activeNode === 'drf' ? '2' : '1'}
            filter="url(#card-shadow)"
          />
          <text x="460" y="82" textAnchor="middle" fill="var(--color-text)" fontWeight="600" fontSize="12">
            Django REST Core
          </text>
          <text x="460" y="98" textAnchor="middle" fill="var(--color-text-muted)" fontSize="10">
            Python 3.12 / DRF
          </text>
          <text x="460" y="112" textAnchor="middle" fill="var(--color-primary)" fontSize="9" fontWeight="600">
            Port 8000
          </text>
        </g>

        {/* Node 4: Domain Subsystems */}
        <g onClick={() => setActiveNode('services')} style={{ cursor: 'pointer' }} className="docs-svg-node">
          <rect
            x="590"
            y="50"
            width="140"
            height="80"
            rx="8"
            fill={activeNode === 'services' ? 'var(--color-primary-subtle)' : 'var(--color-surface)'}
            stroke={activeNode === 'services' ? 'var(--color-primary)' : 'var(--color-border)'}
            strokeWidth={activeNode === 'services' ? '2' : '1'}
            filter="url(#card-shadow)"
          />
          <text x="660" y="82" textAnchor="middle" fill="var(--color-text)" fontWeight="600" fontSize="12">
            Domain Services
          </text>
          <text x="660" y="98" textAnchor="middle" fill="var(--color-text-muted)" fontSize="10">
            Graph / AI / Logistics
          </text>
          <text x="660" y="112" textAnchor="middle" fill="var(--color-primary)" fontSize="9" fontWeight="600">
            Deterministic Engine
          </text>
        </g>

        {/* Node 5: PostgreSQL Database */}
        <g onClick={() => setActiveNode('postgres')} style={{ cursor: 'pointer' }} className="docs-svg-node">
          <rect
            x="590"
            y="180"
            width="140"
            height="80"
            rx="8"
            fill={activeNode === 'postgres' ? 'var(--color-primary-subtle)' : 'var(--color-surface)'}
            stroke={activeNode === 'postgres' ? 'var(--color-primary)' : 'var(--color-border)'}
            strokeWidth={activeNode === 'postgres' ? '2' : '1'}
            filter="url(#card-shadow)"
          />
          <text x="660" y="212" textAnchor="middle" fill="var(--color-text)" fontWeight="600" fontSize="12">
            PostgreSQL 16 DB
          </text>
          <text x="660" y="228" textAnchor="middle" fill="var(--color-text-muted)" fontSize="10">
            Authoritative ACID State
          </text>
          <text x="660" y="242" textAnchor="middle" fill="var(--color-primary)" fontSize="9" fontWeight="600">
            JSONB + Indexes
          </text>
        </g>

        {/* Node 6: External Partners */}
        <g onClick={() => setActiveNode('partners')} style={{ cursor: 'pointer' }} className="docs-svg-node">
          <rect
            x="390"
            y="180"
            width="140"
            height="80"
            rx="8"
            fill={activeNode === 'partners' ? 'var(--color-primary-subtle)' : 'var(--color-surface)'}
            stroke={activeNode === 'partners' ? 'var(--color-primary)' : 'var(--color-border)'}
            strokeWidth={activeNode === 'partners' ? '2' : '1'}
            filter="url(#card-shadow)"
          />
          <text x="460" y="212" textAnchor="middle" fill="var(--color-text)" fontWeight="600" fontSize="12">
            External Partners
          </text>
          <text x="460" y="228" textAnchor="middle" fill="var(--color-text-muted)" fontSize="10">
            Steadfast & Dialyra
          </text>
          <text x="460" y="242" textAnchor="middle" fill="var(--color-primary)" fontSize="9" fontWeight="600">
            REST & SIP Voice
          </text>
        </g>
      </svg>

      {/* Selected Node Details Box */}
      {activeNode && nodes[activeNode] && (
        <div
          style={{
            marginTop: 'var(--space-3)',
            padding: 'var(--space-3) var(--space-4)',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{nodes[activeNode].title}</span>
            <span
              style={{
                fontSize: 'var(--text-caption)',
                fontFamily: 'var(--font-plex-mono)',
                color: 'var(--color-primary-text)',
              }}
            >
              {nodes[activeNode].tech}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: 'var(--text-body-sm)', color: 'var(--color-text-secondary)' }}>
            {nodes[activeNode].desc}
          </p>
        </div>
      )}
    </div>
  )
}

export function DocsDataFlowDiagram() {
  const steps = [
    {
      num: '01',
      title: 'Inbound Ingestion',
      detail:
        'Webhooks from order storefronts, SMS inquiries, WhatsApp messages, and Dialyra telephony incoming calls.',
    },
    {
      num: '02',
      title: 'Normalization & Masking',
      detail:
        'Phone numbers formatted, customer message wrapped in <untrusted_customer_data> tags to block prompt injection.',
    },
    {
      num: '03',
      title: 'Entity Resolution & Graph',
      detail:
        'Deterministic phoneme clustering links disparate orders and phones to the single canonical customer profile.',
    },
    {
      num: '04',
      title: 'GraphRAG Contextualization',
      detail:
        'AI Engine retrieves verified factual evidence (delivery track record, order frequency) from PostgreSQL.',
    },
    {
      num: '05',
      title: 'AI Action Proposal',
      detail:
        'AI formulates a structured business action (e.g. issue 10% coupon, approve Steadfast express courier).',
    },
    {
      num: '06',
      title: 'Human Review & Execution',
      detail:
        'Operator confirms action in AI Studio queue. External API is invoked with a persistent Idempotency-Key.',
    },
  ]

  return (
    <div className="docs-diagram-container">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          marginBottom: 'var(--space-4)',
          borderBottom: '1px solid var(--color-border)',
          paddingBottom: 'var(--space-3)',
        }}
      >
        <Workflow size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
        <strong style={{ fontSize: 'var(--text-body-sm)' }}>
          Autonomous Event Lifecycle & Data Flow (Ingestion → Graph → AI → Review → Execution)
        </strong>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 'var(--space-3)',
        }}
      >
        {steps.map((st) => (
          <div
            key={st.num}
            style={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-4)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-2)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span
                style={{
                  fontSize: 'var(--text-caption)',
                  fontWeight: 700,
                  fontFamily: 'var(--font-plex-mono)',
                  color: 'var(--color-primary)',
                }}
              >
                STEP {st.num}
              </span>
              <Shield size={14} style={{ color: 'var(--color-text-muted)' }} aria-hidden="true" />
            </div>
            <strong style={{ fontSize: 'var(--text-body-sm)', color: 'var(--color-text)' }}>
              {st.title}
            </strong>
            <p
              style={{
                margin: 0,
                fontSize: 'var(--text-caption)',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.5,
              }}
            >
              {st.detail}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
