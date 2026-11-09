'use client'

import React, { forwardRef } from 'react'

/**
 * Enterprise text input component.
 * Supports prefix/suffix icons/text, sizes, invalid state.
 */
export const Input = forwardRef(function Input(
  {
    type = 'text',
    isInvalid = false,
    size = 'md',
    prefix = null,
    suffix = null,
    className = '',
    id,
    disabled = false,
    ...props
  },
  ref,
) {
  const sizeClass = size === 'sm' ? 'input-sm' : ''
  const errorClass = isInvalid ? 'is-invalid' : ''

  if (prefix || suffix) {
    return (
      <div
        className={`input-group ${sizeClass} ${errorClass} ${disabled ? 'is-disabled' : ''} ${className}`.trim()}
      >
        {prefix && <span className="input-affix input-prefix">{prefix}</span>}
        <input
          ref={ref}
          id={id}
          type={type}
          disabled={disabled}
          aria-invalid={isInvalid ? 'true' : undefined}
          className="input-field"
          {...props}
        />
        {suffix && <span className="input-affix input-suffix">{suffix}</span>}
      </div>
    )
  }

  return (
    <input
      ref={ref}
      id={id}
      type={type}
      disabled={disabled}
      aria-invalid={isInvalid ? 'true' : undefined}
      className={`input-field ${sizeClass} ${errorClass} ${className}`.trim()}
      {...props}
    />
  )
})

export default Input
