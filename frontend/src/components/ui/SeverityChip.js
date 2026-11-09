'use client'

import React from 'react'
import { AlertCircle, AlertTriangle, Info, ShieldAlert } from 'lucide-react'
import { enumLabel } from '../../lib/format/index.js'

const SEVERITY_CONFIG = {
  CRITICAL: { tone: 'danger', icon: ShieldAlert },
  HIGH: { tone: 'danger', icon: AlertCircle },
  MEDIUM: { tone: 'warning', icon: AlertTriangle },
  LOW: { tone: 'info', icon: Info },
  INFO: { tone: 'neutral', icon: Info },
}

/**
 * Enterprise severity chip for issues, audits, and security alerts.
 */
export function SeverityChip({ severity = 'INFO', size = 'md', className = '', ...props }) {
  const norm = String(severity).toUpperCase()
  const config = SEVERITY_CONFIG[norm] || SEVERITY_CONFIG.INFO
  const Icon = config.icon
  const sizeClass = size === 'sm' ? 'badge-sm' : ''

  return (
    <span className={`badge badge-${config.tone} severity-chip ${sizeClass} ${className}`.trim()} {...props}>
      <Icon className="severity-icon" size={size === 'sm' ? 12 : 13} aria-hidden="true" />
      <span className="severity-label">{enumLabel(norm)}</span>
    </span>
  )
}

export default SeverityChip
