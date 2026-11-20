'use client'

import React from 'react'

export default function DocsLoading() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-canvas)',
        color: 'var(--color-text-muted)',
        fontFamily: 'var(--font-plex, sans-serif)',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            width: 36,
            height: 36,
            border: '3px solid var(--color-border)',
            borderTopColor: 'var(--color-primary)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px auto',
          }}
        />
        <p style={{ margin: 0, fontSize: 'var(--text-body-sm)' }}>
          Loading Bizora Live Documentation & Pitch Deck...
        </p>
      </div>
    </div>
  )
}
