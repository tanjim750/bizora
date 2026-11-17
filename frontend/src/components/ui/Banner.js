'use client'

import React from 'react'
import { Info, CheckCircle2, AlertTriangle, AlertCircle, X } from 'lucide-react'

const ICON_MAP = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
}

/**
 * Enterprise banner / alert banner.
 * Variants: info, success, warning, danger
 * WCAG: aria-live and role attributes for screen reader announcement.
 */
export function Banner({
  variant = 'info',
  title,
  children,
  icon: CustomIcon,
  onClose,
  action,
  className = '',
  ...props
}) {
  const Icon = CustomIcon || ICON_MAP[variant] || Info
  const role = variant === 'danger' ? 'alert' : 'status'

  return (
    <div role={role} className={`alert alert-${variant} banner-component ${className}`.trim()} {...props}>
      <div className="banner-icon-col">
        <Icon className="banner-icon" size={18} aria-hidden="true" />
      </div>
      <div className="banner-content-col">
        {title && <strong className="banner-title">{title}</strong>}
        {children && <div className="banner-body">{children}</div>}
      </div>
      {action && <div className="banner-action-col">{action}</div>}
      {onClose && (
        <button type="button" onClick={onClose} aria-label="Dismiss banner" className="banner-close-btn">
          <X size={16} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}

export default Banner
