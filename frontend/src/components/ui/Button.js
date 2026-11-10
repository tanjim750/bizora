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
  loading = false,
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
  const isActionDisabled = disabled || isLoading || loading

  const renderIcon = (iconItem, posClass) => {
    if (!iconItem) return null
    if (React.isValidElement(iconItem)) {
      return iconItem
    }
    const IconComponent = iconItem
    return <IconComponent className={posClass} size={size === 'sm' ? 14 : 16} aria-hidden="true" />
  }

  const isSpinning = isLoading || loading

  return (
    <button
      type={type}
      disabled={isActionDisabled}
      aria-busy={isSpinning ? 'true' : undefined}
      className={`button ${variantClass} ${sizeClass} ${isSpinning ? 'button-loading' : ''} ${className}`.trim()}
      {...props}
    >
      {isSpinning ? (
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
          {Icon && iconPosition === 'left' && renderIcon(Icon, 'button-icon-left')}
          <span>{children}</span>
          {Icon && iconPosition === 'right' && renderIcon(Icon, 'button-icon-right')}
        </>
      )}
    </button>
  )
}

export default Button
