'use client'

import React, { forwardRef } from 'react'
import { Calendar } from 'lucide-react'
import { Input } from './Input.js'

/**
 * Enterprise date/time input field with business timezone indicator.
 */
export const DateTimeField = forwardRef(function DateTimeField(
  {
    type = 'datetime-local',
    timezone = 'Asia/Dhaka',
    className = '',
    id,
    disabled = false,
    isInvalid = false,
    ...props
  },
  ref,
) {
  return (
    <div className="datetime-field-wrap">
      <Input
        ref={ref}
        id={id}
        type={type}
        prefix={<Calendar size={14} className="text-muted" aria-hidden="true" />}
        suffix={<span className="datetime-tz-badge">{timezone}</span>}
        disabled={disabled}
        isInvalid={isInvalid}
        className={`datetime-field ${className}`.trim()}
        {...props}
      />
    </div>
  )
})

export default DateTimeField
