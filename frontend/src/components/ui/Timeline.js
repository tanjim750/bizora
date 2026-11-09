'use client'

import React from 'react'
import { Clock, CheckCircle2, AlertTriangle, AlertCircle, Sparkles, Circle } from 'lucide-react'
import { dateTime, relativeTime } from '../../lib/format/index.js'
import { StatusChip } from './StatusChip.js'

/**
 * Enterprise Timeline: the evidence thread.
 * Clean, structured vertical timeline with thin continuous guide line and small nodes.
 */
export function Timeline({ events = [], showRelativeTime = false, className = '', ...props }) {
  if (events.length === 0) {
    return <div className="timeline-empty text-muted text-caption">No timeline events recorded.</div>
  }

  return (
    <ol className={`timeline-thread ${className}`.trim()} {...props}>
      {events.map((event, idx) => {
        const isLast = idx === events.length - 1
        const Icon = event.icon || (event.is_ai ? Sparkles : Circle)
        const timeDisplay = showRelativeTime ? relativeTime(event.timestamp) : dateTime(event.timestamp)

        return (
          <li
            key={event.id || `evt-${idx}`}
            className={`timeline-item ${event.tone ? `tone-${event.tone}` : ''} ${isLast ? 'is-last' : ''}`}
          >
            <div className="timeline-node" aria-hidden="true">
              <Icon size={12} className="timeline-node-icon" />
            </div>

            <div className="timeline-content">
              <div className="timeline-header">
                <span className="timeline-title">{event.title}</span>
                {event.status && <StatusChip status={event.status} size="sm" className="timeline-status" />}
                {event.timestamp && (
                  <time
                    dateTime={event.timestamp}
                    title={dateTime(event.timestamp)}
                    className="timeline-time font-mono text-caption"
                  >
                    {timeDisplay}
                  </time>
                )}
              </div>

              {event.description && <p className="timeline-description">{event.description}</p>}

              {event.metadata && (
                <div className="timeline-metadata">
                  {Object.entries(event.metadata).map(([k, v]) => (
                    <span key={k} className="timeline-meta-pill">
                      <span className="text-muted">{k}:</span> {String(v)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export default Timeline
