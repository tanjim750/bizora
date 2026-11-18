'use client'

import { useState, useEffect } from 'react'
import { Button, Banner, DataTable, Field, Select, StatusChip } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime, enumLabel } from '@/lib/format'
import PayloadDiagnosticDrawer from './PayloadDiagnosticDrawer'
import {
  RECORD_PAGE_SIZE,
  FAILED_RECORD_STATUSES,
  WEBHOOK_STATUSES,
  recordListPath,
  normalizeRecordPage,
  canOpenPayload,
  recordListError,
} from '@/lib/observability/records'

function RecordListShared({
  title,
  subtitle,
  kind,
  statuses,
  columns,
  emptyTitle,
  emptyDescription,
  businessId,
  role,
  timezone,
}) {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [payloadId, setPayloadId] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    try {
      const path = recordListPath(businessId, kind, {
        page,
        status: status || undefined,
      })
      clientApi(path)
        .then((data) => {
          if (!active) return
          const normalized = normalizeRecordPage(data, kind)
          setRows(normalized.rows)
          setTotal(normalized.total)
          setLoading(false)
        })
        .catch((err) => {
          if (!active) return
          setError(recordListError(err))
          setLoading(false)
        })
    } catch (err) {
      if (active) {
        setError(err.message || 'The list could not be loaded.')
        setLoading(false)
      }
    }
    return () => {
      active = false
    }
  }, [businessId, kind, page, status, reloadKey])

  const tableColumns = [
    ...columns,
    {
      key: 'payload',
      label: 'Payload',
      render: (row) => {
        if (canOpenPayload(row, role)) {
          return (
            <Button
              variant="secondary"
              size="sm"
              aria-label={`View diagnostic payload ${row.payloadId} for record ${row.id}`}
              onClick={() => setPayloadId(row.payloadId)}
            >
              View payload
            </Button>
          )
        }
        if (row.payloadId != null) {
          return <span className="muted">Managers only</span>
        }
        return <span className="muted">No payload stored</span>
      },
    },
  ]

  return (
    <div className="stack">
      <div className="section-header">
        <h4>{title}</h4>
        <p className="muted">{subtitle}</p>
      </div>

      <div
        style={{
          display: 'flex',
          gap: 'var(--space-3)',
          alignItems: 'flex-end',
          marginBottom: 'var(--space-4)',
        }}
      >
        <Field label="Status" htmlFor={`${kind}-status-filter`}>
          <Select
            id={`${kind}-status-filter`}
            aria-label="Status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value)
              setPage(1)
            }}
          >
            <option value="">All statuses</option>
            {statuses.map((st) => (
              <option key={st} value={st}>
                {enumLabel(st)}
              </option>
            ))}
          </Select>
        </Field>
        <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
          Refresh
        </Button>
      </div>

      {error && (
        <Banner variant="danger" title="The list could not be loaded" className="mb-4">
          <p>{error}</p>
          <div style={{ marginTop: 'var(--space-2)' }}>
            <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
              Try again
            </Button>
          </div>
        </Banner>
      )}

      <div role="status" aria-live="polite" className="sr-only">
        {loading ? 'Loading...' : error ? error : `${total} records`}
      </div>

      <DataTable
        columns={tableColumns}
        rows={rows}
        isLoading={loading}
        emptyTitle={emptyTitle}
        emptyDescription={emptyDescription}
        openInDrawer={false}
        showDensityToggle={false}
        ariaLabel={title}
        pagination={{
          page,
          pageSize: RECORD_PAGE_SIZE,
          total,
          onPageChange: setPage,
        }}
      />

      <p className="muted" style={{ marginTop: 'var(--space-3)' }}>
        Opening a payload is limited to owners and managers and is recorded in the audit log.
      </p>

      <PayloadDiagnosticDrawer
        businessId={businessId}
        payloadId={payloadId}
        role={role}
        timezone={timezone}
        onClose={() => setPayloadId(null)}
      />
    </div>
  )
}

export function FailedRecordsList({ businessId, role, timezone }) {
  const columns = [
    {
      key: 'lastSeenAt',
      label: 'Last seen',
      render: (row) => dateTime(row.lastSeenAt, timezone) || '—',
    },
    {
      key: 'record',
      label: 'Record',
      render: (row) => (
        <span>
          {row.entityType || '—'} {row.externalId ? <span className="font-mono">{row.externalId}</span> : '—'}
        </span>
      ),
    },
    {
      key: 'stage',
      label: 'Stage',
      render: (row) => enumLabel(row.stage) || '—',
    },
    {
      key: 'code',
      label: 'Code',
      render: (row) => (row.code ? <span className="font-mono">{row.code}</span> : '—'),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusChip status={row.status} />,
    },
    {
      key: 'message',
      label: 'Message',
      render: (row) => <span>{row.message || '—'}</span>,
    },
  ]

  return (
    <RecordListShared
      title="Failed records"
      subtitle="Records that could not be ingested, newest first."
      kind="failed-records"
      statuses={FAILED_RECORD_STATUSES}
      columns={columns}
      emptyTitle="No failed records"
      emptyDescription="The server lists no failed ingestion records for this filter."
      businessId={businessId}
      role={role}
      timezone={timezone}
    />
  )
}

export function WebhooksList({ businessId, role, timezone }) {
  const columns = [
    {
      key: 'receivedAt',
      label: 'Received',
      render: (row) => dateTime(row.receivedAt, timezone) || '—',
    },
    {
      key: 'event',
      label: 'Event',
      render: (row) => (
        <span>
          {row.eventType || '—'} {row.eventId ? <span className="font-mono">{row.eventId}</span> : '—'}
        </span>
      ),
    },
    {
      key: 'entity',
      label: 'Entity',
      render: (row) => row.entityType || '—',
    },
    {
      key: 'validation',
      label: 'Validation',
      render: (row) => (
        <StatusChip
          status={row.validation}
          tone={row.validation === 'VALID' ? 'success' : row.validation === 'INVALID' ? 'danger' : 'neutral'}
        />
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusChip status={row.status} />,
    },
    {
      key: 'deliveries',
      label: 'Deliveries',
      render: (row) =>
        row.deliveryCount != null ? <span className="font-mono">{row.deliveryCount}</span> : '—',
    },
  ]

  return (
    <RecordListShared
      title="Inbound webhooks"
      subtitle="Webhook deliveries received from providers, newest first."
      kind="webhooks"
      statuses={WEBHOOK_STATUSES}
      columns={columns}
      emptyTitle="No webhook deliveries"
      emptyDescription="The server lists no inbound webhook deliveries for this filter."
      businessId={businessId}
      role={role}
      timezone={timezone}
    />
  )
}
