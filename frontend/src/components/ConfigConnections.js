'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Banner } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { providersPath } from '@/lib/configuration/paths'
import { normalizePage } from '@/lib/configuration/normalize'
import { normalizeProvider, CONNECTIONS_RESOURCE } from '@/lib/configuration/integrations'
import ConfigResourceManager from './ConfigResourceManager'

export default function ConfigConnections({ businessId, role, timezone }) {
  const [providers, setProviders] = useState([])
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    let active = true
    async function loadProviders() {
      setLoadError(null)
      try {
        const data = await clientApi(providersPath(businessId, { pageSize: 100 }))
        const norm = normalizePage(data, normalizeProvider)
        if (active) {
          setProviders(norm.results)
        }
      } catch (err) {
        if (active) {
          setLoadError(err?.detail || err?.message || 'Could not load providers')
          setProviders([])
        }
      }
    }
    loadProviders()
    return () => {
      active = false
    }
  }, [businessId])

  const context = { providers }

  return (
    <div className="stack" style={{ gap: 'var(--space-4, 16px)' }}>
      {loadError && (
        <Banner variant="danger" title="Could not load providers">
          {loadError}
        </Banner>
      )}

      <p className="text-caption text-secondary">
        <Link href={`/business/${businessId}/admin/integrations`} className="text-primary hover:underline">
          Open Integrations & Sync for health, syncs and connection tests
        </Link>
      </p>

      <ConfigResourceManager
        resource={CONNECTIONS_RESOURCE}
        context={context}
        businessId={businessId}
        role={role}
        timezone={timezone}
      />
    </div>
  )
}
