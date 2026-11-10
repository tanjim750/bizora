'use client'

import React, { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  Users,
  ShoppingBag,
  Headphones,
  TrendingUp,
  BarChart3,
  Sparkles,
  ShieldCheck,
  Cable,
  Sliders,
  Boxes,
  Menu,
  X,
  Search,
  LogOut,
  Building2,
  PanelLeftClose,
  PanelLeftOpen,
  Sun,
  Moon,
  ChevronDown,
} from 'lucide-react'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { Tooltip, TooltipProvider } from '@/components/ui/Tooltip'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/DropdownMenu'
import { QuickSearchDialog } from '@/components/shell/QuickSearchDialog'
import { clientApi } from '@/lib/clientApi'
import { MANAGER_ROLES } from '@/lib/catalog'

// Navigation groups configuration per DESIGN_SPEC.md and docs/frontend.md section 3.0
const NAVIGATION_GROUPS = [
  {
    key: 'overview',
    label: 'Overview',
    items: [
      {
        key: 'overview',
        label: 'Overview',
        getPath: (id) => `/business/${id}/overview`,
        icon: LayoutDashboard,
      },
    ],
  },
  {
    key: 'operations',
    label: 'Operations',
    items: [
      {
        key: 'commerce',
        label: 'Commerce',
        getPath: (id) => `/business/${id}/commerce`,
        icon: ShoppingBag,
      },
      {
        key: 'support',
        label: 'Support',
        getPath: (id) => `/business/${id}/support`,
        icon: Headphones,
        badge: '3',
      },
      {
        key: 'growth',
        label: 'Growth',
        getPath: (id) => `/business/${id}/growth`,
        icon: TrendingUp,
      },
    ],
  },
  {
    key: 'intelligence',
    label: 'Intelligence',
    items: [
      {
        key: 'intelligence',
        label: 'Intelligence',
        getPath: (id) => `/business/${id}/intelligence`,
        icon: BarChart3,
      },
      {
        key: 'ai',
        label: 'AI Assistant',
        getPath: (id) => `/business/${id}/ai`,
        icon: Sparkles,
      },
    ],
  },
  {
    key: 'data-identity',
    label: 'Data and identity',
    items: [
      {
        key: 'customers',
        label: 'Customers',
        getPath: (id) => `/business/${id}/customers`,
        icon: Users,
      },
      {
        key: 'identity',
        label: 'Identity',
        getPath: (id) => `/business/${id}/admin/identity`,
        icon: ShieldCheck,
        manager: true,
      },
    ],
  },
  {
    key: 'integrations',
    label: 'Integrations',
    items: [
      {
        key: 'integrations',
        label: 'Integrations',
        getPath: (id) => `/business/${id}/admin/integrations`,
        icon: Cable,
        manager: true,
      },
    ],
  },
  {
    key: 'settings',
    label: 'Settings',
    items: [
      {
        key: 'configuration',
        label: 'Configuration',
        getPath: (id) => `/business/${id}/admin/configuration`,
        icon: Sliders,
        manager: true,
      },
      {
        key: 'ui-kit',
        label: 'UI Kit Gallery',
        getPath: (id) => `/business/${id}/ui-kit`,
        icon: Boxes,
        devOnly: true,
      },
    ],
  },
]

/**
 * Derives whether a nav item is active based on current pathname.
 * Handles both new 9-workspace URLs and backward-compatible legacy routes.
 */
