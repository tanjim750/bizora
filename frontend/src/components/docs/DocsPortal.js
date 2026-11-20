'use client'

import React, { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import {
  Download,
  Share2,
  Printer,
  Search,
  Lock,
  Sliders,
  Check,
  ChevronRight,
  Activity,
  BookOpen,
} from 'lucide-react'
import BizoraLogo from '../ui/BizoraLogo'
import { DocsPitchDeck } from './DocsPitchDeck'
import { DocsTechnical } from './DocsTechnical'
import { DocsLiveSystem } from './DocsLiveSystem'
import { DocsAdminPanel } from './DocsAdminPanel'
import {
  generateMarkdownExport,
  downloadMarkdownFile,
  triggerPrintPdf,
  copyShareableLink,
} from '@/lib/docs/export'

export function DocsPortal({
  initialConfig,
  initialContent,
  initialLiveStats,
  initialFeatureMatrix,
  access,
  session,
}) {
  const [activeView, setActiveView] = useState('DECK') // 'DECK' | 'TECH' | 'LIVE'
  const [searchQuery, setSearchQuery] = useState('')
  const [activeAnchor, setActiveAnchor] = useState('problem')
  const [isAdminPanelOpen, setIsAdminPanelOpen] = useState(false)
  const [copiedLink, setCopiedLink] = useState(false)

  // Local state for live updates from admin panel
  const [config, setConfig] = useState(initialConfig || {})
  const [content, setContent] = useState(initialContent || {})
  const [liveStats, setLiveStats] = useState(initialLiveStats || {})

  const isAdmin = access?.isAdmin || session?.authenticated

  // Scroll spy for active anchor
  useEffect(() => {
    const handleScroll = () => {
      const sections = document.querySelectorAll('section[id]')
      const scrollY = window.scrollY
      for (const sec of sections) {
        const top = sec.offsetTop - 120
        const height = sec.offsetHeight
        if (scrollY >= top && scrollY < top + height) {
          setActiveAnchor(sec.id)
          break
        }
      }
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleCopyLink = async () => {
    const ok = await copyShareableLink(activeAnchor)
    if (ok) {
      setCopiedLink(true)
      setTimeout(() => setCopiedLink(false), 2000)
    }
  }

  const handleDownloadMarkdown = () => {
    const md = generateMarkdownExport(
      content.pitchSections || [],
      content.technicalSections || [],
      content.teamMembers || [],
      liveStats,
    )
    downloadMarkdownFile('bizora-yc-pitch-and-technical-whitepaper.md', md)
  }

  // Filtered sections by search
  const filteredPitchSections = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    if (!q) return content.pitchSections || []
    return (content.pitchSections || []).filter(
      (s) =>
        s.title?.toLowerCase().includes(q) ||
        s.summary?.toLowerCase().includes(q) ||
        s.tagline?.toLowerCase().includes(q) ||
        s.points?.some((p) => p.title?.toLowerCase().includes(q) || p.detail?.toLowerCase().includes(q)),
    )
  }, [content.pitchSections, searchQuery])

  const filteredTechSections = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    if (!q) return content.technicalSections || []
    return (content.technicalSections || []).filter(
      (s) =>
        s.title?.toLowerCase().includes(q) ||
        s.summary?.toLowerCase().includes(q) ||
        s.endpoints?.some(
          (ep) => ep.path?.toLowerCase().includes(q) || ep.description?.toLowerCase().includes(q),
        ),
    )
  }, [content.technicalSections, searchQuery])

  return (
    <div className="docs-container">
      {/* Top Sticky Bar */}
      <header className="docs-topbar docs-no-print">
        <div className="docs-topbar-left">
          <Link
            href="/workspace"
            aria-label="Go to workspace"
            style={{ display: 'flex', alignItems: 'center', minHeight: 40, textDecoration: 'none' }}
          >
            <BizoraLogo />
          </Link>
          <div className="docs-topbar-title">
            <div className="docs-brand-heading">Bizora Docs</div>
            <span className="docs-brand-badge">Product & Engineering</span>
          </div>
        </div>

        {/* Mode Switcher */}
        <div className="docs-topbar-center">
          <button
            type="button"
            className={`docs-mode-tab ${activeView === 'DECK' ? 'active' : ''}`}
            onClick={() => setActiveView('DECK')}
          >
            Pitch
          </button>
          <button
            type="button"
            className={`docs-mode-tab ${activeView === 'TECH' ? 'active' : ''}`}
            onClick={() => setActiveView('TECH')}
          >
            Engineering
          </button>
          <button
            type="button"
            className={`docs-mode-tab ${activeView === 'LIVE' ? 'active' : ''}`}
            onClick={() => setActiveView('LIVE')}
          >
            System
          </button>
        </div>

        {/* Actions & Admin */}
        <div className="docs-topbar-right">
          {/* Global Search */}
          <div style={{ position: 'relative', width: 180 }}>
            <Search
              size={14}
              style={{
                position: 'absolute',
                left: 8,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--color-text-muted)',
              }}
              aria-hidden="true"
            />
            <input
              type="text"
              aria-label="Search documentation"
              placeholder="Search /docs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 8px 6px 28px',
                fontSize: 'var(--text-body-sm)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
                color: 'var(--color-text)',
              }}
            />
          </div>

          {/* Export Actions */}
          <button
            type="button"
            className="docs-mode-tab"
            onClick={triggerPrintPdf}
            title="Print or Save as PDF"
            aria-label="Export PDF"
          >
            <Printer size={15} aria-hidden="true" />
            <span style={{ display: 'none' }}>PDF</span>
          </button>

          <button
            type="button"
            className="docs-mode-tab"
            onClick={handleDownloadMarkdown}
            title="Download full document as Markdown"
            aria-label="Export Markdown"
          >
            <Download size={15} aria-hidden="true" />
            <span style={{ display: 'none' }}>Markdown</span>
          </button>

          <button
            type="button"
            className="docs-mode-tab"
            onClick={handleCopyLink}
            title="Copy link to current section"
            aria-label="Share Link"
          >
            {copiedLink ? (
              <Check size={15} style={{ color: 'var(--color-success)' }} aria-hidden="true" />
            ) : (
              <Share2 size={15} aria-hidden="true" />
            )}
          </button>

          {/* Admin Control Button */}
          {isAdmin && (
            <button
              type="button"
              className="docs-mode-tab active"
              onClick={() => setIsAdminPanelOpen(true)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}
              title="Configure visibility, scheduling windows, and content"
            >
              <Sliders size={14} aria-hidden="true" />
              <span>Admin Console</span>
            </button>
          )}
        </div>
      </header>

      {/* Admin Notice Banner (shown if visitor is Admin and docs are restricted to public) */}
      {isAdmin && access && !access.publicGranted && (
        <div className="docs-admin-notice-bar docs-no-print">
          <div className="docs-admin-notice-text">
            <Lock size={15} aria-hidden="true" />
            <span>
              <strong>Admin Preview Active:</strong> Public access is currently restricted (
              {access.publicReason}). Visitors see the Scheduled Showcase screen.
            </span>
          </div>
          <button
            type="button"
            className="docs-mode-tab active"
            onClick={() => setIsAdminPanelOpen(true)}
            style={{ padding: '3px 10px', fontSize: 'var(--text-caption)' }}
          >
            Adjust Schedule
          </button>
        </div>
      )}

      {/* Main Layout Container */}
      <div className="docs-layout">
        {/* Sticky Sidebar Navigation Rail */}
        <aside className="docs-sidebar docs-no-print" aria-label="Table of Contents">
          {activeView === 'DECK' && (
            <div className="docs-sidebar-section">
              <div className="docs-sidebar-heading">YC Pitch Deck</div>
              <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {[
                  { id: 'problem', label: '1. The Problem' },
                  { id: 'solution', label: '2. The Solution' },
                  { id: 'why-now', label: '3. Why Now' },
                  { id: 'product-demo', label: '4. Product Demo' },
                  { id: 'market-opportunity', label: '5. Market Opportunity' },
                  { id: 'business-model', label: '6. Business Model' },
                  { id: 'traction', label: '7. Live Traction' },
                  { id: 'competition', label: '8. Competition' },
                  { id: 'unique-advantage', label: '9. Unique Moat' },
                  { id: 'gtm', label: '10. Go-To-Market' },
                  { id: 'team', label: '11. Core Team' },
                  { id: 'vision', label: '12. Vision' },
                ].map((item) => (
                  <a
                    key={item.id}
                    href={`#${item.id}`}
                    className={`docs-nav-link ${activeAnchor === item.id ? 'active' : ''}`}
                  >
                    <span>{item.label}</span>
                    <ChevronRight size={12} style={{ opacity: 0.5 }} aria-hidden="true" />
                  </a>
                ))}
              </nav>
            </div>
          )}

          {activeView === 'TECH' && (
            <div className="docs-sidebar-section">
              <div className="docs-sidebar-heading">Technical Whitepaper</div>
              <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {[
                  { id: 'tech-overview', label: 'System Foundations' },
                  { id: 'feature-matrix', label: 'Live Feature Matrix' },
                  { id: 'architecture', label: 'Architecture Diagram' },
                  { id: 'data-flow', label: 'Data Flow & Graph' },
                  { id: 'tech-stack', label: 'Technology Stack' },
                  { id: 'api-documentation', label: 'API Reference' },
                  { id: 'security', label: 'Security & RBAC' },
                  { id: 'roadmap', label: 'Roadmap & Milestones' },
                  { id: 'changelog', label: 'Changelog' },
                ].map((item) => (
                  <a
                    key={item.id}
                    href={`#${item.id}`}
                    className={`docs-nav-link ${activeAnchor === item.id ? 'active' : ''}`}
                  >
                    <span>{item.label}</span>
                    <ChevronRight size={12} style={{ opacity: 0.5 }} aria-hidden="true" />
                  </a>
                ))}
              </nav>
            </div>
          )}
        </aside>

        {/* Main Content Stream */}
        <main className="docs-main">
          {/* Hero Banner */}
          <div className="docs-hero">
            <div className="docs-hero-badge-row">
              <span className="docs-brand-badge">
                <BookOpen size={12} style={{ marginRight: 4 }} aria-hidden="true" />
                Bizora product brief
              </span>
              <span
                style={{
                  fontSize: 'var(--text-caption)',
                  color: 'var(--color-success-text)',
                  background: 'var(--color-success-subtle)',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <Activity size={12} />
                System status synced
              </span>
            </div>

            <h1 className="docs-hero-h1">
              {config.title || 'Bizora — Autonomous Enterprise Business Brain'}
            </h1>
            <p className="docs-hero-tagline">
              {config.tagline ||
                'The operating system for emerging market commerce intelligence. Unifying Customer Identity, Steadfast Logistics, and Dialyra Voice Telephony with Deterministic AI Guardrails.'}
            </p>

            {/* Keep system metrics focused in the System view. */}
            {activeView === 'LIVE' && (
              <div className="docs-telemetry-grid">
                <div className="docs-telemetry-tile">
                  <span className="docs-telemetry-label">Processed GMV</span>
                  <div className="docs-telemetry-value">
                    {liveStats?.grossMerchandiseValue || 'BDT 48,290,400.00'}
                  </div>
                  <div className="docs-telemetry-sub">Authoritative Volume</div>
                </div>
                <div className="docs-telemetry-tile">
                  <span className="docs-telemetry-label">Customer Profiles</span>
                  <div className="docs-telemetry-value">
                    {Number(liveStats?.verifiedCustomersCount || 24190).toLocaleString()}
                  </div>
                  <div className="docs-telemetry-sub">98.4% Resolution Rate</div>
                </div>
                <div className="docs-telemetry-tile">
                  <span className="docs-telemetry-label">Steadfast Parcels</span>
                  <div className="docs-telemetry-value">
                    {Number(liveStats?.courierParcelsDispatched || 8420).toLocaleString()}
                  </div>
                  <div className="docs-telemetry-sub">94.2% Delivery Rate</div>
                </div>
                <div className="docs-telemetry-tile">
                  <span className="docs-telemetry-label">Dialyra Calls</span>
                  <div className="docs-telemetry-value">
                    {Number(liveStats?.telephonyMinutesHandled || 12850).toLocaleString()} min
                  </div>
                  <div className="docs-telemetry-sub">91.4% Automated Triage</div>
                </div>
              </div>
            )}
          </div>

          {/* Conditional View Rendering */}
          {activeView === 'DECK' && (
            <DocsPitchDeck
              pitchSections={filteredPitchSections}
              teamMembers={content.teamMembers || []}
              teamName={config.teamName}
              liveStats={liveStats}
            />
          )}

          {activeView === 'TECH' && (
            <DocsTechnical
              technicalSections={filteredTechSections}
              liveFeatureMatrix={initialFeatureMatrix || []}
            />
          )}

          {activeView === 'LIVE' && (
            <DocsLiveSystem liveStats={liveStats} liveFeatureMatrix={initialFeatureMatrix || []} />
          )}
        </main>
      </div>

      {/* Admin Panel Modal */}
      <DocsAdminPanel
        isOpen={isAdminPanelOpen}
        onClose={() => setIsAdminPanelOpen(false)}
        config={config}
        onUpdateConfig={(newCfg) => setConfig(newCfg)}
        content={content}
        onUpdateContent={(newCnt) => setContent(newCnt)}
      />
    </div>
  )
}
