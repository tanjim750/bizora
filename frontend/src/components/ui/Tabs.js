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
  items,
  tabs,
  activeTab,
  activeKey,
  onChange,
  ariaLabel = 'Navigation tabs',
  className = '',
  ...props
}) {
  const pathname = usePathname()
  const tabList = items || tabs || []
  const currentActive = activeTab !== undefined ? activeTab : activeKey

  const isLinkTabs = tabList.some((item) => Boolean(item.href))

  if (isLinkTabs) {
    return (
      <nav aria-label={ariaLabel} className={`tabs-nav ${className}`.trim()} {...props}>
        <div className="tabs-list">
          {tabList.map((tab) => {
            const isActive =
              tab.isActive !== undefined
                ? tab.isActive
                : currentActive !== undefined
                  ? currentActive === (tab.id || tab.key)
                  : pathname === tab.href || pathname.startsWith(`${tab.href}/`)

            const Icon = tab.icon

            return (
              <Link
                key={tab.id || tab.key || tab.href}
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
        {tabList.map((tab) => {
          const tabId = tab.id || tab.key
          const isActive = currentActive === tabId
          const Icon = tab.icon

          return (
            <button
              key={tabId}
              role="tab"
              type="button"
              id={`tab-${tabId}`}
              aria-selected={isActive ? 'true' : 'false'}
              aria-controls={`tabpanel-${tabId}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onChange && onChange(tabId)}
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
