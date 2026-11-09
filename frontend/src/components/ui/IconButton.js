'use client'

import React from 'react'
import { Loader2 } from 'lucide-react'

/**
 * Enterprise icon button component.
 * Requires `label` for accessible name and tooltip.
 */
export function IconButton({
  icon: Icon,
  label,
  variant = 'ghost',
  size = 'md',
  isLoading = false,
  disabled = false,
  type = 'button',
  className = '',
  ...props
}) {
  if (!label && process.env.NODE_ENV !== 'production') {
    console.warn('IconButton: `label` prop is required for WCAG 2.2 AA accessibility.')
  }

  const variantClass =
    {
      primary: 'button-primary',
      secondary: 'button-secondary',
      ghost: 'button-ghost',
      danger: 'button-danger',
    }[variant] || 'button-ghost'

  const sizeClass = size === 'sm' ? 'button-sm' : ''
  const iconSize = size === 'sm' ? 14 : 16

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      aria-label={label}
      title={label}
      aria-busy={isLoading ? 'true' : undefined}
      className={`button icon-button ${variantClass} ${sizeClass} ${isLoading ? 'button-loading' : ''} ${className}`.trim()}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="button-spinner animate-spin" size={iconSize} aria-hidden="true" />
      ) : (
        Icon && <Icon size={iconSize} aria-hidden="true" />
      )}
    </button>
  )
}

export default IconButton
