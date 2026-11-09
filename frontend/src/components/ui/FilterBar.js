'use client'

import React from 'react'
import { Search, X } from 'lucide-react'
import { Input } from './Input.js'
import { Button } from './Button.js'

/**
 * Enterprise filter bar for data tables and resource lists.
 * Supports search input, custom filter controls, and active filter pill removal.
 */
export function FilterBar({
  searchValue = '',
  onSearchChange,
  searchPlaceholder = 'Search records...',
  isSearchDisabled = false,
  activeFilters = [], // Array of { key, label, value, onRemove }
  onClearAll,
  children,
  className = '',
  ...props
}) {
  const hasActiveFilters = activeFilters.length > 0 || Boolean(searchValue)

  return (
    <div className={`filter-bar ${className}`.trim()} {...props}>
      <div className="filter-bar-main">
        {!isSearchDisabled && (
          <div className="filter-search-wrap">
            <Input
              type="search"
              size="sm"
              value={searchValue}
              onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
              placeholder={searchPlaceholder}
              prefix={<Search size={14} className="text-muted" aria-hidden="true" />}
              suffix={
                searchValue ? (
                  <button
                    type="button"
                    onClick={() => onSearchChange && onSearchChange('')}
                    className="filter-clear-search-btn"
                    aria-label="Clear search"
                  >
                    <X size={12} aria-hidden="true" />
                  </button>
                ) : null
              }
            />
          </div>
        )}

        {children && <div className="filter-controls-group">{children}</div>}

        {hasActiveFilters && onClearAll && (
          <Button variant="ghost" size="sm" onClick={onClearAll} className="filter-clear-all-btn">
            Clear filters
          </Button>
        )}
      </div>

      {activeFilters.length > 0 && (
        <div className="filter-chips-row">
          <span className="filter-chips-label">Active filters:</span>
          {activeFilters.map((filter) => (
            <span key={filter.key} className="badge badge-neutral filter-pill">
              <span className="filter-pill-label">{filter.label}:</span>
              <strong className="filter-pill-value">{filter.value}</strong>
              <button
                type="button"
                onClick={filter.onRemove}
                className="filter-pill-remove"
                aria-label={`Remove filter for ${filter.label}`}
              >
                <X size={12} aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default FilterBar
