'use client'

import React, { forwardRef, useId } from 'react'

/**
 * Enterprise checkbox component with label and description.
 */
export const Checkbox = forwardRef(function Checkbox(
  {
    label,
    children,
    hint,
    id: explicitId,
    checked,
    defaultChecked,
    onChange,
    disabled = false,
    isInvalid = false,
    className = '',
    ...props
  },
  ref,
) {
  const autoId = useId()
  const id = explicitId || autoId
  const hintId = hint ? `${id}-hint` : undefined

  return (
    <div className={`checkbox-field ${disabled ? 'is-disabled' : ''} ${className}`.trim()}>
      <div className="checkbox-control">
        <input
          ref={ref}
          id={id}
          type="checkbox"
          {...(checked !== undefined ? { checked } : { defaultChecked })}
          onChange={onChange}
          disabled={disabled}
          aria-invalid={isInvalid ? 'true' : undefined}
          aria-describedby={hintId}
          className="checkbox-input"
          {...props}
        />
      </div>
      <div className="checkbox-text">
        {(label || children) && (
          <label htmlFor={id} className="checkbox-label">
            {label || children}
          </label>
        )}
        {hint && (
          <p id={hintId} className="checkbox-hint">
            {hint}
          </p>
        )}
      </div>
    </div>
  )
})

export default Checkbox
