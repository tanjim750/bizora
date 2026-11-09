'use client'

import React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './Button.js'

/**
 * Enterprise pagination component.
 * Displays tabular item range '1–25 of 1,284' and accessible page controls.
 */
export function Pagination({ page = 1, pageSize = 25, total = 0, onPageChange, className = '', ...props }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const startItem = total === 0 ? 0 : (page - 1) * pageSize + 1
  const endItem = Math.min(page * pageSize, total)

  const hasPrev = page > 1
  const hasNext = page < totalPages

  return (
    <nav aria-label="Pagination" className={`pagination-component ${className}`.trim()} {...props}>
      <div className="pagination-range font-mono">
        <span>
          {startItem.toLocaleString()}–{endItem.toLocaleString()}
        </span>
        <span className="pagination-range-of"> of </span>
        <span>{total.toLocaleString()}</span>
      </div>

      <div className="pagination-controls">
        <Button
          variant="secondary"
          size="sm"
          disabled={!hasPrev}
          onClick={() => onPageChange && onPageChange(page - 1)}
          aria-label="Previous page"
          icon={ChevronLeft}
        >
          Previous
        </Button>
        <span className="pagination-page-indicator font-mono">
          Page {page} of {totalPages}
        </span>
        <Button
          variant="secondary"
          size="sm"
          disabled={!hasNext}
          onClick={() => onPageChange && onPageChange(page + 1)}
          aria-label="Next page"
          icon={ChevronRight}
          iconPosition="right"
        >
          Next
        </Button>
      </div>
    </nav>
  )
}

export default Pagination