function isItemActive(itemKey, pathname, businessId) {
  if (!pathname) return false
  const prefix = `/business/${businessId}`

  switch (itemKey) {
    case 'overview':
      return pathname === `${prefix}/overview` || pathname === prefix
    case 'commerce':
      return (
        pathname.startsWith(`${prefix}/commerce`) ||
        pathname.startsWith(`${prefix}/orders`) ||
        pathname.startsWith(`${prefix}/products`) ||
        pathname.startsWith(`${prefix}/payments`) ||
        pathname.startsWith(`${prefix}/delivery`) ||
        pathname.startsWith(`${prefix}/finance`)
      )
    case 'support':
      return (
        pathname.startsWith(`${prefix}/support`) ||
        pathname.startsWith(`${prefix}/inbox`) ||
        pathname.startsWith(`${prefix}/queue`) ||
        pathname.startsWith(`${prefix}/calls`)
      )
    case 'growth':
      return (
        pathname.startsWith(`${prefix}/growth`) ||
        pathname.startsWith(`${prefix}/marketing`) ||
        pathname.startsWith(`${prefix}/website`) ||
        pathname.startsWith(`${prefix}/website-performance`)
      )
    case 'intelligence':
      return pathname.startsWith(`${prefix}/intelligence`) || pathname.startsWith(`${prefix}/insights`)
    case 'ai':
      return (
        pathname.startsWith(`${prefix}/ai`) ||
        pathname.startsWith(`${prefix}/assistant`) ||
        pathname.startsWith(`${prefix}/actions`)
      )
    case 'customers':
      return pathname.startsWith(`${prefix}/customers`)
    case 'identity':
      return pathname.startsWith(`${prefix}/admin/identity`) || pathname.startsWith(`${prefix}/identity`)
    case 'integrations':
      return (
        pathname.startsWith(`${prefix}/admin/integrations`) || pathname.startsWith(`${prefix}/observability`)
      )
    case 'configuration':
      return (
        pathname.startsWith(`${prefix}/admin/configuration`) ||
        pathname.startsWith(`${prefix}/configuration`) ||
        pathname.startsWith(`${prefix}/contracts`)
      )
    case 'ui-kit':
      return pathname.startsWith(`${prefix}/ui-kit`)
    default:
      return false
  }
}

