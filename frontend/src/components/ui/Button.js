'use client'

import React from 'react'
import { Loader2 } from 'lucide-react'

/**
 * Enterprise button component.
 * Variants: primary, secondary, ghost, danger
 * Sizes: sm (28px), md (36px)
 * States: default, hover, focus, disabled, loading
 */
export function Button({
  children,
  variant = 'secondary',
  size = 'md',
  isLoading = false,
  disabled = false,
  type = 'button',
  icon: Icon = null,
  iconPosition = 'left',
  className = '',
  ...props
}) {
  const variantClass =
    {
      primary: 'button-primary',
      secondary: 'button-secondary',
      ghost: 'button-ghost',
      danger: 'button-danger',
    }[variant] || 'button-secondary'

  const sizeClass = size === 'sm' ? 'button-sm' : ''
  const isActionDisabled = disabled || isLoading

  return (
    <button
      type={type}
      disabled={isActionDisabled}
      aria-busy={isLoading ? 'true' : undefined}
      className={`button ${variantClass} ${sizeClass} ${isLoading ? 'button-loading' : ''} ${className}`.trim()}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2
            className="button-spinner animate-spin"
            size={size === 'sm' ? 14 : 16}
            aria-hidden="true"
          />
          <span>{children}</span>
        </>
      ) : (
        <>
          {Icon && iconPosition === 'left' && (
            <Icon className="button-icon-left" size={size === 'sm' ? 14 : 16} aria-hidden="true" />
          )}
          <span>{children}</span>
          {Icon && iconPosition === 'right' && (
            <Icon className="button-icon-right" size={size === 'sm' ? 14 : 16} aria-hidden="true" />
          )}
        </>
      )}
    </button>
  )
}

export default Button
