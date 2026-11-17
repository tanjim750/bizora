'use client'

import React from 'react'

/**
 * Enterprise loading skeleton shaped like the final layout.
 * Always aria-hidden="true" to prevent screen reader clutter.
 */
export function Skeleton({ variant = 'text', width, height, count = 1, className = '', ...props }) {
  const items = Array.from({ length: count }, (_, i) => i)

  return (
    <>
      {items.map((key) => (
        <span
          key={key}
          aria-hidden="true"
          className={`skeleton skeleton-${variant} ${className}`.trim()}
          style={{
            width: width !== undefined ? width : undefined,
            height: height !== undefined ? height : undefined,
          }}
          {...props}
        />
      ))}
    </>
  )
}

export default Skeleton
