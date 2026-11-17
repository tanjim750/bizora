'use client'

import React from 'react'
import { Inbox } from 'lucide-react'

/**
 * Enterprise empty state component with single action.
 */
export function EmptyState({
  icon: Icon = Inbox,
  title = 'No records found',
  description,
  action,
  className = '',
  ...props
}) {
  return (
    <div className={`empty-state ${className}`.trim()} {...props}>
      <div className="empty-state-icon-wrap" aria-hidden="true">
        <Icon className="empty-state-icon" size={32} />
      </div>
      <strong>{title}</strong>
      {description && <p>{description}</p>}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  )
}

export default EmptyState
