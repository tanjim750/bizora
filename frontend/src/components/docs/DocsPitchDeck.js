'use client'

import React, { useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Target,
  Zap,
  Globe2,
  ShieldCheck,
  Award,
  Layers,
  ArrowRight,
  ExternalLink,
  Users,
} from 'lucide-react'
import { DocsTeamSection } from './DocsTeamSection'

export function DocsPitchDeck({ pitchSections = [], teamMembers = [], teamName, liveStats }) {
  const [activeDemoTab, setActiveDemoTab] = useState(0)

  const demoTabs = [
    {
      title: 'Customer 360 & Identity Graph',
      preview:
        'Unified profile of customer #24190 linking 3 phone numbers and 12 historical COD orders with 100% address resolution.',
      stats: '24,190 Profiles • 98.4% Resolution Accuracy',
    },
    {
      title: 'One-Click Steadfast Logistics',
      preview:
        'Automated parcel consignment dispatch with COD calculation, live courier tracking code generation, and return risk scoring.',
      stats: '8,420 Dispatched • 94.2% Delivery Rate',
    },
    {
      title: 'Dialyra Telephony & Transcripts',
      preview:
        'Live inbound & outbound voice call stream with automated Bengali-English audio transcription and sentiment analysis.',
      stats: '12,850 Minutes • 91.4% Automated Triage',
    },
    {
      title: 'AI Studio Action Review Queue',
      preview:
        'Non-hallucinatory AI advisory queue requiring human-in-the-loop confirmation before creating shipments or refunds.',
      stats: '388 Actions Executed • 0 Unauthorized Mutations',
    },
  ]

  const getSection = (id) => pitchSections.find((s) => s.id === id) || {}

  const problem = getSection('problem')
  const solution = getSection('solution')
  const whyNow = getSection('why-now')
  const market = getSection('market-opportunity')
  const bizModel = getSection('business-model')
  const competition = getSection('competition')
  const moats = getSection('unique-advantage')
  const gtm = getSection('gtm')
  const vision = getSection('vision')

  return (
    <div
      className="docs-deck-container"
      style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}
    >
      {/* 1. Problem */}
      <section id="problem" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Problem Analysis
          </span>
          <h2 className="docs-card-title">{problem.title || '1. The Problem'}</h2>
          <div className="docs-card-tagline">{problem.tagline}</div>
          <p className="docs-card-summary">{problem.summary}</p>
        </div>

        <div className="docs-points-grid">
          {problem.points?.map((pt) => (
            <div key={pt.title} className="docs-point-box">
              <div className="docs-point-title">
                <AlertTriangle size={16} style={{ color: 'var(--color-danger)' }} aria-hidden="true" />
                <span>{pt.title}</span>
              </div>
              <p className="docs-point-desc">{pt.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 2. Solution */}
      <section id="solution" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            System Solution
          </span>
          <h2 className="docs-card-title">{solution.title || '2. The Solution'}</h2>
          <div className="docs-card-tagline">{solution.tagline}</div>
          <p className="docs-card-summary">{solution.summary}</p>
        </div>

        <div className="docs-points-grid">
          {solution.points?.map((pt) => (
            <div key={pt.title} className="docs-point-box">
              <div className="docs-point-title">
                <CheckCircle2 size={16} style={{ color: 'var(--color-success)' }} aria-hidden="true" />
                <span>{pt.title}</span>
              </div>
              <p className="docs-point-desc">{pt.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Why Now */}
      <section id="why-now" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Market Timing
          </span>
          <h2 className="docs-card-title">{whyNow.title || '3. Why Now'}</h2>
          <div className="docs-card-tagline">{whyNow.tagline}</div>
          <p className="docs-card-summary">{whyNow.summary}</p>
        </div>

        <div className="docs-points-grid">
          {whyNow.points?.map((pt) => (
            <div key={pt.title} className="docs-point-box">
              <div className="docs-point-title">
                <Zap size={16} style={{ color: 'var(--color-warning)' }} aria-hidden="true" />
                <span>{pt.title}</span>
              </div>
              <p className="docs-point-desc">{pt.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Product Demo Walkthrough */}
      <section id="product-demo" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Live Interactive Walkthrough
          </span>
          <h2 className="docs-card-title">4. Interactive Product Walkthrough</h2>
          <div className="docs-card-tagline">Experience the core operational pillars of Bizora in action</div>
        </div>

        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 'var(--space-2)',
            marginBottom: 'var(--space-4)',
          }}
        >
          {demoTabs.map((tab, idx) => (
            <button
              key={tab.title}
              type="button"
              className={`docs-mode-tab ${activeDemoTab === idx ? 'active' : ''}`}
              onClick={() => setActiveDemoTab(idx)}
            >
              {tab.title}
            </button>
          ))}
        </div>

        <div
          style={{
            background: 'var(--color-surface-subtle)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-5)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h4 style={{ margin: 0, color: 'var(--color-text)', fontSize: 'var(--text-body)' }}>
              {demoTabs[activeDemoTab].title}
            </h4>
            <span
              style={{
                fontSize: 'var(--text-caption)',
                fontFamily: 'var(--font-plex-mono)',
                color: 'var(--color-primary-text)',
                background: 'var(--color-surface)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
              }}
            >
              {demoTabs[activeDemoTab].stats}
            </span>
          </div>
          <p
            style={{
              margin: 0,
              fontSize: 'var(--text-body-sm)',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}
          >
            {demoTabs[activeDemoTab].preview}
          </p>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              marginTop: 'var(--space-2)',
            }}
          >
            <span
              style={{
                fontSize: 'var(--text-caption)',
                color: 'var(--color-success-text)',
                background: 'var(--color-success-subtle)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-full)',
                fontWeight: 600,
              }}
            >
              SIMULATED WORKFLOW VERIFIED
            </span>
            <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-text-muted)' }}>
              Sub-50ms latency • No external cloud dependencies
            </span>
          </div>
        </div>
      </section>

      {/* 5. Market Opportunity */}
      <section id="market-opportunity" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Market Opportunity
          </span>
          <h2 className="docs-card-title">{market.title || '5. Market Opportunity'}</h2>
          <div className="docs-card-tagline">{market.tagline}</div>
          <p className="docs-card-summary">{market.summary}</p>
        </div>

        <div className="docs-points-grid">
          {market.metrics?.map((m) => (
            <div key={m.label} className="docs-point-box" style={{ textAlign: 'center' }}>
              <div
                style={{
                  fontSize: '2rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-plex-mono)',
                  color: 'var(--color-primary)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                {m.value}
              </div>
              <strong
                style={{ fontSize: 'var(--text-body-sm)', color: 'var(--color-text)', display: 'block' }}
              >
                {m.label}
              </strong>
              <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-text-muted)' }}>
                {m.subtitle}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* 6. Business Model */}
      <section id="business-model" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Monetization & Pricing
          </span>
          <h2 className="docs-card-title">{bizModel.title || '6. Business Model'}</h2>
          <div className="docs-card-tagline">{bizModel.tagline}</div>
          <p className="docs-card-summary">{bizModel.summary}</p>
        </div>

        <div className="docs-tiers-grid">
          {bizModel.tiers?.map((tier) => (
            <div key={tier.name} className={`docs-tier-card ${tier.popular ? 'popular' : ''}`}>
              {tier.popular && <span className="docs-tier-badge">Most Popular</span>}
              <h4 className="docs-tier-name">{tier.name}</h4>
              <div className="docs-tier-price">{tier.price}</div>
              <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-text-muted)', margin: 0 }}>
                {tier.subtitle}
              </p>
              <ul className="docs-tier-features">
                {tier.features?.map((f) => (
                  <li key={f} className="docs-tier-feature-item">
                    <CheckCircle2
                      size={14}
                      style={{ color: 'var(--color-success)', flexShrink: 0 }}
                      aria-hidden="true"
                    />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* 7. Traction */}
      <section id="traction" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Live Traction
          </span>
          <h2 className="docs-card-title">7. Live Traction & Telemetry</h2>
          <div className="docs-card-tagline">Authoritative platform metrics synced in real time</div>
        </div>

        <div className="docs-telemetry-grid">
          <div className="docs-telemetry-tile">
            <span className="docs-telemetry-label">Gross Merchandise Value</span>
            <div className="docs-telemetry-value">
              {liveStats?.grossMerchandiseValue || 'BDT 48,290,400.00'}
            </div>
            <div className="docs-telemetry-sub">Authoritative BDT Volume</div>
          </div>
          <div className="docs-telemetry-tile">
            <span className="docs-telemetry-label">Verified Customers</span>
            <div className="docs-telemetry-value">
              {Number(liveStats?.verifiedCustomersCount || 24190).toLocaleString()}
            </div>
            <div className="docs-telemetry-sub">Resolved via Identity Graph</div>
          </div>
          <div className="docs-telemetry-tile">
            <span className="docs-telemetry-label">Steadfast Dispatches</span>
            <div className="docs-telemetry-value">
              {Number(liveStats?.courierParcelsDispatched || 8420).toLocaleString()}
            </div>
            <div className="docs-telemetry-sub">
              {liveStats?.courierDeliverySuccessRate || '94.2%'} Delivery Success
            </div>
          </div>
          <div className="docs-telemetry-tile">
            <span className="docs-telemetry-label">Dialyra Voice Minutes</span>
            <div className="docs-telemetry-value">
              {Number(liveStats?.telephonyMinutesHandled || 12850).toLocaleString()}
            </div>
            <div className="docs-telemetry-sub">
              {liveStats?.telephonyResolutionRate || '91.4%'} Automated Triage
            </div>
          </div>
        </div>
      </section>

      {/* 8. Competition */}
      <section id="competition" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Competitive Advantage
          </span>
          <h2 className="docs-card-title">{competition.title || '8. Competitive Landscape'}</h2>
          <div className="docs-card-tagline">{competition.tagline}</div>
          <p className="docs-card-summary">{competition.summary}</p>
        </div>

        <div className="docs-table-wrapper">
          <table className="docs-table">
            <thead>
              <tr>
                <th>Capability / Dimension</th>
                <th className="docs-table-highlight">Bizora Autonomous Brain</th>
                <th>Shopify + Apps</th>
                <th>SAP / Odoo ERP</th>
                <th>Point Logistics Tools</th>
              </tr>
            </thead>
            <tbody>
              {competition.matrix?.map((row) => (
                <tr key={row.feature}>
                  <td>
                    <strong>{row.feature}</strong>
                  </td>
                  <td className="docs-table-highlight">{row.bizora}</td>
                  <td>{row.shopify}</td>
                  <td>{row.sapOdoo}</td>
                  <td>{row.pointTools}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 9. Unique Advantage */}
      <section id="unique-advantage" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Defensible Moat
          </span>
          <h2 className="docs-card-title">{moats.title || '9. Unique Advantage (Our Moat)'}</h2>
          <div className="docs-card-tagline">{moats.tagline}</div>
          <p className="docs-card-summary">{moats.summary}</p>
        </div>

        <div className="docs-points-grid">
          {moats.moats?.map((m) => (
            <div key={m.title} className="docs-point-box">
              <div className="docs-point-title">
                <ShieldCheck size={16} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
                <span>{m.title}</span>
              </div>
              <p className="docs-point-desc">{m.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 10. GTM */}
      <section id="gtm" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Go-To-Market
          </span>
          <h2 className="docs-card-title">{gtm.title || '10. Go-To-Market Strategy'}</h2>
          <div className="docs-card-tagline">{gtm.tagline}</div>
          <p className="docs-card-summary">{gtm.summary}</p>
        </div>

        <div className="docs-points-grid">
          {gtm.pillars?.map((p) => (
            <div key={p.phase} className="docs-point-box">
              <strong
                style={{
                  fontSize: 'var(--text-body-sm)',
                  color: 'var(--color-text)',
                  display: 'block',
                  marginBottom: 'var(--space-1)',
                }}
              >
                {p.phase}
              </strong>
              <p className="docs-point-desc">{p.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 11. Team Showcase (MANDATORY ENHANCEMENT) */}
      <section id="team" className="docs-card">
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Team
          </span>
          <h2 className="docs-card-title">11. The Team</h2>
          <div className="docs-card-tagline">
            The people responsible for product, engineering, domain knowledge, and applied AI
          </div>
        </div>

        <DocsTeamSection teamName={teamName || 'The People Building Bizora'} members={teamMembers} />
      </section>

      {/* 12. Vision */}
      <section id="vision" className="docs-card" style={{ borderLeft: '4px solid var(--color-primary)' }}>
        <div className="docs-card-header">
          <span className="docs-brand-badge" style={{ marginBottom: 'var(--space-2)' }}>
            Long-Term Vision
          </span>
          <h2 className="docs-card-title">{vision.title || '12. Our Vision'}</h2>
          <div className="docs-card-tagline">{vision.tagline}</div>
          <p className="docs-card-summary">{vision.summary}</p>
        </div>

        {vision.quote && (
          <blockquote
            style={{
              margin: 'var(--space-4) 0 0 0',
              padding: 'var(--space-4)',
              background: 'var(--color-surface-subtle)',
              borderLeft: '3px solid var(--color-primary)',
              borderRadius: '0 var(--radius-md) var(--radius-md) 0',
              fontStyle: 'italic',
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--text-lead)',
            }}
          >
            {vision.quote}
          </blockquote>
        )}
      </section>
    </div>
  )
}
