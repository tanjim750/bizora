'use client'

import React, { forwardRef } from 'react'
import { Input } from './Input.js'

/**
 * Enterprise money input field.
 * Displays currency prefix, enforces decimal input, monospace font.
 */
export const MoneyField = forwardRef(function MoneyField(
  {
    currency = 'BDT',
    value,
    onChange,
    min = '0.00',
    step = '0.01',
    placeholder = '0.00',
    className = '',
    id,
    disabled = false,
    isInvalid = false,
    ...props
  },
  ref,
) {
  const handleChange = (e) => {
    const val = e.target.value
    // Allow empty or valid decimal numbers with up to 2 decimal places
    if (val === '' || /^\d*(\.\d{0,2})?$/.test(val)) {
      if (onChange) onChange(e)
    }
  }

  return (
    <Input
      ref={ref}
      id={id}
      type="text"
      inputMode="decimal"
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      prefix={<span className="font-mono">{currency}</span>}
      disabled={disabled}
      isInvalid={isInvalid}
      className={`money-field font-mono ${className}`.trim()}
      {...props}
    />
  )
})

export default MoneyField
