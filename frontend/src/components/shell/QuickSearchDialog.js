'use client'

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import {
  Search,
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
  ClipboardList,
  CreditCard,
  Truck,
  Phone,
  Megaphone,
  Radio,
  ExternalLink,
  ArrowRight,
  SunMoon,
  Building2,
  Palette,
} from 'lucide-react'
import { Dialog } from '../ui/Dialog.js'
import { Input } from '../ui/Input.js'

export function QuickSearchDialog({ isOpen, onClose, businessId, onToggleTheme }) {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef(null)

  // Searchable items registry
  const searchItems = useMemo(() => {
    const bId = businessId || '1'
    return [
      // Workspaces
      {
        id: 'ws-overview',
        category: 'Workspaces',
        title: 'Business Overview',
        subtitle: 'Executive KPIs, performance trends, and business health',
        href: `/business/${bId}/overview`,
        icon: LayoutDashboard,
      },
      {
        id: 'ws-customers',
        category: 'Workspaces',
        title: 'Customer 360 & Profiles',
        subtitle: 'Unified profiles, identity resolution, orders, and touchpoints',
        href: `/business/${bId}/customers`,
        icon: Users,
      },
      {
        id: 'ws-commerce',
        category: 'Workspaces',
        title: 'Commerce & Orders',
        subtitle: 'Order processing, payments, refunds, shipments, and catalog',
        href: `/business/${bId}/commerce`,
        icon: ShoppingBag,
      },
      {
        id: 'ws-support',
        category: 'Workspaces',
        title: 'Support & Unified Inbox',
        subtitle: 'Customer messaging, urgent queue, and call logs',
        href: `/business/${bId}/support`,
        icon: Headphones,
      },
      {
        id: 'ws-growth',
        category: 'Workspaces',
        title: 'Growth & Marketing',
        subtitle: 'Campaign metrics, visitor sessions, and website performance',
        href: `/business/${bId}/growth`,
        icon: TrendingUp,
      },
      {
        id: 'ws-intelligence',
        category: 'Workspaces',
        title: 'Business Intelligence',
        subtitle: 'Grounded facts, entity graph, metrics catalog, and pipeline',
        href: `/business/${bId}/intelligence`,
        icon: BarChart3,
      },
      {
        id: 'ws-ai',
        category: 'Workspaces',
        title: 'AI Studio & Proposals',
        subtitle: 'Grounded assistant, advisory proposals, and audit logs',
        href: `/business/${bId}/ai`,
        icon: Sparkles,
      },
      {
        id: 'ws-switch',
        category: 'Workspaces',
        title: 'Switch Workspace',
        subtitle: 'Select another business organization or multi-tenant workspace',
        href: '/workspace',
        icon: Building2,
      },
      {
        id: 'ws-uikit',
        category: 'Workspaces',
        title: 'UI Kit & Component Gallery',
        subtitle: 'Enterprise design system primitives, forms, tables, and charts',
        href: `/business/${bId}/ui-kit`,
        icon: Palette,
      },
      {
        id: 'ws-identity',
        category: 'Administration',
        title: 'Identity Resolution',
        subtitle: 'Canonical customer records, conflict review, and merge dry-run',
        href: `/business/${bId}/admin/identity`,
        icon: ShieldCheck,
      },
      {
        id: 'ws-integrations',
        category: 'Administration',
        title: 'Integrations & Sync',
        subtitle: 'Platform connections, sync statistics, webhook replay, and health',
        href: `/business/${bId}/admin/integrations`,
        icon: Cable,
      },
      {
        id: 'ws-config',
        category: 'Administration',
        title: 'Business Configuration',
        subtitle: 'Policies, threshold rules, providers, and environment settings',
        href: `/business/${bId}/admin/configuration`,
        icon: Sliders,
      },
      // Resources
      {
        id: 'res-orders',
        category: 'Resources',
        title: 'Orders',
        subtitle: 'Customer orders and fulfillment lifecycle',
        href: `/business/${bId}/commerce?tab=orders`,
        icon: ClipboardList,
      },
      {
        id: 'res-payments',
        category: 'Resources',
        title: 'Payments & Refunds',
        subtitle: 'Transaction references, bKash/SSLCommerz, and refund ledger',
        href: `/business/${bId}/commerce?tab=payments`,
        icon: CreditCard,
      },
      {
        id: 'res-products',
        category: 'Resources',
        title: 'Products & Variants',
        subtitle: 'SKU catalog, variant pricing, and inventory quantities',
        href: `/business/${bId}/commerce?tab=products`,
        icon: Boxes,
      },
      {
        id: 'res-shipments',
        category: 'Resources',
        title: 'Deliveries & Shipments',
        subtitle: 'Courier tracking, fulfillment status, and delivery dispatch',
        href: `/business/${bId}/commerce?tab=deliveries`,
        icon: Truck,
      },
      {
        id: 'res-calls',
        category: 'Resources',
        title: 'Calls & Transcripts',
        subtitle: 'Recorded call logs, scheduled callbacks, and sentiment',
        href: `/business/${bId}/support?tab=calls`,
        icon: Phone,
      },
      {
        id: 'res-campaigns',
        category: 'Resources',
        title: 'Campaigns & Ads',
        subtitle: 'Meta and Google ad spend, impressions, and conversions',
        href: `/business/${bId}/growth?tab=campaigns`,
        icon: Megaphone,
      },
      // Developer
      {
        id: 'dev-ui-kit',
        category: 'Developer',
        title: 'UI Kit Gallery',
        subtitle: 'Interactive component gallery and enterprise design tokens testbed',
        href: `/business/${bId}/ui-kit`,
        icon: Boxes,
      },
    ]
  }, [businessId])

  // Filter items based on query
  const filteredItems = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return searchItems.slice(0, 8)
    return searchItems.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.subtitle.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q),
    )
  }, [query, searchItems])

  // Reset selectedIndex when results change or dialog opens
  useEffect(() => {
    setSelectedIndex(0)
  }, [query, isOpen])

  // Auto focus input when dialog opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        inputRef.current?.focus()
      }, 50)
    } else {
      setQuery('')
    }
  }, [isOpen])

  // Keyboard navigation
  function handleKeyDown(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (filteredItems[selectedIndex]) {
        selectItem(filteredItems[selectedIndex])
      }
    }
  }

  function selectItem(item) {
    onClose()
    router.push(item.href)
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Quick Navigation & Search"
      description="Jump instantly to any workspace, resource list, or configuration panel."
      size="md"
      className="quick-search-modal"
    >
      <div className="quick-search-body" onKeyDown={handleKeyDown}>
        <div className="quick-search-input-wrap">
          <Input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search workspaces, orders, customers, settings..."
            aria-label="Search across Bizora workspaces and resources"
            prefix={<Search size={16} className="text-muted" aria-hidden="true" />}
            autoComplete="off"
            spellCheck={false}
          />
        </div>

        <div className="quick-search-results" role="listbox" aria-label="Search results">
          {filteredItems.length === 0 ? (
            <div className="quick-search-empty">
              <p className="text-muted">No matching workspaces or resources found for &quot;{query}&quot;</p>
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const Icon = item.icon
              const isSelected = index === selectedIndex
              return (
                <div
                  key={item.id}
                  id={`search-option-${index}`}
                  role="option"
                  aria-selected={isSelected}
                  className={`quick-search-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => selectItem(item)}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <div className="quick-search-item-icon">
                    <Icon size={18} aria-hidden="true" />
                  </div>
                  <div className="quick-search-item-content">
                    <div className="quick-search-item-header">
                      <span className="quick-search-item-title">{item.title}</span>
                      <span className="quick-search-item-category">{item.category}</span>
                    </div>
                    <div className="quick-search-item-subtitle">{item.subtitle}</div>
                  </div>
                  <div className="quick-search-item-action" aria-hidden="true">
                    <ArrowRight size={14} className="text-muted" />
                  </div>
                </div>
              )
            })
          )}
        </div>

        <div className="quick-search-footer">
          <span className="quick-search-shortcut-hint">
            <kbd>↑</kbd> <kbd>↓</kbd> to navigate · <kbd>↵</kbd> to select · <kbd>Esc</kbd> to dismiss
          </span>
        </div>
      </div>
    </Dialog>
  )
}

export default QuickSearchDialog
