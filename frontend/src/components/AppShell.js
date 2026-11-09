'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  BarChart3,
  Boxes,
  ClipboardList,
  CreditCard,
  Headphones,
  LayoutDashboard,
  Megaphone,
  Menu,
  MessageSquareText,
  Phone,
  ShieldCheck,
  Sparkles,
  Truck,
  Users,
  X,
} from 'lucide-react'
import { businessPath, MANAGER_ROLES, SECTIONS } from '@/lib/catalog'
import { clientApi } from '@/lib/clientApi'

const ICONS = {
  overview: LayoutDashboard,
  customers: Users,
  products: Boxes,
  orders: ClipboardList,
  payments: CreditCard,
  finance: CreditCard,
  insights: BarChart3,
  inbox: MessageSquareText,
  queue: Headphones,
  marketing: Megaphone,
  website: BarChart3,
  'website-performance': BarChart3,
  delivery: Truck,
  calls: Phone,
  assistant: Sparkles,
  actions: Sparkles,
  identity: ShieldCheck,
  contracts: ShieldCheck,
  configuration: ShieldCheck,
  observability: BarChart3,
}

export default function AppShell({ session, business, children }) {
  const router = useRouter()
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const [logoutError, setLogoutError] = useState('')
  const menuButton = useRef(null)
  const sidebar = useRef(null)
  const groups = [...new Set(SECTIONS.map((item) => item.group))]

  useEffect(() => {
    if (!open) return
    const firstLink = sidebar.current?.querySelector('a')
    firstLink?.focus()
    function onKeyDown(event) {
      if (event.key === 'Escape') {
        setOpen(false)
        menuButton.current?.focus()
      }
      if (event.key !== 'Tab') return
      const focusables = [...sidebar.current.querySelectorAll('a, button')]
      const first = focusables[0]
      const last = focusables.at(-1)
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open])

  async function signOut() {
    setLogoutError('')
    try {
      await clientApi('frontend/logout', { method: 'POST' })
      router.replace('/login')
      router.refresh()
    } catch (error) {
      setLogoutError(error.message)
    }
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="app-shell">
        <aside
          className={`sidebar ${open ? 'sidebar-open' : ''}`}
          ref={sidebar}
          aria-label="Business navigation"
        >
          <div className="sidebar-brand">
            <Link href="/workspace">
              <span className="brand-mark">B</span>
              <span>
                bizora<span className="brand-dot">.</span>
              </span>
            </Link>
            <button
              type="button"
              className="sidebar-close"
              onClick={() => {
                setOpen(false)
                menuButton.current?.focus()
              }}
              aria-label="Close navigation"
            >
              <X size={20} />
            </button>
          </div>
          <div className="sidebar-context">
            <span>Current workspace</span>
            <strong>{business.name}</strong>
            <small>{business.role.toLowerCase()} access</small>
          </div>
          <nav aria-label="Business operations">
            {groups.map((group) => (
              <div key={group} className="nav-group">
                <p>{group}</p>
                {SECTIONS.filter(
                  (section) =>
                    section.group === group && (!section.manager || MANAGER_ROLES.has(business.role)),
                ).map((section) => {
                  const Icon = ICONS[section.key]
                  const href = businessPath(business.id, section.key)
                  const current = pathname === href
                  return (
                    <Link
                      key={section.key}
                      href={href}
                      onClick={() => setOpen(false)}
                      aria-current={current ? 'page' : undefined}
                      className={`nav-link ${current ? 'nav-active' : ''}`}
                    >
                      <Icon size={18} strokeWidth={1.9} aria-hidden="true" />
                      <span>{section.label}</span>
                    </Link>
                  )
                })}
              </div>
            ))}
          </nav>
          <div className="sidebar-foot">Internal operations · {business.currency}</div>
        </aside>
        {open && (
          <button
            className="nav-scrim"
            type="button"
            aria-label="Close navigation"
            onClick={() => {
              setOpen(false)
              menuButton.current?.focus()
            }}
          />
        )}
        <div className="main-column">
          <header className="topbar">
            <button
              ref={menuButton}
              className="menu-button"
              type="button"
              onClick={() => setOpen(true)}
              aria-label="Open navigation"
              aria-expanded={open}
            >
              <Menu size={21} />
            </button>
            <div className="business-switch">
              <label htmlFor="business-switch">Business</label>
              <select
                id="business-switch"
                value={business.id}
                onChange={(event) => router.push(businessPath(event.target.value))}
              >
                {session.businesses.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </div>
            <form className="top-search" action={businessPath(business.id, 'customers')}>
              <label className="sr-only" htmlFor="customer-search">
                Search customers in {business.name}
              </label>
              <input id="customer-search" type="search" name="q" placeholder="Search customers" />
              <button type="submit">Search</button>
            </form>
            <div className="account">
              <span>{session.username}</span>
              <button type="button" onClick={signOut}>
                Sign out
              </button>
            </div>
          </header>
          {logoutError && (
            <div className="alert alert-danger" role="alert">
              {logoutError}
            </div>
          )}
          <main id="main" className="content" tabIndex={-1}>
            {children}
          </main>
        </div>
      </div>
    </>
  )
}
