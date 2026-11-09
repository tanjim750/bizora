'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

/**
 * Enterprise navigation tabs component.
 * Supports path-segment navigation (Link with aria-current="page")
 * and controlled in-page tab switching (role="tablist").
 */
export function Tabs({
  items = [],
  activeTab,
  onChange,
  ariaLabel = 'Navigation tabs',
  className = '',
  ...props
}) {
  const pathname = usePathname()

  const isLinkTabs = items.some((item) => Boolean(item.href))

  if (isLinkTabs) {
    return (
      <nav aria-label={ariaLabel} className={`tabs-nav ${className}`.trim()} {...props}>
        <div className="tabs-list">
          {items.map((tab) => {
            const isActive =
              tab.isActive !== undefined
                ? tab.isActive
                : activeTab !== undefined
                  ? activeTab === tab.id
                  : pathname === tab.href || pathname.startsWith(`${tab.href}/`)

            const Icon = tab.icon

            return (
              <Link
                key={tab.id || tab.href}
                href={tab.href}
                aria-current={isActive ? 'page' : undefined}
                className={`tab-item ${isActive ? 'is-active' : ''}`}
              >
                {Icon && <Icon className="tab-icon" size={16} aria-hidden="true" />}
                <span className="tab-label">{tab.label}</span>
                {tab.count !== undefined && tab.count !== null && (
                  <span className="tab-count font-mono">{tab.count}</span>
                )}
              </Link>
            )
          })}
        </div>
      </nav>
    )
  }

  return (
    <div role="tablist" aria-label={ariaLabel} className={`tabs-nav ${className}`.trim()} {...props}>
      <div className="tabs-list">
        {items.map((tab) => {
          const isActive = activeTab === tab.id
          const Icon = tab.icon

          return (
            <button
              key={tab.id}
              role="tab"
              type="button"
              id={`tab-${tab.id}`}
              aria-selected={isActive ? 'true' : 'false'}
              aria-controls={`tabpanel-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onChange && onChange(tab.id)}
              className={`tab-item ${isActive ? 'is-active' : ''}`}
            >
              {Icon && <Icon className="tab-icon" size={16} aria-hidden="true" />}
              <span className="tab-label">{tab.label}</span>
              {tab.count !== undefined && tab.count !== null && (
                <span className="tab-count font-mono">{tab.count}</span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default Tabs
