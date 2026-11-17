'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Search, Building2, LogOut, ArrowRight, X, ShieldCheck, Layers } from 'lucide-react'
import { clientApi } from '@/lib/clientApi'
import { businessPath } from '@/lib/catalog'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { StatusChip } from '@/components/ui/StatusChip'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { BizoraLogo } from '@/components/ui/BizoraLogo'

export function WorkspacePickerClient({ session }) {
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [signingOut, setSigningOut] = useState(false)

  const businesses = session?.businesses || []
  const filtered = businesses.filter((b) => {
    if (!search.trim()) return true
    const q = search.toLowerCase()
    return (
      b.name?.toLowerCase().includes(q) ||
      b.currency?.toLowerCase().includes(q) ||
      b.role?.toLowerCase().includes(q) ||
      String(b.id).includes(q)
    )
  })

  const handleSignOut = async () => {
    setSigningOut(true)
    try {
      await clientApi('frontend/logout', { method: 'POST' })
    } catch {
      // Proceed even if network error
    }
    router.replace('/login')
    router.refresh()
  }

  const userInitial = (session?.username || 'U').slice(0, 2).toUpperCase()

  return (
    <div className="workspace-screen">
      {/* Top Header */}
      <header className="workspace-top">
        <div className="workspace-top-inner">
          <Link
            href="/workspace"
            className="workspace-brand-link"
            aria-label="Bizora Home - Workspace switcher"
          >
            <BizoraLogo size={32} showText={true} />
          </Link>

          <div className="workspace-top-actions">
            <ThemeToggle />
            <div className="workspace-user-chip">
              <div className="workspace-user-avatar" aria-hidden="true">
                {userInitial}
              </div>
              <div className="workspace-user-meta">
                <span className="workspace-username">{session?.username}</span>
                <span className="workspace-user-badge">Authenticated</span>
              </div>
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleSignOut}
              disabled={signingOut}
              aria-label="Sign out of Bizora"
              className="workspace-signout-btn"
            >
              <LogOut size={14} aria-hidden="true" />
              <span>{signingOut ? 'Signing out…' : 'Sign out'}</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Workspace Content */}
      <main className="workspace-content">
        <div className="workspace-hero">
          <div className="workspace-hero-badge">
            <span className="workspace-pulse-dot" aria-hidden="true" />
            <span>Enterprise Multi-Tenant Environment</span>
          </div>
          <h1 className="workspace-title">Choose your workspace</h1>
          <p className="workspace-subtitle">
            Select an authorized organization to manage real-time commerce, intelligence pipelines, and
            autonomous AI advisory workflows.
          </p>
        </div>

        {businesses.length > 0 && (
          <div className="workspace-toolbar">
            <div className="workspace-search-bar input-group">
              <Search size={18} className="workspace-search-icon" aria-hidden="true" />
              <input
                id="workspace-search"
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search workspaces by name, role, currency, or ID..."
                className="workspace-search-input"
                aria-label="Search workspaces"
                autoComplete="off"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="workspace-search-clear"
                  aria-label="Clear search query"
                >
                  <X size={14} aria-hidden="true" />
                </button>
              )}
              <span className="workspace-search-badge" aria-hidden="true">
                {filtered.length} {filtered.length === 1 ? 'workspace' : 'workspaces'}
              </span>
            </div>

            <div className="workspace-stats-pill">
              <Layers size={14} aria-hidden="true" />
              <span>
                {businesses.length} Total Authorized {businesses.length === 1 ? 'Entity' : 'Entities'}
              </span>
            </div>
          </div>
        )}

        {filtered.length > 0 ? (
          <div className="workspace-grid">
            {filtered.map((business) => {
              const monogram = business.name
                ? business.name
                    .split(' ')
                    .map((w) => w[0])
                    .slice(0, 2)
                    .join('')
                    .toUpperCase()
                : 'BD'

              return (
                <div key={business.id} className="workspace-card-item">
                  <Link
                    href={businessPath(business.id, 'overview')}
                    className="workspace-card-main"
                    aria-label={`Open workspace for ${business.name}`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <div className="workspace-card-identity">
                      <div className="workspace-avatar" aria-hidden="true">
                        {monogram}
                      </div>

                      <div className="workspace-name-col">
                        <div className="workspace-name-row">
                          <strong className="workspace-name">{business.name}</strong>
                          <StatusChip status={business.role?.toUpperCase() || 'MEMBER'} size="sm" />
                        </div>
                        <span className="workspace-id-tag">Tenant ID: #{business.id}</span>
                      </div>
                    </div>

                    <div className="workspace-launch-btn" aria-hidden="true">
                      <span>Launch</span>
                      <ArrowRight size={14} className="workspace-arrow" />
                    </div>
                  </Link>

                  <div className="workspace-card-specs">
                    <div className="workspace-spec-item">
                      <span className="spec-label">Currency</span>
                      <span className="spec-val font-mono">{business.currency || 'BDT'}</span>
                    </div>
                    <div className="workspace-spec-item">
                      <span className="spec-label">Timezone</span>
                      <span className="spec-val">{business.timezone || 'Asia/Dhaka'}</span>
                    </div>
                    <div className="workspace-spec-item">
                      <span className="spec-label">Operational State</span>
                      <span className="spec-val text-success">
                        <span className="status-live-dot" aria-hidden="true" /> Active
                      </span>
                    </div>
                  </div>

                  <div className="workspace-card-shortcuts">
                    <span className="shortcut-label">Jump to:</span>
                    <Link
                      href={businessPath(business.id, 'overview')}
                      className="shortcut-pill"
                      style={{ textDecoration: 'none' }}
                    >
                      Overview
                    </Link>
                    <Link
                      href={businessPath(business.id, 'commerce')}
                      className="shortcut-pill"
                      style={{ textDecoration: 'none' }}
                    >
                      Commerce
                    </Link>
                    <Link
                      href={businessPath(business.id, 'support')}
                      className="shortcut-pill"
                      style={{ textDecoration: 'none' }}
                    >
                      Support
                    </Link>
                    <Link
                      href={businessPath(business.id, 'ai')}
                      className="shortcut-pill"
                      style={{ textDecoration: 'none' }}
                    >
                      AI Studio
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>
        ) : businesses.length > 0 ? (
          <EmptyState
            title="No matching workspaces"
            description={`No business matching "${search}" was found in your authorizations.`}
            action={
              <Button variant="secondary" size="sm" onClick={() => setSearch('')}>
                Clear search filter
              </Button>
            }
          />
        ) : (
          <EmptyState
            title="No active business access"
            description="Your account is not assigned to any business workspace yet. Ask an organization owner to grant you access."
          />
        )}
      </main>
    </div>
  )
}

export default WorkspacePickerClient
