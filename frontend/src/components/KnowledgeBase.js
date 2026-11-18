'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Banner, Button, DataTable, KpiTile, StatusChip, UnavailableState } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime, enumLabel } from '@/lib/format/index.js'
import { RefreshCw } from 'lucide-react'
import {
  SOURCES_PAGE_LIMIT,
  sourcesPath,
  normalizeSources,
  sourceStatusLabel,
  sourceStatusTone,
  knowledgeErrorReason,
} from '@/lib/knowledge/api'

export default function KnowledgeBase({ businessId, timezone, title = 'Memory & Knowledge Base' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hasLoaded, setHasLoaded] = useState(false)
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const reqSeq = useRef(0)

  const handleRefresh = useCallback(() => {
    setReloadKey((k) => k + 1)
  }, [])

  useEffect(() => {
    if (!businessId) return
    const currentSeq = ++reqSeq.current
    setLoading(true)
    setError(null)

    try {
      const path = sourcesPath(businessId, { limit: SOURCES_PAGE_LIMIT })
      clientApi(path)
        .then((res) => {
          if (currentSeq !== reqSeq.current) return
          setData(normalizeSources(res))
          setLoading(false)
          setHasLoaded(true)
        })
        .catch((err) => {
          if (currentSeq !== reqSeq.current) return
          setError(err)
          setLoading(false)
          setHasLoaded(true)
        })
    } catch (err) {
      if (currentSeq === reqSeq.current) {
        setError(err)
        setLoading(false)
        setHasLoaded(true)
      }
    }
  }, [businessId, reloadKey])

  const totals = data?.totals
  const results = data?.results || []
  const total = data?.total || 0

  const columns = [
    {
      key: 'name',
      label: 'Source',
      render: (row) => (
        <div>
          <strong>{row.name || 'Unnamed source'}</strong>
          {row.source_type && (
            <div>
              <span className="muted">{enumLabel(row.source_type)}</span>
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'knowledge_type',
      label: 'Knowledge type',
      render: (row) => (row.knowledge_type ? enumLabel(row.knowledge_type) : '—'),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => (
        <StatusChip
          size="sm"
          status={row.status}
          tone={sourceStatusTone(row.status)}
          label={sourceStatusLabel(row.status)}
        />
      ),
    },
    {
      key: 'document_count',
      label: 'Documents',
      render: (row) => {
        if (row.document_count == null) return '—'
        const ready = row.ready_document_count != null ? row.ready_document_count : 0
        return `${row.document_count} (${ready} ready)`
      },
    },
    {
      key: 'chunk_count',
      label: 'Text chunks',
      render: (row) => (row.chunk_count != null ? row.chunk_count : '—'),
    },
    {
      key: 'updated_at',
      label: 'Updated',
      render: (row) => dateTime(row.updated_at, timezone),
    },
  ]

  let liveStatus = ''
  if (loading) {
    liveStatus = 'Loading the knowledge base...'
  } else if (error) {
    liveStatus = 'Could not load the knowledge base.'
  }

  return (
    <div className="stack">
      <div role="status" aria-live="polite" className="sr-only">
        {liveStatus}
      </div>

      <Banner variant="info" title="Read-only view">
        This screen shows what the Business Memory service has stored for this business: sources, documents,
        versions and text chunks. Nothing can be added, edited or deleted here.
      </Banner>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h2 style={{ margin: 0, fontSize: 'var(--text-section)' }}>{title}</h2>
        <Button
          variant="secondary"
          size="sm"
          icon={RefreshCw}
          loading={loading}
          aria-label="Refresh knowledge base"
          onClick={handleRefresh}
        >
          Refresh
        </Button>
      </div>

      {error ? (
        <UnavailableState
          title={title}
          owner="Business Memory"
          reason={knowledgeErrorReason(error)}
          action={
            <Button variant="secondary" size="sm" onClick={handleRefresh}>
              Try again
            </Button>
          }
        />
      ) : (
        <>
          <div className="grid-kpi">
            <KpiTile title="Sources" value={totals?.sources ?? null} isLoading={loading && !hasLoaded} />
            <KpiTile title="Documents" value={totals?.documents ?? null} isLoading={loading && !hasLoaded} />
            <KpiTile
              title="Ready documents"
              subtext="Ready or published"
              value={totals?.ready_documents ?? null}
              isLoading={loading && !hasLoaded}
            />
            <KpiTile title="Text chunks" value={totals?.chunks ?? null} isLoading={loading && !hasLoaded} />
          </div>

          {/* KNOWLEDGE_SEARCH_MOUNT */}

          <DataTable
            title="Sources"
            ariaLabel="Knowledge sources"
            showDensityToggle={false}
            isLoading={loading}
            columns={columns}
            rows={results}
            emptyTitle="No knowledge sources yet"
            emptyDescription="This business has no knowledge sources. Sources and documents are created by the Business Memory service; this screen only shows what is stored."
          />

          {total > results.length && (
            <p className="muted" style={{ marginTop: 'var(--space-2)' }}>
              {`Showing the first ${results.length} of ${total} sources.`}
            </p>
          )}

          {/* KNOWLEDGE_DOCUMENTS_MOUNT */}
        </>
      )}
    </div>
  )
}
