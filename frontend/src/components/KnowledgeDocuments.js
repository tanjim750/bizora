'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { DataTable, Field, Select, StatusChip } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime, enumLabel } from '@/lib/format/index.js'
import {
  DOCUMENTS_PAGE_LIMIT,
  DOCUMENT_STATUS_ORDER,
  documentsPath,
  documentStatusLabel,
  documentStatusTone,
  searchabilityNote,
  normalizeDocuments,
  offsetForPage,
} from '@/lib/knowledge/documents'
import { knowledgeErrorReason } from '@/lib/knowledge/api'

export default function KnowledgeDocuments({
  businessId,
  timezone,
  sources = [],
  sourceId = '',
  onSourceChange,
  refreshKey = 0,
}) {
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const reqSeq = useRef(0)

  const prevSourceId = useRef(sourceId)
  useEffect(() => {
    if (prevSourceId.current !== sourceId) {
      setPage(1)
      prevSourceId.current = sourceId
    }
  }, [sourceId])

  const handleSourceChange = (e) => {
    const nextVal = e.target.value
    if (onSourceChange) {
      onSourceChange(nextVal)
    }
    setPage(1)
  }

  const handleStatusChange = (e) => {
    setStatusFilter(e.target.value)
    setPage(1)
  }

  useEffect(() => {
    if (!businessId) return
    const currentSeq = ++reqSeq.current
    setLoading(true)
    setError(null)

    try {
      const path = documentsPath(businessId, {
        source: sourceId || undefined,
        status: statusFilter || undefined,
        limit: DOCUMENTS_PAGE_LIMIT,
        offset: offsetForPage(page, DOCUMENTS_PAGE_LIMIT),
      })

      clientApi(path)
        .then((res) => {
          if (currentSeq !== reqSeq.current) return
          setData(normalizeDocuments(res))
          setLoading(false)
        })
        .catch((err) => {
          if (currentSeq !== reqSeq.current) return
          setError(err)
          setLoading(false)
        })
    } catch (err) {
      if (currentSeq === reqSeq.current) {
        setError(err)
        setLoading(false)
      }
    }
  }, [businessId, sourceId, statusFilter, page, refreshKey, retryCount])

  const results = data?.results || []
  const total = data?.total || 0

  const columns = [
    {
      key: 'title',
      label: 'Document',
      render: (row) => (
        <div>
          <strong>{row.title || 'Untitled document'}</strong>
          {row.document_type && (
            <div>
              <span className="muted">{enumLabel(row.document_type)}</span>
            </div>
          )}
          {row.preview && (
            <p className="muted" style={{ margin: 'var(--space-1) 0 0 0' }}>
              {row.preview}
            </p>
          )}
          {row.is_duplicate && (
            <div>
              <span className="muted">Duplicate of a ready document</span>
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'source_name',
      label: 'Source',
      render: (row) => row.source_name || '—',
    },
    {
      key: 'version',
      label: 'Version',
      render: (row) => (row.version != null ? `v${row.version}` : '—'),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => (
        <div>
          <StatusChip
            size="sm"
            status={row.status}
            tone={documentStatusTone(row.status)}
            label={documentStatusLabel(row.status)}
          />
          <div>
            <span className="muted">{searchabilityNote(row)}</span>
          </div>
        </div>
      ),
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
    liveStatus = 'Loading documents...'
  } else if (error) {
    liveStatus = 'Could not load documents.'
  }

  const emptyDescription =
    sourceId || statusFilter
      ? 'No documents match these filters.'
      : 'No documents have been stored for this business yet.'

  return (
    <div className="stack-sm">
      <div role="status" aria-live="polite" className="sr-only">
        {liveStatus}
      </div>

      <div
        style={{
          display: 'flex',
          gap: 'var(--space-3)',
          alignItems: 'flex-end',
          flexWrap: 'wrap',
          marginBottom: 'var(--space-3)',
        }}
      >
        <Field label="Source" htmlFor="kb-documents-source">
          <Select
            id="kb-documents-source"
            aria-label="Filter documents by source"
            value={sourceId}
            onChange={handleSourceChange}
            options={[
              { value: '', label: 'All sources' },
              ...sources.map((s) => ({
                value: String(s.id),
                label: s.name || 'Unnamed source',
              })),
            ]}
          />
        </Field>

        <Field label="Status" htmlFor="kb-documents-status">
          <Select
            id="kb-documents-status"
            aria-label="Filter documents by status"
            value={statusFilter}
            onChange={handleStatusChange}
            options={[
              { value: '', label: 'All statuses' },
              ...DOCUMENT_STATUS_ORDER.map((st) => ({
                value: st,
                label: documentStatusLabel(st),
              })),
            ]}
          />
        </Field>
      </div>

      <DataTable
        title="Documents"
        ariaLabel="Knowledge documents"
        showDensityToggle={false}
        isLoading={loading}
        columns={columns}
        rows={results}
        emptyTitle="No documents"
        emptyDescription={emptyDescription}
        pagination={{
          page,
          pageSize: DOCUMENTS_PAGE_LIMIT,
          total,
          onPageChange: setPage,
        }}
        error={error ? { detail: knowledgeErrorReason(error) } : null}
        onRetry={() => setRetryCount((c) => c + 1)}
      />
    </div>
  )
}
