'use client'

import React from 'react'
import {
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Sparkles,
  CircleOff,
  Clock,
  MinusCircle,
  Radio,
} from 'lucide-react'
import { statusTone, statusText, enumLabel } from '../../lib/format/index.js'

const TONE_ICONS = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
  ai: Sparkles,
  unavailable: CircleOff,
  'not-mounted': Radio,
  neutral: Clock,
}

/**
 * Enterprise status chip.
 * HARD RULE: Status is never colour alone: every chip has an icon and a label.
 */
export function StatusChip({
  status,
  record,
  tone: explicitTone,
  label: explicitLabel,
  size = 'md',
  className = '',
  ...props
}) {
  const tone = explicitTone || statusTone(status)
  const label = explicitLabel || (record ? statusText(record) : enumLabel(status))

  const Icon = TONE_ICONS[tone] || MinusCircle
  const sizeClass = size === 'sm' ? 'badge-sm' : ''

  return (
    <span className={`badge badge-${tone} status-chip ${sizeClass} ${className}`.trim()} {...props}>
      <Icon className="status-chip-icon" size={size === 'sm' ? 12 : 13} aria-hidden="true" />
      <span className="status-chip-label">{label}</span>
    </span>
  )
}

export default StatusChip
