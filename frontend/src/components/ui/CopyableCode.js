'use client'

import React, { useState } from 'react'
import { Copy, Check } from 'lucide-react'

/**
 * Enterprise copyable code and ID component.
 * Supports inline or block presentation with feedback.
 */
export function CopyableCode({
  value,
  code,
  label = 'code snippet',
  inline = true,
  truncate = false,
  className = '',
  ...props
}) {
  const [copied, setCopied] = useState(false)

  const effectiveValue = value !== undefined ? value : code
  const stringValue =
    typeof effectiveValue === 'object' && effectiveValue !== null
      ? JSON.stringify(effectiveValue, null, 2)
      : String(effectiveValue ?? '')

  const handleCopy = async (e) => {
    e.stopPropagation()
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(stringValue)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }
    } catch {
      // Fallback if clipboard API is restricted
    }
  }

  if (inline) {
    return (
      <span
        className={`copyable-code inline-mode ${truncate ? 'is-truncated' : ''} ${className}`.trim()}
        {...props}
      >
        <code className="font-mono copyable-text">{stringValue}</code>
        <button
          type="button"
          onClick={handleCopy}
          className="copy-btn"
          aria-label={copied ? 'Copied to clipboard' : `Copy ${label}`}
          title={copied ? 'Copied!' : 'Copy to clipboard'}
        >
          {copied ? (
            <Check size={12} className="text-success" aria-hidden="true" />
          ) : (
            <Copy size={12} aria-hidden="true" />
          )}
        </button>
      </span>
    )
  }

  return (
    <div className={`copyable-code block-mode ${className}`.trim()} {...props}>
      <div className="copyable-header">
        <span className="copyable-label text-caption text-muted">{label}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="copy-btn-block button button-sm button-ghost"
          aria-label={copied ? 'Copied to clipboard' : `Copy ${label}`}
        >
          {copied ? (
            <>
              <Check size={12} className="text-success" aria-hidden="true" />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy size={12} aria-hidden="true" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="font-mono copyable-pre">
        <code>{stringValue}</code>
      </pre>
    </div>
  )
}

export default CopyableCode
