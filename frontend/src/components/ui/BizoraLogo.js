'use client'

import React from 'react'

/**
 * Enterprise Bizora Brand Logo.
 * Multi-faceted geometric isometric cube / neural graph symbol representing
 * business operations, data graphs, and intelligence.
 */
export function BizoraLogo({ size = 32, showText = true, className = '' }) {
  return (
    <span className={`bizora-brand ${className}`.trim()}>
      <span className="bizora-logo-mark" aria-hidden="true">
        <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="bizora-logo-bg" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
              <stop stopColor="var(--color-primary, #1b4b8f)" />
              <stop offset="1" stopColor="var(--chart-1, #2a78d6)" />
            </linearGradient>
            <linearGradient
              id="bizora-logo-specular"
              x1="16"
              y1="2"
              x2="16"
              y2="30"
              gradientUnits="userSpaceOnUse"
            >
              <stop stopColor="#ffffff" stopOpacity="0.35" />
              <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
            </linearGradient>
          </defs>
          {/* Rounded squircle base */}
          <rect x="2" y="2" width="28" height="28" rx="7.5" fill="url(#bizora-logo-bg)" />
          <rect
            x="2.5"
            y="2.5"
            width="27"
            height="27"
            rx="7"
            stroke="url(#bizora-logo-specular)"
            strokeWidth="1"
          />

          {/* Isometric faceted business graph geometry */}
          <path
            d="M16 6.5L24.5 11.2V20.8L16 25.5L7.5 20.8V11.2L16 6.5Z"
            stroke="#ffffff"
            strokeWidth="1.6"
            strokeLinejoin="round"
            fill="rgba(255, 255, 255, 0.08)"
          />
          {/* Internal isometric coordinate axes */}
          <path
            d="M16 6.5V25.5M7.5 11.2L16 16L24.5 11.2M7.5 20.8L16 16L24.5 20.8"
            stroke="#ffffff"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          {/* Core Central Node (Business Brain) */}
          <circle cx="16" cy="16" r="2.5" fill="#ffffff" />
          {/* Peripheral intelligence satellite nodes */}
          <circle cx="16" cy="6.5" r="1.5" fill="#ffffff" />
          <circle cx="24.5" cy="20.8" r="1.5" fill="#ffffff" />
          <circle cx="7.5" cy="20.8" r="1.5" fill="#ffffff" />
        </svg>
      </span>

      {showText && (
        <span className="bizora-brand-text">
          bizora<span className="bizora-brand-dot">.</span>
        </span>
      )}
    </span>
  )
}

export default BizoraLogo
