'use client'

import React, { useId } from 'react'

/**
 * Enterprise form field container.
 * Associates label, control, hint, and error messages via WCAG AA attributes.
 */
export function Field({
  label,
  id: explicitId,
  htmlFor,
  hint,
  error,
  required = false,
  children,
  className = '',
}) {
  const autoId = useId()
  const id = explicitId || htmlFor || autoId
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined

  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className={`form-field ${error ? 'has-error' : ''} ${className}`.trim()}>
      {label && (
        <label htmlFor={id} className="form-label">
          <span>{label}</span>
          {required && (
            <span className="form-required" aria-hidden="true">
              {' '}
              *
            </span>
          )}
          {required && <span className="sr-only"> (required)</span>}
        </label>
      )}

      <div className="form-control-wrap">
        {React.isValidElement(children)
          ? React.cloneElement(children, {
              id: children.props.id || id,
              'aria-describedby': children.props['aria-describedby'] || describedBy,
              'aria-invalid': error ? 'true' : children.props['aria-invalid'],
              isInvalid: Boolean(error) || children.props.isInvalid,
              required: required || children.props.required,
            })
          : children}
      </div>

      {hint && !error && (
        <p id={hintId} className="form-hint">
          {hint}
        </p>
      )}

      {error && (
        <p id={errorId} className="form-error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

export default Field
