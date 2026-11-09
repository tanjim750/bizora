'use client'

import React from 'react'
import { ArrowUpRight, ArrowDownRight, Minus, CircleOff } from 'lucide-react'
import { Skeleton } from './Skeleton.js'

/**
 * Enterprise KPI tile.
 * Displays metric title, monospaced tabular value, trend indicator, and subtext.
 * Handles loading skeleton and calm "Not connected" unavailable state.
 */
export function KpiTile({
  title,
  value,
  trend,
  trendDirection = 'neutral', // 'up' | 'down' | 'neutral'
  trendLabel,
  subtext,
  isLoading = false,
  isUnavailable = false,
  unavailableOwner,
  unavailableReason,
  className = '',
  ...props
}) {
  if (isLoading) {
    return (
      <div className={`metric-card kpi-tile is-loading ${className}`.trim()} {...props}>
        <Skeleton variant="text" width="50%" height={16} />
        <div style={{ margin: 'var(--space-3) 0 var(--space-2)' }}>
          <Skeleton variant="text" width="75%" height={32} />
        </div>
        <Skeleton variant="text" width="40%" height={14} />
      </div>
    )
  }

  if (isUnavailable || value === 'UNAVAILABLE') {
    return (
      <div className={`metric-card kpi-tile is-unavailable ${className}`.trim()} {...props}>
        <h2>{title}</h2>
        <div className="kpi-unavailable-body">
          <CircleOff size={16} className="text-muted" aria-hidden="true" />
          <span className="kpi-unavailable-tag">Not connected</span>
        </div>
        <p className="kpi-unavailable-reason">{unavailableReason || 'Data source not configured'}</p>
        {unavailableOwner && <span className="kpi-unavailable-owner">Owner: {unavailableOwner}</span>}
      </div>
    )
  }

  const TrendIcon =
    trendDirection === 'up' ? ArrowUpRight : trendDirection === 'down' ? ArrowDownRight : Minus

  const trendClass =
    trendDirection === 'up' ? 'trend-up' : trendDirection === 'down' ? 'trend-down' : 'trend-neutral'

  return (
    <div className={`metric-card kpi-tile ${className}`.trim()} {...props}>
      <h2>{title}</h2>
      <strong className="kpi-value font-mono">
        {value !== null && value !== undefined && value !== '' ? value : '—'}
      </strong>
      <p>
        {trend && (
          <span className={`kpi-trend ${trendClass}`}>
            <TrendIcon size={14} aria-hidden="true" />
            <span>{trend}</span>
          </span>
        )}
        {trendLabel && <span className="kpi-trend-label">{trendLabel}</span>}
        {subtext && <span className="kpi-subtext">{subtext}</span>}
      </p>
    </div>
  )
}

export default KpiTile
