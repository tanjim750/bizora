'use client'

import React from 'react'

/**
 * Enterprise confidence meter for AI recommendations, entity resolution, and predictions.
 */
export function ConfidenceMeter({
  value,
  label = 'Confidence',
  showPercentage = true,
  className = '',
  ...props
}) {
  if (value === null || value === undefined || value === 'UNAVAILABLE') {
    return <span className="confidence-meter-empty text-muted">—</span>
  }

  // Handle both 0..1 and 0..100 ranges
  const num = typeof value === 'number' ? value : parseFloat(value) || 0
  const normalized = num <= 1.0 ? Math.round(num * 100) : Math.round(num)
  const clamped = Math.max(0, Math.min(100, normalized))

  const tone = clamped >= 80 ? 'high' : clamped >= 50 ? 'medium' : 'low'

  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={`confidence-meter meter-${tone} ${className}`.trim()}
      {...props}
    >
      <div className="confidence-track">
        <div className="confidence-fill" style={{ width: `${clamped}%` }} />
      </div>
      {showPercentage && <span className="confidence-value font-mono">{clamped}%</span>}
    </div>
  )
}

export default ConfidenceMeter
