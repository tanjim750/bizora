'use client'

import React, { forwardRef } from 'react'
import { ChevronDown } from 'lucide-react'

/**
 * Enterprise select component.
 * Uses native <select> for 100% accessibility and mobile support,
 * with styled wrapper and tokens.
 */
export const Select = forwardRef(function Select(
  {
    options = [],
    placeholder,
    isInvalid = false,
    size = 'md',
    className = '',
    id,
    disabled = false,
    children,
    ...props
  },
  ref,
) {
  const sizeClass = size === 'sm' ? 'select-sm' : ''
  const errorClass = isInvalid ? 'is-invalid' : ''

  return (
    <div
      className={`select-wrap ${sizeClass} ${errorClass} ${disabled ? 'is-disabled' : ''} ${className}`.trim()}
    >
      <select
        ref={ref}
        id={id}
        disabled={disabled}
        aria-invalid={isInvalid ? 'true' : undefined}
        className="select-field"
        {...props}
      >
        {placeholder && (
          <option value="" disabled hidden>
            {placeholder}
          </option>
        )}
        {options.length > 0
          ? options.map((opt) => (
              <option key={opt.value ?? opt} value={opt.value ?? opt} disabled={opt.disabled}>
                {opt.label ?? opt}
              </option>
            ))
          : children}
      </select>
      <ChevronDown className="select-chevron" size={14} aria-hidden="true" />
    </div>
  )
})

export default Select
