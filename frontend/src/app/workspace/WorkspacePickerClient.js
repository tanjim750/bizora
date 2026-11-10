'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Search, Building2, LogOut, ArrowRight, ShieldCheck } from 'lucide-react'
import { clientApi } from '@/lib/clientApi'
import { businessPath } from '@/lib/catalog'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { StatusChip } from '@/components/ui/StatusChip'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'

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
      b.role?.toLowerCase().includes(q)
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

  return (
    <div className="workspace-screen">
      {/* Top Header */}
      <header className="workspace-top">
        <Link
          href="/workspace"
          aria-label="Bizora Home - Workspace switcher"
          style={{
            minHeight: '40px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
            color: 'var(--color-nav-text-active)',
            textDecoration: 'none',
            fontFamily: 'var(--font-heading)',
            fontSize: 'var(--text-section)',
            fontWeight: 'var(--weight-heading)',
            letterSpacing: 'var(--tracking-heading)',
          }}
        >
          <span className="brand-mark">B</span> bizora<span className="brand-dot">.</span>
        </Link>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <ThemeToggle />
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              fontSize: 'var(--text-caption)',
              color: 'var(--color-nav-text)',
            }}
          >
            <ShieldCheck size={16} aria-hidden="true" />
            <span>{session?.username}</span>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleSignOut}
            disabled={signingOut}
            aria-label="Sign out of Bizora"
            style={{ color: 'var(--color-nav-text)', borderColor: 'var(--color-nav-active-bg)' }}
          >
            <LogOut size={14} aria-hidden="true" />
            <span>{signingOut ? 'Signing out…' : 'Sign out'}</span>
          </Button>
        </div>
      </header>

      {/* Main Workspace Content */}
      <main className="workspace-content">
        <p className="page-context">Workspaces</p>
        <h1>Choose a workspace</h1>
        <p className="lead">
          Select an authorized business to manage operations, intelligence, and commerce records.
        </p>

        {businesses.length > 0 && (
          <div style={{ margin: 'var(--space-6) 0 var(--space-4)', maxWidth: '420px' }}>
            <label htmlFor="workspace-search" className="sr-only">
              Search workspaces
            </label>
            <div className="input-group">
              <span className="input-addon">
                <Search size={16} className="text-muted" aria-hidden="true" />
              </span>
              <input
                id="workspace-search"
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search workspaces by name, role, currency..."
                className="input input-field"
                aria-label="Search workspaces"
              />
            </div>
          </div>
        )}

        {filtered.length > 0 ? (
          <div className="workspace-grid">
            {filtered.map((business) => (
              <Link
                key={business.id}
                className="workspace-card"
                href={businessPath(business.id, 'overview')}
                aria-label={`Open workspace for ${business.name}`}
              >
                <span className="workspace-monogram" aria-hidden="true">
                  {business.name?.slice(0, 1).toUpperCase() || 'B'}
                </span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}
                  >
                    <strong>{business.name}</strong>
                    <StatusChip status={business.role?.toUpperCase() || 'MEMBER'} />
                  </div>
                  <small
                    style={{
                      display: 'block',
                      marginTop: 'var(--space-1)',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    {business.currency} currency · {business.timezone || 'Asia/Dhaka'} · Workspace #
                    {business.id}
                  </small>
                </div>

                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    color: 'var(--color-primary)',
                    fontWeight: 600,
                    fontSize: 'var(--text-caption)',
                    flexShrink: 0,
                  }}
                  aria-hidden="true"
                >
                  <span>Open</span>
                  <ArrowRight size={14} />
                </span>
              </Link>
            ))}
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
