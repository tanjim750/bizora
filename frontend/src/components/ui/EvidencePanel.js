'use client'

import React from 'react'
import { FileText, ShieldCheck, Link2 } from 'lucide-react'
import { stripUntrusted } from '../../lib/format/index.js'
import { ConfidenceMeter } from './ConfidenceMeter.js'

/**
 * Enterprise EvidencePanel for audit trails, AI reasoning grounding, and fact threads.
 */
export function EvidencePanel({
  title = 'Grounding evidence',
  items = [],
  confidence,
  source,
  description,
  className = '',
  ...props
}) {
  return (
    <div className={`evidence-panel surface ${className}`.trim()} {...props}>
      <div className="evidence-header">
        <div className="evidence-title-group">
          <div className="evidence-title-row">
            <FileText size={16} className="text-primary" aria-hidden="true" />
            <h4 className="evidence-title">{title}</h4>
          </div>
          {description && <p className="evidence-description">{description}</p>}
        </div>

        {confidence !== undefined && (
          <div className="evidence-confidence">
            <ConfidenceMeter value={confidence} label="Grounding confidence" />
          </div>
        )}
      </div>

      {source && (
        <div className="evidence-source-bar">
          <ShieldCheck size={14} className="text-success" aria-hidden="true" />
          <span className="evidence-source-text">
            Authoritative source: <strong>{source}</strong>
          </span>
        </div>
      )}

      <div className="evidence-body">
        {items.length === 0 ? (
          <p className="text-muted text-caption" style={{ margin: 0 }}>
            No grounding facts or citations recorded.
          </p>
        ) : (
          <ul className="evidence-list">
            {items.map((item, idx) => {
              const factText = typeof item === 'string' ? item : item.fact || item.text || item.summary
              const itemSource = typeof item === 'object' ? item.source || item.entity : null

              return (
                <li key={item.id || `ev-${idx}`} className="evidence-item">
                  <span className="evidence-bullet" aria-hidden="true">
                    •
                  </span>
                  <div className="evidence-item-content">
                    <p className="evidence-item-text">{stripUntrusted(factText)}</p>
                    {itemSource && (
                      <span className="evidence-item-source text-muted font-mono">
                        <Link2 size={11} aria-hidden="true" />
                        <span>{itemSource}</span>
                      </span>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

export default EvidencePanel
