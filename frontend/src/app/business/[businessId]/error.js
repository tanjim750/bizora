'use client'

import React, { useEffect } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { AlertTriangle, RefreshCw, LayoutDashboard, ArrowLeft } from 'lucide-react'
import { Banner } from '@/components/ui/Banner'
import { Button } from '@/components/ui/Button'

export default function BusinessError({ error, retry, reset }) {
  const params = useParams()
  const businessId = params?.businessId || '1'

  useEffect(() => {
    // Structured error log
    console.error('Workspace error boundary caught:', error)
  }, [error])

  const handleRetry = () => {
    if (typeof retry === 'function') {
      retry()
    } else if (typeof reset === 'function') {
      reset()
    } else {
      window.location.reload()
    }
  }

  const errorMessage =
    error?.detail ||
    error?.message ||
    'An unexpected operational error occurred while loading this workspace segment.'

  return (
    <div className="workspace-error-boundary" role="alert">
      <div className="workspace-error-content">
        <Banner variant="danger" title="Operational Request Failed" className="workspace-error-banner">
          <p>{errorMessage}</p>
          {error?.digest && (
            <p className="text-caption text-muted" style={{ marginTop: 'var(--space-1)' }}>
              Server digest reference: <code>{error.digest}</code>
            </p>
          )}
        </Banner>

        <div className="workspace-error-actions">
          <Button variant="primary" onClick={handleRetry} icon={<RefreshCw size={14} aria-hidden="true" />}>
            Retry operation
          </Button>

          <Link href={`/business/${encodeURIComponent(businessId)}/overview`} className="btn btn-secondary">
            <LayoutDashboard size={14} aria-hidden="true" />
            <span>Return to Overview</span>
          </Link>

          <Link href="/workspace" className="btn btn-ghost">
            <ArrowLeft size={14} aria-hidden="true" />
            <span>Switch workspace</span>
          </Link>
        </div>
      </div>
    </div>
  )
}
