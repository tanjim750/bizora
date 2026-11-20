'use client'

import React from 'react'

export default function DocsError({ error, reset }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-canvas)',
        padding: 'var(--space-6)',
        fontFamily: 'var(--font-plex, sans-serif)',
      }}
    >
      <div
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-8)',
          maxWidth: 480,
          textAlign: 'center',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <h2
          style={{ fontSize: 'var(--text-section)', color: 'var(--color-danger-text)', margin: '0 0 8px 0' }}
        >
          Unable to load documentation
        </h2>
        <p
          style={{
            fontSize: 'var(--text-body-sm)',
            color: 'var(--color-text-secondary)',
            margin: '0 0 16px 0',
          }}
        >
          {error?.message || 'An unexpected error occurred while loading the documentation module.'}
        </p>
        <button
          type="button"
          onClick={() => reset()}
          style={{
            padding: '8px 20px',
            background: 'var(--color-primary)',
            color: 'var(--color-on-primary)',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          Try Again
        </button>
      </div>
    </div>
  )
}
