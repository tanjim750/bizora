import React from 'react'
import Link from 'next/link'
import { FileQuestion, LayoutDashboard, ArrowLeft } from 'lucide-react'

export const metadata = {
  title: 'Record or Section Not Found (404)',
  description: 'The requested record or resource was not found in this business.',
}

export default function BusinessNotFound() {
  return (
    <div className="workspace-not-found-card" role="main">
      <div className="not-found-icon-wrap" aria-hidden="true">
        <FileQuestion size={36} className="text-muted" />
      </div>
      <span className="not-found-code">404 — Not Found</span>
      <h1>Record or Section Not Found</h1>
      <p className="not-found-lead">
        The requested record, view, or configuration does not exist in this business workspace or may have
        been deleted.
      </p>

      <div className="not-found-actions">
        <Link href="/workspace" className="btn btn-primary">
          <LayoutDashboard size={14} aria-hidden="true" />
          <span>Return to business overview</span>
        </Link>
        <Link href="/workspace" className="btn btn-secondary">
          <ArrowLeft size={14} aria-hidden="true" />
          <span>Switch business</span>
        </Link>
      </div>
    </div>
  )
}
