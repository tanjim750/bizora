'use client'

import React from 'react'
import { CircleOff } from 'lucide-react'

/**
 * Enterprise "Not connected" state for unavailable backend services.
 * HARD RULE: UNAVAILABLE is normal data. Show a calm "Not connected" state
 * naming the owner and the reason. Never an error style, never a zero.
 */
export function UnavailableState({
  owner = 'Service provider',
  reason = 'This capability is not connected or configured for this business.',
  title = 'Not connected',
  action,
  className = '',
  ...props
}) {
  return (
    <div className={`unavailable-state ${className}`.trim()} {...props}>
      <div className="unavailable-icon-wrap" aria-hidden="true">
        <CircleOff className="unavailable-icon" size={28} />
      </div>
      <strong>{title}</strong>
      <p className="unavailable-reason">{reason}</p>
      <div className="unavailable-meta">
        <span className="unavailable-owner-badge">Owner: {owner}</span>
      </div>
      {action && <div className="unavailable-action">{action}</div>}
    </div>
  )
}

export default UnavailableState
