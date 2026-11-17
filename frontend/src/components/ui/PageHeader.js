'use client'

import React from 'react'
import Link from 'next/link'
import { ChevronRight } from 'lucide-react'

/**
 * Enterprise Page Header.
 * Renders breadcrumbs, single authoritative h1, description, and action buttons.
 */
export function PageHeader({
  title,
  description,
  breadcrumbs = [], // Array of { label, href }
  badge,
  actions,
  className = '',
  ...props
}) {
  return (
    <header className={`page-header ${className}`.trim()} {...props}>
      {breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="breadcrumbs-nav">
          <ol className="breadcrumbs-list">
            {breadcrumbs.map((crumb, idx) => {
              const isLast = idx === breadcrumbs.length - 1
              return (
                <li key={crumb.href || crumb.label} className="breadcrumb-item">
                  {idx > 0 && <ChevronRight size={12} className="breadcrumb-separator" aria-hidden="true" />}
                  {isLast || !crumb.href ? (
                    <span aria-current={isLast ? 'page' : undefined} className="breadcrumb-current">
                      {crumb.label}
                    </span>
                  ) : (
                    <Link href={crumb.href} className="breadcrumb-link">
                      {crumb.label}
                    </Link>
                  )}
                </li>
              )
            })}
          </ol>
        </nav>
      )}

      <div className="page-header-main">
        <div className="page-header-text">
          <div className="page-header-title-row">
            <h1 className="page-title">{title}</h1>
            {badge && <div className="page-header-badge">{badge}</div>}
          </div>
          {description && <p className="page-description">{description}</p>}
        </div>

        {actions && <div className="page-header-actions button-row">{actions}</div>}
      </div>
    </header>
  )
}

export default PageHeader
