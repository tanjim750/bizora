'use client'

import React, { forwardRef } from 'react'

/**
 * Enterprise textarea component.
 */
export const Textarea = forwardRef(function Textarea(
  { rows = 3, isInvalid = false, className = '', id, disabled = false, ...props },
  ref,
) {
  const errorClass = isInvalid ? 'is-invalid' : ''

  return (
    <textarea
      ref={ref}
      id={id}
      rows={rows}
      disabled={disabled}
      aria-invalid={isInvalid ? 'true' : undefined}
      className={`textarea-field ${errorClass} ${className}`.trim()}
      {...props}
    />
  )
})

export default Textarea
