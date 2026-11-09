'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { ArrowUpDown, ArrowUp, ArrowDown, AlignJustify, ListFilter } from 'lucide-react'
import { money, dateTime, relativeTime, recordTitle, stripUntrusted } from '../../lib/format/index.js'
import { RESOURCE_CONFIGS } from '../../lib/domain/resources.js'
import { StatusChip } from './StatusChip.js'
import { SeverityChip } from './SeverityChip.js'
import { Skeleton } from './Skeleton.js'
import { EmptyState } from './EmptyState.js'
import { Banner } from './Banner.js'
import { Pagination } from './Pagination.js'
import { IconButton } from './IconButton.js'

/**
 * Enterprise DataTable component.
 * Features:
 * - Typed columns (text, money, datetime, relativeTime, status, severity, entity, mono, untrusted, custom)
 * - Sticky header with sort indicators
 * - Right-aligned monospaced numerics
 * - Density toggle (compact 36px vs default 44px)
 * - Empty, loading (skeleton), and error states
 * - Pagination footer
 * - Row click opens detail drawer (?open=resource:id) or triggers onRowClick
 * - Focusable, accessible scroll wrapper
 */
export function DataTable({
  columns: explicitColumns,
  rows = [],
  resource,
  businessId,
  title,
  ariaLabel,
  isLoading = false,
  error = null,
  onRetry = null,
  emptyTitle = 'No records found',
  emptyDescription = 'Authorized records will appear here.',
  emptyAction = null,
  onRowClick,
  openInDrawer = true,
  drawerResource,
  sortColumn,
  sortDirection = 'asc',
  onSort,
  pagination, // { page, pageSize, total, onPageChange }
  density: explicitDensity,
  showDensityToggle = true,
  className = '',
  ...props
}) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [density, setDensity] = useState(explicitDensity || 'default')

  // Resolve columns from resource config if not explicitly provided
  const config = resource ? RESOURCE_CONFIGS[resource] : null
  const columns = explicitColumns ||
    config?.columns || [
      { key: 'title', label: 'Record', type: 'entity' },
      { key: 'status', label: 'Status', type: 'status' },
      { key: 'created_at', label: 'Created', type: 'datetime' },
    ]

  const handleRowClick = (row, e) => {
    // If the click came from a link or button, do not intercept
    if (e.target.closest('a, button, input, select, textarea')) return

    if (onRowClick) {
      onRowClick(row)
      return
    }

    if (openInDrawer && (drawerResource || resource) && row.id) {
      const targetRes = drawerResource || resource
      const params = new URLSearchParams(searchParams.toString())
      params.set('open', `${targetRes}:${row.id}`)
      router.push(`${pathname}?${params.toString()}`, { scroll: false })
    }
  }

  const renderCell = (row, col) => {
    const val = row[col.key]

    if (col.render) {
      return col.render(row, val)
    }

    if (val === null || val === undefined || val === '') {
      return <span className="text-muted">—</span>
    }

    switch (col.type) {
      case 'money':
        return (
          <span className="font-mono tabular-nums font-semibold">
            {money(val, row.currency || col.currency || 'BDT')}
          </span>
        )

      case 'datetime':
        return <span className="font-mono text-caption text-secondary">{dateTime(val)}</span>

      case 'relativeTime':
        return (
          <span className="text-caption text-muted" title={dateTime(val)}>
            {relativeTime(val)}
          </span>
        )

      case 'status':
        return <StatusChip status={val} record={row} size="sm" />

      case 'severity':
        return <SeverityChip severity={val} size="sm" />

      case 'entity':
        return <strong className="table-entity-title">{recordTitle(row)}</strong>

      case 'mono':
        return <span className="font-mono text-caption">{String(val)}</span>

      case 'untrusted':
        return <span className="table-untrusted-text">{stripUntrusted(val)}</span>

      case 'link':
        return businessId && (drawerResource || resource) ? (
          <Link
            href={`/business/${businessId}/records/${drawerResource || resource}/${row.id}`}
            className="row-link"
          >
            {val || 'Open'}
          </Link>
        ) : (
          String(val)
        )

      default:
        return String(val)
    }
  }

  const isInteractive = Boolean(onRowClick || (openInDrawer && (drawerResource || resource)))

  return (
    <div className={`data-table-container ${className}`.trim()} {...props}>
      {(title || showDensityToggle) && (
        <div className="data-table-toolbar">
          {title && <h3 className="data-table-title">{title}</h3>}
          {showDensityToggle && (
            <div className="data-table-toolbar-actions">
              <IconButton
                icon={AlignJustify}
                label={density === 'compact' ? 'Switch to comfortable density' : 'Switch to compact density'}
                variant="ghost"
                size="sm"
                onClick={() => setDensity(density === 'compact' ? 'default' : 'compact')}
              />
            </div>
          )}
        </div>
      )}

      {error && (
        <Banner
          variant="danger"
          title="Error loading table data"
          action={
            onRetry ? (
              <button type="button" onClick={onRetry} className="button button-sm button-secondary">
                Retry
              </button>
            ) : null
          }
        >
          {error.detail || error.message || String(error)}
        </Banner>
      )}

      <div
        tabIndex={0}
        role="region"
        aria-label={ariaLabel || `${title || 'Data'} table, scrollable`}
        className={`table-wrap density-${density}`}
      >
        <table>
          <thead>
            <tr>
              {columns.map((col) => {
                const isNumeric = col.type === 'money' || col.align === 'right'
                const isSortable = Boolean(onSort && col.sortable !== false)
                const isCurrentSort = sortColumn === col.key
                const sortIcon = isCurrentSort
                  ? sortDirection === 'desc'
                    ? ArrowDown
                    : ArrowUp
                  : ArrowUpDown

                return (
                  <th
                    key={col.key}
                    scope="col"
                    className={`${isNumeric ? 'text-right' : ''} ${isSortable ? 'is-sortable' : ''}`}
                    aria-sort={
                      isCurrentSort ? (sortDirection === 'desc' ? 'descending' : 'ascending') : undefined
                    }
                  >
                    {isSortable ? (
                      <button
                        type="button"
                        onClick={() => onSort(col.key)}
                        className="th-sort-btn"
                        aria-label={`Sort by ${col.label}`}
                      >
                        <span>{col.label}</span>
                        {React.createElement(sortIcon, {
                          size: 12,
                          className: 'th-sort-icon',
                          'aria-hidden': 'true',
                        })}
                      </button>
                    ) : (
                      <span>{col.label}</span>
                    )}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, rIdx) => (
                <tr key={`skeleton-${rIdx}`}>
                  {columns.map((col, cIdx) => (
                    <td key={`sk-${cIdx}`}>
                      <Skeleton variant="text" width={cIdx === 0 ? '70%' : '50%'} height={14} />
                    </td>
                  ))}
                </tr>
              ))
            ) : rows.length > 0 ? (
              rows.map((row, rIdx) => {
                const rowKey = row.id !== undefined && row.id !== null ? `row-${row.id}` : `idx-${rIdx}`
                return (
                  <tr
                    key={rowKey}
                    onClick={(e) => handleRowClick(row, e)}
                    className={isInteractive ? 'is-clickable' : ''}
                  >
                    {columns.map((col) => {
                      const isNumeric = col.type === 'money' || col.align === 'right'
                      return (
                        <td key={col.key} className={isNumeric ? 'text-right' : ''}>
                          {renderCell(row, col)}
                        </td>
                      )
                    })}
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan={columns.length}>
                  <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {pagination && (
        <Pagination
          page={pagination.page}
          pageSize={pagination.pageSize}
          total={pagination.total}
          onPageChange={pagination.onPageChange}
        />
      )}
    </div>
  )
}

export default DataTable
