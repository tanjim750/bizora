'use client'

import React from 'react'
import { Sparkles } from 'lucide-react'

/**
 * Enterprise badge indicating sample, simulated, or demo data.
 * HARD RULE: Never invent data silently; sample data must be visibly marked.
 */
export function SimulatedBadge({
  tooltip = 'This metric or record is simulated for demonstration and not an authoritative production record.',
  size = 'md',
  className = '',
  ...props
}) {
  const sizeClass = size === 'sm' ? 'badge-sm' : ''

  return (
    <span
      className={`badge badge-ai simulated-badge ${sizeClass} ${className}`.trim()}
      title={tooltip}
      {...props}
    >
      <Sparkles size={size === 'sm' ? 10 : 12} aria-hidden="true" />
      <span>SIMULATED</span>
    </span>
  )
}

export default SimulatedBadge
