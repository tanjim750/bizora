import React from 'react'
import Link from 'next/link'
import { FileQuestion, ArrowRight } from 'lucide-react'

export const metadata = {
  title: 'Page Not Found (404)',
  description: 'The requested page or record could not be found.',
}

export default function NotFound() {
  return (
    <div className="not-found-screen">
      <main className="not-found-card" role="main">
        <div className="not-found-icon-wrap" aria-hidden="true">
          <FileQuestion size={36} className="text-muted" />
        </div>
        <span className="not-found-code">404 Error</span>
        <h1>Page not found</h1>
        <p className="not-found-lead">
          The requested record, workspace, or resource does not exist or has been moved to another location.
        </p>

        <div className="not-found-actions">
          <Link href="/workspace" className="btn btn-primary">
            <span>Return to workspaces</span>
            <ArrowRight size={14} aria-hidden="true" />
          </Link>
          <Link href="/login" className="btn btn-secondary">
            Sign in as different user
          </Link>
        </div>
      </main>
    </div>
  )
}
