'use client'

import React, { useState } from 'react'
import {
  Server,
  Database,
  Cpu,
  Layers,
  Code2,
  Lock,
  GitBranch,
  Shield,
  FileCode,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react'
import { DocsArchitectureDiagram, DocsDataFlowDiagram } from './DocsDiagrams'

export function DocsTechnical({ technicalSections = [], liveFeatureMatrix = [] }) {
  const [selectedFeatureFilter, setSelectedFeatureFilter] = useState('ALL')
  const [expandedEndpoint, setExpandedEndpoint] = useState(null)

  const getSection = (id) => technicalSections.find((s) => s.id === id) || {}

  const techOverview = getSection('tech-overview')
  const techStack = getSection('tech-stack')
  const apiDocs = getSection('api-reference')
  const security = getSection('security-data-privacy')
  const roadmap = getSection('roadmap')
  const changelog = getSection('changelog')

  const filteredFeatures =
    selectedFeatureFilter === 'ALL'
      ? liveFeatureMatrix
      : liveFeatureMatrix.filter((f) => f.status === selectedFeatureFilter)

  return (
    <div
      className="docs-tech-container"
      style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}
    >
      {/* B. Product Overview & Architectural Law */}
      <section id="tech-overview" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            System Architecture
          </span>
          <h2 className="docs-card-title">Technical Whitepaper: System Overview & Foundations</h2>
          <div className="docs-card-tagline">
            Deterministic Business Facts vs Non-Hallucinatory AI Advisory
          </div>
          <p className="docs-card-summary">
            {techOverview.summary ||
              'Bizora is structured around a strict engineering boundary: Deterministic business systems establish facts and metrics; AI advisory never silently creates authoritative records without human approval.'}
          </p>
        </div>

        <div className="docs-points-grid">
          <div className="docs-point-box">
            <strong
              style={{
                fontSize: 'var(--text-body-sm)',
                color: 'var(--color-text)',
                display: 'block',
                marginBottom: 4,
              }}
            >
              Target Operators
            </strong>
            <p
              style={{
                margin: 0,
                fontSize: 'var(--text-body-sm)',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.5,
              }}
            >
              Platform Owners, Logistics Operations Managers, Support Dispatch Agents, and BI Data Analysts.
            </p>
          </div>
          <div className="docs-point-box">
            <strong
              style={{
                fontSize: 'var(--text-body-sm)',
                color: 'var(--color-text)',
                display: 'block',
                marginBottom: 4,
              }}
            >
              Zero-Mutation Invariant
            </strong>
            <p
              style={{
                margin: 0,
                fontSize: 'var(--text-body-sm)',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.5,
              }}
            >
              AI models generate structured proposals. No database records (orders, payments, refunds) are
              created without an explicit operator click.
            </p>
          </div>
          <div className="docs-point-box">
            <strong
              style={{
                fontSize: 'var(--text-body-sm)',
                color: 'var(--color-text)',
                display: 'block',
                marginBottom: 4,
              }}
            >
              Same-Origin Proxy Seam
            </strong>
            <p
              style={{
                margin: 0,
                fontSize: 'var(--text-body-sm)',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.5,
              }}
            >
              Frontend client components never call external or backend APIs directly. All traffic is proxied
              through Next.js route handlers with CSRF validation.
            </p>
          </div>
        </div>
      </section>

      {/* C. Live Feature Matrix */}
      <section id="feature-matrix" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Live System State
          </span>
          <h2 className="docs-card-title">Live Feature Matrix & Implementation Status</h2>
          <div className="docs-card-tagline">
            Synchronized directly with the application codebase and active modules
          </div>
        </div>

        {/* Status Filter Tabs */}
        <div
          style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)', flexWrap: 'wrap' }}
        >
          {['ALL', 'LIVE', 'BETA', 'IN_DEV', 'PLANNED'].map((st) => (
            <button
              key={st}
              type="button"
              className={`docs-mode-tab ${selectedFeatureFilter === st ? 'active' : ''}`}
              onClick={() => setSelectedFeatureFilter(st)}
            >
              {st === 'ALL' ? 'All Features' : st}
              <span style={{ fontSize: 'var(--text-caption)', opacity: 0.7 }}>
                (
                {st === 'ALL'
                  ? liveFeatureMatrix.length
                  : liveFeatureMatrix.filter((f) => f.status === st).length}
                )
              </span>
            </button>
          ))}
        </div>

        <div className="docs-table-wrapper">
          <table className="docs-table">
            <thead>
              <tr>
                <th>Domain</th>
                <th>Feature Capability</th>
                <th>Status</th>
                <th>Classification</th>
                <th>Engine Version</th>
                <th>Contract Coverage</th>
              </tr>
            </thead>
            <tbody>
              {filteredFeatures.map((f) => (
                <tr key={f.name}>
                  <td>
                    <strong>{f.domain}</strong>
                  </td>
                  <td>
                    <div>
                      <strong>{f.name}</strong>
                    </div>
                    <div style={{ fontSize: 'var(--text-caption)', color: 'var(--color-text-muted)' }}>
                      {f.description}
                    </div>
                  </td>
                  <td>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-full)',
                        fontSize: 'var(--text-caption)',
                        fontWeight: 600,
                        background:
                          f.status === 'LIVE'
                            ? 'var(--color-success-subtle)'
                            : f.status === 'BETA'
                              ? 'var(--color-info-subtle)'
                              : 'var(--color-surface-subtle)',
                        color:
                          f.status === 'LIVE'
                            ? 'var(--color-success-text)'
                            : f.status === 'BETA'
                              ? 'var(--color-info-text)'
                              : 'var(--color-text-muted)',
                        border: '1px solid var(--color-border)',
                      }}
                    >
                      {f.status}
                    </span>
                  </td>
                  <td>
                    <code>{f.badge}</code>
                  </td>
                  <td>
                    <code style={{ fontFamily: 'var(--font-plex-mono)' }}>{f.version}</code>
                  </td>
                  <td>{f.coverage}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* D. Architecture Diagram */}
      <section id="architecture" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            System Blueprint
          </span>
          <h2 className="docs-card-title">Interactive Architecture Diagram</h2>
          <div className="docs-card-tagline">
            Layered topology showing Next.js App Router, Django REST, and Authoritative PostgreSQL
          </div>
        </div>

        <DocsArchitectureDiagram />
      </section>

      {/* E. Data Flow Diagram */}
      <section id="data-flow" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Event Lifecycle
          </span>
          <h2 className="docs-card-title">Autonomous Data Flow & Graph Traversal</h2>
          <div className="docs-card-tagline">
            Step-by-step tracing of incoming webhooks to deterministic external dispatch
          </div>
        </div>

        <DocsDataFlowDiagram />
      </section>

      {/* F. Technology Stack */}
      <section id="tech-stack" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Technology Stack
          </span>
          <h2 className="docs-card-title">Authoritative Technology Stack</h2>
          <div className="docs-card-tagline">
            Modern, maintainable, enterprise stack with high performance and zero unnecessary dependencies
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {techStack.layers?.map((layer) => (
            <div
              key={layer.layer}
              style={{
                background: 'var(--color-surface-subtle)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-4)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: 4,
                }}
              >
                <strong style={{ fontSize: 'var(--text-body)', color: 'var(--color-text)' }}>
                  {layer.layer}
                </strong>
                <span
                  style={{
                    fontSize: 'var(--text-caption)',
                    color: 'var(--color-primary-text)',
                    fontWeight: 600,
                  }}
                >
                  Verified Layer
                </span>
              </div>
              <p
                style={{
                  margin: '0 0 var(--space-2) 0',
                  fontSize: 'var(--text-body-sm)',
                  fontFamily: 'var(--font-plex-mono)',
                  color: 'var(--color-primary)',
                }}
              >
                {layer.technologies}
              </p>
              <p
                style={{
                  margin: 0,
                  fontSize: 'var(--text-body-sm)',
                  color: 'var(--color-text-secondary)',
                  lineHeight: 1.5,
                }}
              >
                <strong>Architectural Rationale:</strong> {layer.rationale}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* G. API Documentation */}
      <section id="api-documentation" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            API Reference
          </span>
          <h2 className="docs-card-title">API Documentation & Verified Contracts</h2>
          <div className="docs-card-tagline">
            Full endpoint specifications with role requirements, auth model, and idempotency
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {apiDocs.endpoints?.map((ep, idx) => {
            const isExpanded = expandedEndpoint === idx
            return (
              <div key={ep.path} className="docs-api-card">
                <div
                  className="docs-api-header"
                  onClick={() => setExpandedEndpoint(isExpanded ? null : idx)}
                  style={{ cursor: 'pointer' }}
                >
                  <span
                    className={`docs-method-badge ${ep.method === 'GET' ? 'docs-method-get' : 'docs-method-post'}`}
                  >
                    {ep.method}
                  </span>
                  <span className="docs-api-path">{ep.path}</span>
                  <span
                    style={{
                      marginLeft: 'auto',
                      fontSize: 'var(--text-caption)',
                      color: 'var(--color-text-muted)',
                      fontFamily: 'var(--font-plex-mono)',
                    }}
                  >
                    Role: {ep.role}
                  </span>
                </div>

                <p className="docs-api-desc">{ep.description}</p>

                <div className="docs-api-meta">
                  <span>Auth: {ep.auth}</span>
                  {ep.headers && (
                    <span>
                      Header: <code>{ep.headers}</code>
                    </span>
                  )}
                </div>

                {/* Response Preview */}
                <div style={{ marginTop: 'var(--space-3)' }}>
                  <div
                    style={{
                      fontSize: 'var(--text-caption)',
                      fontWeight: 600,
                      color: 'var(--color-text-muted)',
                      marginBottom: 4,
                    }}
                  >
                    SAMPLE JSON RESPONSE
                  </div>
                  <pre
                    style={{
                      margin: 0,
                      padding: 'var(--space-3)',
                      background: 'var(--color-surface)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 'var(--text-caption)',
                      fontFamily: 'var(--font-plex-mono)',
                      color: 'var(--color-text)',
                      overflowX: 'auto',
                    }}
                  >
                    {ep.response}
                  </pre>
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* L. Security, RBAC & Privacy */}
      <section id="security" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Security & Governance
          </span>
          <h2 className="docs-card-title">Security Architecture, RBAC & PII Masking</h2>
          <div className="docs-card-tagline">
            Server-enforced access controls, CSRF synchronization, and customer data isolation
          </div>
        </div>

        <div className="docs-points-grid">
          {security.points?.map((pt) => (
            <div key={pt.title} className="docs-point-box">
              <div className="docs-point-title">
                <Shield size={16} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
                <span>{pt.title}</span>
              </div>
              <p className="docs-point-desc">{pt.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* J. Roadmap */}
      <section id="roadmap" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Engineering Roadmap
          </span>
          <h2 className="docs-card-title">Product Roadmap & Milestones</h2>
          <div className="docs-card-tagline">
            Quarterly engineering progression from foundation to autonomous multi-agent networks
          </div>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 'var(--space-4)',
          }}
        >
          {roadmap.milestones?.map((m) => (
            <div
              key={m.quarter}
              style={{
                background: 'var(--color-surface-subtle)',
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
                  {m.quarter}
                </span>
                <span
                  style={{
                    fontSize: 'var(--text-caption)',
                    padding: '2px 6px',
                    borderRadius: 'var(--radius-full)',
                    background:
                      m.status === 'SHIPPED'
                        ? 'var(--color-success-subtle)'
                        : m.status === 'IN_PROGRESS'
                          ? 'var(--color-warning-subtle)'
                          : 'var(--color-surface)',
                    color:
                      m.status === 'SHIPPED'
                        ? 'var(--color-success-text)'
                        : m.status === 'IN_PROGRESS'
                          ? 'var(--color-warning-text)'
                          : 'var(--color-text-muted)',
                    fontWeight: 600,
                    border: '1px solid var(--color-border)',
                  }}
                >
                  {m.status}
                </span>
              </div>
              <strong style={{ fontSize: 'var(--text-body-sm)', color: 'var(--color-text)' }}>
                {m.title}
              </strong>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: varCss('space-4', 16),
                  fontSize: 'var(--text-caption)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                {m.deliverables?.map((d) => (
                  <li key={d} style={{ marginBottom: 4 }}>
                    {d}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* O. Changelog */}
      <section id="changelog" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Release History
          </span>
          <h2 className="docs-card-title">Changelog & Semantic Version History</h2>
          <div className="docs-card-tagline">
            Documented updates and improvements across production releases
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {changelog.releases?.map((r) => (
            <div
              key={r.version}
              style={{
                background: 'var(--color-surface-subtle)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-4)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                <span
                  style={{
                    fontSize: 'var(--text-body)',
                    fontWeight: 700,
                    fontFamily: 'var(--font-plex-mono)',
                    color: 'var(--color-primary)',
                  }}
                >
                  {r.version}
                </span>
                <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-text-muted)' }}>
                  Released on {r.date}
                </span>
              </div>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: 20,
                  fontSize: 'var(--text-body-sm)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                {r.highlights?.map((h) => (
                  <li key={h} style={{ marginBottom: 4 }}>
                    {h}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function varCss(token, fallback) {
  return `var(--${token}, ${fallback}px)`
}
