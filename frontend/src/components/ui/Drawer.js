'use client'

import React, { useEffect, useRef, useId } from 'react'
import { X } from 'lucide-react'
import { IconButton } from './IconButton.js'

/**
 * Enterprise right-sliding drawer panel.
 * WCAG 2.2 AA compliant: focus trap, Escape key handling, aria-modal, body scroll lock.
 */
export function Drawer({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  footer,
  width = '480px',
  ariaLabel,
  className = '',
}) {
  const autoId = useId()
  const titleId = `drawer-title-${autoId}`
  const drawerRef = useRef(null)
  const previousActiveElementRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return

    previousActiveElementRef.current = document.activeElement

    // Lock body scroll
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    // Focus first focusable element inside drawer or the drawer itself
    const timer = setTimeout(() => {
      if (drawerRef.current) {
        const focusables = drawerRef.current.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        )
        if (focusables.length > 0) {
          focusables[0].focus()
        } else {
          drawerRef.current.focus()
        }
      }
    }, 50)

    // Escape listener and tab trap
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        if (onClose) onClose()
        return
      }

      if (e.key === 'Tab' && drawerRef.current) {
        const focusables = Array.from(
          drawerRef.current.querySelectorAll(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
          ),
        )
        if (focusables.length === 0) return

        const first = focusables[0]
        const last = focusables[focusables.length - 1]

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
      clearTimeout(timer)
      if (previousActiveElementRef.current?.focus) {
        previousActiveElementRef.current.focus()
      }
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-label={!title ? ariaLabel || 'Details panel' : undefined}
        tabIndex={-1}
        className={`drawer-panel ${className}`.trim()}
        style={{ '--drawer-width': width }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="drawer-header">
          <div className="drawer-title-group">
            {title && (
              <h2 id={titleId} className="drawer-title">
                {title}
              </h2>
            )}
            {subtitle && <p className="drawer-subtitle">{subtitle}</p>}
          </div>
          <IconButton
            icon={X}
            label="Close drawer"
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="drawer-close-btn"
          />
        </div>

        <div className="drawer-body">{children}</div>

        {footer && <div className="drawer-footer">{footer}</div>}
      </div>
    </div>
  )
}

export default Drawer