export default function AppShell({ session, business, children }) {
  const router = useRouter()
  const pathname = usePathname()

  // State
  const [mobileOpen, setMobileOpen] = useState(false)
  const [railCollapsed, setRailCollapsed] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState('')
  const [theme, setTheme] = useState('light')
  const [mounted, setMounted] = useState(false)

  // Refs
  const menuButton = useRef(null)
  const sidebar = useRef(null)

  const isManager = MANAGER_ROLES.has(business?.role)
  const isDev = process.env.NODE_ENV !== 'production'

  // Initialize rail collapse based on viewport and saved preference
  useEffect(() => {
    try {
      const saved = localStorage.getItem('bizora_rail_collapsed')
      if (saved !== null) {
        setRailCollapsed(saved === 'true')
      } else if (typeof window !== 'undefined') {
        const width = window.innerWidth
        if (width >= 1024 && width < 1280) {
          setRailCollapsed(true)
        } else if (width >= 1280) {
          setRailCollapsed(false)
        }
      }
    } catch {
      // Ignore localStorage restrictions
    }
  }, [])

  // Track theme changes
  useEffect(() => {
    setMounted(true)
    const active = document.documentElement.getAttribute('data-theme')
    if (active === 'dark' || active === 'light') {
      setTheme(active)
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setTheme('dark')
    }
  }, [])

  function toggleRail() {
    setRailCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem('bizora_rail_collapsed', String(next))
      } catch {
        // Ignore
      }
      return next
    })
  }

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    document.documentElement.setAttribute('data-theme', next)
    try {
      localStorage.setItem('bizora_theme', next)
    } catch {
      // Ignore
    }
  }

  // Global keyboard shortcut for search dialog (Ctrl+K / Cmd+K)
  useEffect(() => {
    function onKeyDown(e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearchOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false)
  }, [pathname])

  // Mobile drawer focus trap, escape listener, inert, and body scroll lock
  useEffect(() => {
    const mainEl = document.getElementById('main')
    if (!mobileOpen) {
      mainEl?.removeAttribute('inert')
      return
    }

    // Mark content behind drawer as inert
    mainEl?.setAttribute('inert', '')

    // Lock body scroll
    const origOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const focusables = sidebar.current
      ? [...sidebar.current.querySelectorAll('a, button, select, [tabindex="0"]')]
      : []
    focusables[0]?.focus()

    function onKeyDown(event) {
      if (event.key === 'Escape') {
        setMobileOpen(false)
        menuButton.current?.focus()
      }
      if (event.key !== 'Tab') return
      const currentFocusables = sidebar.current
        ? [...sidebar.current.querySelectorAll('a, button, select, [tabindex="0"]')]
        : []
      const first = currentFocusables[0]
      const last = currentFocusables.at(-1)
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = origOverflow
      document.removeEventListener('keydown', onKeyDown)
      mainEl?.removeAttribute('inert')
    }
  }, [mobileOpen])

  // Sign out handler
  async function signOut() {
    setLoggingOut(true)
    setLogoutError('')
    try {
      await clientApi('frontend/logout', { method: 'POST' })
      router.replace('/login')
      router.refresh()
    } catch (err) {
      setLogoutError(err.message || 'Failed to sign out.')
      setLoggingOut(false)
    }
  }

  const userInitial = (session?.username || 'U').charAt(0).toUpperCase()
  const businessInitial = (business?.name || 'B').charAt(0).toUpperCase()

  return (
    <TooltipProvider delayDuration={150}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <div className={`app-shell ${railCollapsed ? 'rail-collapsed' : ''}`}>
        {/* Navigation Rail / Mobile Drawer */}
        <aside
          className={`sidebar ${railCollapsed ? 'rail-collapsed' : ''} ${mobileOpen ? 'sidebar-open' : ''}`}
          ref={sidebar}
          role={mobileOpen ? 'dialog' : 'complementary'}
          aria-label="Navigation drawer"
          aria-modal={mobileOpen ? 'true' : undefined}
        >
          {/* Brand header: exactly 56px high aligning with topbar */}
          <div className="sidebar-brand">
            <Link href="/workspace" aria-label="Bizora Home - Workspace switcher">
              <span className="brand-mark" aria-hidden="true">
                B
              </span>
              <span className="brand-text">
                bizora<span className="brand-dot">.</span>
              </span>
            </Link>

            <button
              type="button"
              className="sidebar-close"
              onClick={() => {
                setMobileOpen(false)
                menuButton.current?.focus()
              }}
              aria-label="Close navigation"
            >
              <X size={20} aria-hidden="true" />
            </button>
          </div>

          {/* Current workspace context card (informational, not a switcher) */}
          {business && (
            <div className="sidebar-context">
              {railCollapsed ? (
                <Tooltip
                  side="right"
                  content={`${business.name} (${business.role?.toLowerCase()}) · ${business.currency}`}
                >
                  <div className="workspace-collapsed-avatar" aria-hidden="true">
                    {businessInitial}
                  </div>
                </Tooltip>
              ) : (
                <>
                  <span className="sidebar-context-label">Current workspace</span>
                  <Tooltip content={business.name} side="bottom" align="start">
                    <strong className="sidebar-context-name">{business.name}</strong>
                  </Tooltip>
                  <small className="sidebar-context-meta">
                    {business.role?.toLowerCase()} access · {business.currency}
                  </small>
                </>
              )}
            </div>
          )}

          {/* Navigation groups (independent scroll container) */}
          <nav className="sidebar-nav" aria-label="Business operations">
            {NAVIGATION_GROUPS.map((group) => {
              // Filter items based on manager role and devOnly flag
              const visibleItems = group.items.filter((item) => {
                if (item.manager && !isManager) return false
                if (item.devOnly && !isDev) return false
                return true
              })

              if (visibleItems.length === 0) return null

              return (
                <div key={group.key} className="nav-group">
                  <div className="nav-group-header">
                    <p>{group.label}</p>
                    <div className="nav-group-divider" aria-hidden="true" />
                  </div>
                  {visibleItems.map((item) => {
                    const Icon = item.icon
                    const href = item.getPath(business?.id || '1')
                    const active = isItemActive(item.key, pathname, business?.id || '1')
                    const tooltipText = item.badge ? `${item.label} (${item.badge})` : item.label

                    const navLink = (
                      <Link
                        key={item.key}
                        href={href}
                        onClick={() => setMobileOpen(false)}
                        aria-current={active ? 'page' : undefined}
                        aria-label={item.label}
                        className={`nav-link ${active ? 'nav-active' : ''}`}
                      >
                        <Icon size={18} strokeWidth={1.75} aria-hidden="true" className="nav-icon" />
                        <span className="nav-label">{item.label}</span>
                        {item.badge && <span className="nav-badge">{item.badge}</span>}
                      </Link>
                    )

                    return railCollapsed ? (
                      <Tooltip key={item.key} side="right" content={tooltipText}>
                        {navLink}
                      </Tooltip>
                    ) : (
                      navLink
                    )
                  })}
                </div>
              )
            })}
          </nav>

          {/* Pinned Footer */}
          <div className="sidebar-footer">
            {/* Rail collapse button (desktop only) */}
            {railCollapsed ? (
              <Tooltip side="right" content="Expand navigation rail">
                <button
                  type="button"
                  className="rail-toggle-btn collapsed"
                  onClick={toggleRail}
                  aria-label="Expand navigation rail"
                >
                  <PanelLeftOpen size={18} aria-hidden="true" />
                </button>
              </Tooltip>
            ) : (
              <button
                type="button"
                className="rail-toggle-btn"
                onClick={toggleRail}
                aria-label="Collapse navigation rail"
              >
                <PanelLeftClose size={16} aria-hidden="true" />
                <span>Collapse rail</span>
              </button>
            )}

            {/* User card with Radix DropdownMenu */}
            {session && (
              <div className="sidebar-user-card">
                <DropdownMenu>
                  {railCollapsed ? (
                    <Tooltip
                      side="right"
                      content={`Signed in as ${session.username || 'User'} (${business?.role?.toLowerCase() || 'member'})`}
                    >
                      <DropdownMenuTrigger asChild>
                        <button
                          type="button"
                          className="sidebar-user-btn collapsed"
                          aria-label="User account and settings menu"
                        >
                          <div className="sidebar-user-avatar" aria-hidden="true">
                            {userInitial}
                          </div>
                        </button>
                      </DropdownMenuTrigger>
                    </Tooltip>
                  ) : (
                    <DropdownMenuTrigger asChild>
                      <button
                        type="button"
                        className="sidebar-user-btn"
                        aria-label="User account and settings menu"
                      >
                        <div className="sidebar-user-avatar" aria-hidden="true">
                          {userInitial}
                        </div>
                        <div className="sidebar-user-info">
                          <span className="sidebar-user-name">{session.username || 'User'}</span>
                          <span className="sidebar-user-role">
                            {business?.role?.toLowerCase() || 'member'}
                          </span>
                        </div>
                        <ChevronDown size={14} className="sidebar-user-chevron" aria-hidden="true" />
                      </button>
                    </DropdownMenuTrigger>
                  )}

                  <DropdownMenuContent
                    side={railCollapsed ? 'right' : 'top'}
                    align="start"
                    sideOffset={8}
                    className="sidebar-user-dropdown"
                  >
                    <DropdownMenuLabel>
                      <div className="sidebar-dropdown-header">
                        <strong className="sidebar-dropdown-name">{session.username || 'User'}</strong>
                        <span className="sidebar-dropdown-meta">
                          {business?.role?.toLowerCase()} · {business?.name}
                        </span>
                      </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={toggleTheme}>
                      {mounted && theme === 'dark' ? (
                        <Sun size={15} aria-hidden="true" />
                      ) : (
                        <Moon size={15} aria-hidden="true" />
                      )}
                      <span>
                        {mounted && theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
                      </span>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={signOut}
                      disabled={loggingOut}
                      className="dropdown-item-danger"
                    >
                      <LogOut size={15} aria-hidden="true" />
                      <span>{loggingOut ? 'Signing out...' : 'Sign out'}</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}

            {/* Development badge */}
            {isDev && <div className="sidebar-dev-badge">Development</div>}
          </div>
        </aside>

        {/* Mobile backdrop scrim */}
        {mobileOpen && (
          <div
            className="nav-scrim"
            onClick={() => {
              setMobileOpen(false)
              menuButton.current?.focus()
            }}
            aria-hidden="true"
          />
        )}

        {/* Main Column */}
        <div className="main-column">
          {/* Sticky Topbar */}
          <header className="topbar">
            <div className="topbar-left">
              {/* Mobile hamburger menu button (44px target) */}
              <button
                ref={menuButton}
                className="menu-button"
                type="button"
                onClick={() => setMobileOpen(true)}
                aria-label="Open navigation menu"
                aria-expanded={mobileOpen}
              >
                <Menu size={20} aria-hidden="true" />
              </button>

              {/* Business Switcher: the sole business switcher */}
              {business && session?.businesses && (
                <div className="business-switcher">
                  <label htmlFor="business-switch" className="sr-only">
                    Select active business
                  </label>
                  <div className="business-switcher-select-wrap">
                    <Building2 size={16} className="text-muted" aria-hidden="true" />
                    <select
                      id="business-switch"
                      value={business.id}
                      onChange={(e) => {
                        router.push(`/business/${encodeURIComponent(e.target.value)}/overview`)
                      }}
                      className="business-switcher-select"
                      aria-label="Switch active business"
                    >
                      {session.businesses.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.name} ({b.role?.toLowerCase()})
                        </option>
                      ))}
                    </select>
                  </div>
                  <span className="topbar-role-badge">{business.role?.toLowerCase()}</span>
                </div>
              )}
            </div>

            {/* Global Search Command Trigger (Ctrl+K) */}
            <button
              type="button"
              className="global-search-trigger"
              onClick={() => setSearchOpen(true)}
              aria-label="Search records, customers, orders... (Ctrl+K)"
            >
              <Search size={15} className="text-muted" aria-hidden="true" />
              <span className="global-search-text">Search records, workspaces...</span>
              <kbd className="topbar-kbd">Ctrl K</kbd>
            </button>

            {/* Operational Context tag (responsive: hidden on mobile) */}
            {business && (
              <div
                className="topbar-context-tag"
                title={`Operational context: ${business.currency} currency in ${business.timezone || 'Asia/Dhaka'} timezone`}
              >
                <span>{business.currency}</span>
                <span>·</span>
                <span>{business.timezone || 'Asia/Dhaka'}</span>
              </div>
            )}

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Topbar User Profile */}
            {session && (
              <div className="user-profile-menu">
                <div
                  className="user-avatar"
                  title={`Signed in as ${session.username || 'User'}`}
                  aria-hidden="true"
                >
                  {userInitial}
                </div>
                <div className="user-info">
                  <span className="user-name">{session.username}</span>
                  <span className="user-role-tag">{business?.role?.toLowerCase() || 'member'}</span>
                </div>
                <button
                  type="button"
                  onClick={signOut}
                  disabled={loggingOut}
                  className="signout-button"
                  aria-label="Sign out of Bizora"
                  title="Sign out"
                >
                  <LogOut size={16} aria-hidden="true" />
                  <span className="signout-text">{loggingOut ? 'Signing out...' : 'Sign out'}</span>
                </button>
              </div>
            )}
          </header>

          {/* Logout error notice */}
          {logoutError && (
            <div
              className="alert alert-danger"
              role="alert"
              style={{ margin: 'var(--space-3) var(--space-6)' }}
            >
              {logoutError}
            </div>
          )}

          {/* Page Content */}
          <main id="main" className="content" tabIndex={-1}>
            {children}
          </main>
        </div>
      </div>

      {/* Quick Search Command Dialog */}
      <QuickSearchDialog isOpen={searchOpen} onClose={() => setSearchOpen(false)} businessId={business?.id} />
    </TooltipProvider>
  )
}
