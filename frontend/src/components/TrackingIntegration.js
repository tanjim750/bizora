'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  summaryPath,
  attemptsPath,
  normalizeSummary,
  normalizeAttempts,
  providerLabel,
  modeLabel,
  attemptTone,
} from '@/lib/tracking/api'
import { clientApi } from '@/lib/clientApi'
import {
  Banner,
  Button,
  DataTable,
  EmptyState,
  Field,
  KpiTile,
  Select,
  StatusChip,
  UnavailableState,
  Skeleton,
} from '@/components/ui'
import { dateTime } from '../lib/format/index.js'
import { RefreshCw, Radio, CheckCircle2, XCircle, Info, Activity } from 'lucide-react'

export default function TrackingIntegration({ businessId, role }) {
  const [summary, setSummary] = useState(null)
  const [attempts, setAttempts] = useState({ total: 0, limit: 25, offset: 0, results: [] })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [liveAnnouncement, setLiveAnnouncement] = useState('')

  // Filters
  const [connectionFilter, setConnectionFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [modeFilter, setModeFilter] = useState('ALL')
  const [offset, setOffset] = useState(0)
  const limit = 25

  const loadData = useCallback(async () => {
    if (!businessId) return
    setIsLoading(true)
    setError(null)
    setLiveAnnouncement('Loading tracking integration data…')

    try {
      const summaryUrl = summaryPath(businessId)
      const summaryRes = await clientApi(summaryUrl)
      const normSummary = normalizeSummary(summaryRes)
      setSummary(normSummary)

      const filterParams = { limit, offset }
      if (connectionFilter !== 'ALL') {
        filterParams.connection = Number(connectionFilter)
      }
      if (statusFilter !== 'ALL') {
        filterParams.status = statusFilter
      }
      if (modeFilter !== 'ALL') {
        filterParams.mode = modeFilter
      }

      const attemptsUrl = attemptsPath(businessId, filterParams)
      const attemptsRes = await clientApi(attemptsUrl)
      const normAttempts = normalizeAttempts(attemptsRes)
      setAttempts(normAttempts)
      setLiveAnnouncement('Tracking data loaded successfully.')
    } catch (err) {
      setError(err)
      setLiveAnnouncement(`Error loading tracking data: ${err.detail || err.message}`)
    } finally {
      setIsLoading(false)
    }
  }, [businessId, connectionFilter, statusFilter, modeFilter, offset])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleConnectionChange = (e) => {
    setConnectionFilter(e.target.value)
    setOffset(0)
  }

  const handleStatusChange = (e) => {
    setStatusFilter(e.target.value)
    setOffset(0)
  }

  const handleModeChange = (e) => {
    setModeFilter(e.target.value)
    setOffset(0)
  }

  const handlePageChange = (newPage) => {
    setOffset((newPage - 1) * limit)
  }

  const isManager = role === 'OWNER' || role === 'MANAGER'

  if (error && !summary) {
    return (
      <div className="stack section-gap">
        <UnavailableState
          owner="Integrations"
          reason={error.detail || error.message || 'Failed to load tracking integration data.'}
          action={
            <Button variant="secondary" onClick={loadData} icon={RefreshCw}>
              Retry
            </Button>
          }
        />
      </div>
    )
  }

  const connections = summary?.connections || []
  const currentPage = Math.floor(offset / limit) + 1

  const columns = [
    {
      key: 'created_at',
      label: 'Time',
      render: (row) => (row.created_at ? dateTime(row.created_at) : '—'),
    },
    {
      key: 'connection_name',
      label: 'Connection',
      render: (row) => `${providerLabel(row.provider)} — ${row.connection_name || row.connection_id}`,
    },
    {
      key: 'event_type',
      label: 'Event',
      render: (row) => <span className="font-mono text-body font-semibold">{row.event_type || '—'}</span>,
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusChip status={attemptTone(row)} label={row.status} size="sm" />,
    },
    {
      key: 'mode',
      label: 'Mode',
      render: (row) => modeLabel(row.mode, row.sent),
    },
    {
      key: 'http_status',
      label: 'HTTP Status',
      render: (row) => (row.http_status ? <span className="font-mono">{row.http_status}</span> : '—'),
    },
    {
      key: 'note',
      label: 'Note',
      render: (row) => {
        const note = row.error || row.reason
        return note ? <code className="font-mono text-caption">{note}</code> : '—'
      },
    },
  ]

  return (
    <div className="stack section-gap">
      <div aria-live="polite" className="sr-only">
        {liveAnnouncement}
      </div>

      {/* Top calm informational banner */}
      <Banner variant="info">
        <span>
          Tracking events are built and stored here. Nothing is sent to Meta, TikTok or Google until a
          connection is live (not a mock, tracking enabled, credentials available). Sending is run by the
          server command send_tracking_events; this screen only shows what happened.
        </span>
      </Banner>

      {/* Header and Refresh Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--space-3)',
        }}
      >
        <div>
          <h3 className="text-section font-semibold">Server-Side Tracking Outbox</h3>
          <p className="text-secondary text-caption">
            Conversational and behavioral telemetry conversion pipeline for Meta, TikTok, and Google
            Analytics.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {!isManager && (
            <span className="text-caption text-secondary">Only owners and managers can change settings</span>
          )}
          <Button variant="secondary" onClick={loadData} disabled={isLoading} icon={RefreshCw}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Connection Cards Section */}
      <section aria-labelledby="tracking-connections-heading" className="stack-sm">
        <h4 id="tracking-connections-heading" className="text-body font-semibold">
          Tracking Connections ({connections.length})
        </h4>

        {isLoading && !summary ? (
          <div className="grid-2">
            <Skeleton style={{ height: '160px', borderRadius: 'var(--radius-panel)' }} />
            <Skeleton style={{ height: '160px', borderRadius: 'var(--radius-panel)' }} />
          </div>
        ) : connections.length === 0 ? (
          <EmptyState
            title="No tracking connection yet"
            description="Add a Meta, TikTok or Google Analytics connection on the Connections tab."
          />
        ) : (
          <div className="grid-2">
            {connections.map((c) => (
              <div
                key={c.id}
                className="surface card-padding stack-sm"
                style={{
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-panel)',
                  background: 'var(--bg-surface)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span className="text-caption text-secondary font-mono">{providerLabel(c.provider)}</span>
                    <h5 className="text-card font-semibold">{c.name}</h5>
                  </div>
                  <StatusChip
                    status={c.mode === 'LIVE' ? 'ACTIVE' : 'INACTIVE'}
                    label={c.mode === 'LIVE' ? 'Live' : 'Prepared, not sent'}
                    size="sm"
                  />
                </div>

                {/* Status indicator badges */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                  <StatusChip
                    status={c.settings.enabled ? 'ACTIVE' : 'INACTIVE'}
                    label={c.settings.enabled ? 'Tracking enabled' : 'Tracking disabled'}
                    size="sm"
                  />
                  <StatusChip
                    status={c.settings.test_mode ? 'WARNING' : 'INACTIVE'}
                    label={c.settings.test_mode ? 'Test mode on' : 'Test mode off'}
                    size="sm"
                  />
                  <StatusChip
                    status={c.is_mock ? 'WARNING' : 'ACTIVE'}
                    label={c.is_mock ? 'Mock connection yes' : 'Mock connection no'}
                    size="sm"
                  />
                  <StatusChip
                    status={c.credentials_available ? 'ACTIVE' : 'DANGER'}
                    label={c.credentials_available ? 'Credentials available yes' : 'Credentials available no'}
                    size="sm"
                  />
                </div>

                {/* KPI summary tiles */}
                <div className="grid-kpi mt-2">
                  <KpiTile title="Total Events" value={String(c.counts.total)} />
                  <KpiTile title="Prepared Events" value={String(c.counts.prepared)} />
                  <KpiTile title="Sent and Accepted" value={String(c.counts.live_succeeded)} />
                  <KpiTile title="Failed Attempts" value={String(c.counts.failed)} />
                  <KpiTile title="Not Supported" value={String(c.counts.unsupported)} />
                </div>

                <div className="text-caption text-secondary stack-xs mt-2">
                  <div>
                    Last attempt:{' '}
                    <span className="font-mono">{c.last_attempt_at ? dateTime(c.last_attempt_at) : '—'}</span>
                  </div>
                  <div>
                    Allowed events:{' '}
                    <span className="font-mono">
                      {c.settings.events && c.settings.events.length > 0
                        ? c.settings.events.join(', ')
                        : 'All supported events'}
                    </span>
                  </div>
                  <div className="font-semibold text-primary">Personal identifiers are never sent.</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Attempts Activity Log */}
      <section aria-labelledby="tracking-attempts-heading" className="stack-sm">
        <h4 id="tracking-attempts-heading" className="text-body font-semibold">
          Dispatch Activity Log
        </h4>

        {/* Filter Controls */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 'var(--space-3)',
            alignItems: 'flex-end',
            marginBottom: 'var(--space-2)',
          }}
        >
          <Field label="Filter Connection" htmlFor="tracking-conn-filter">
            <Select
              id="tracking-conn-filter"
              aria-label="Filter Connection"
              value={connectionFilter}
              onChange={handleConnectionChange}
            >
              <option value="ALL">All connections</option>
              {connections.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {providerLabel(c.provider)} — {c.name}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Filter Status" htmlFor="tracking-status-filter">
            <Select
              id="tracking-status-filter"
              aria-label="Filter Status"
              value={statusFilter}
              onChange={handleStatusChange}
            >
              <option value="ALL">All statuses</option>
              <option value="SUCCEEDED">SUCCEEDED</option>
              <option value="RUNNING">RUNNING</option>
              <option value="FAILED">FAILED</option>
              <option value="UNSUPPORTED">UNSUPPORTED</option>
            </Select>
          </Field>

          <Field label="Filter Mode" htmlFor="tracking-mode-filter">
            <Select
              id="tracking-mode-filter"
              aria-label="Filter Mode"
              value={modeFilter}
              onChange={handleModeChange}
            >
              <option value="ALL">All modes</option>
              <option value="PREPARED">PREPARED</option>
              <option value="LIVE">LIVE</option>
            </Select>
          </Field>
        </div>

        {/* Attempts Table */}
        <DataTable
          columns={columns}
          rows={attempts.results}
          isLoading={isLoading}
          emptyTitle="No tracking events recorded yet"
          emptyDescription="Events will appear here as web and storefront interactions are captured."
          pagination={{
            page: currentPage,
            pageSize: limit,
            total: attempts.total,
            onPageChange: handlePageChange,
          }}
        />
      </section>
    </div>
  )
}
