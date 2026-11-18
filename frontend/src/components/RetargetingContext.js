'use client'

import { useState, useEffect, useCallback } from 'react'
import { Banner, Button, KpiTile, DataTable, EmptyState, UnavailableState, Skeleton } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import {
  retargetingPath,
  normalizeRetargeting,
  isEmptyRetargeting,
  truncationNote,
  describeRetargetingError,
} from '@/lib/customers/retargeting'
import { money, dateTime, duration } from '@/lib/format'

export default function RetargetingContext({ businessId, customerId, timezone, currency }) {
  const [loading, setLoading] = useState(true)
  const [errorText, setErrorText] = useState(null)
  const [view, setView] = useState(null)

  const loadSignals = useCallback(async () => {
    setLoading(true)
    setErrorText(null)
    try {
      const path = retargetingPath(businessId, customerId)
      const res = await clientApi(path)
      const normalized = normalizeRetargeting(res)
      if (!normalized) {
        setErrorText("Observed signals could not be read from the server's answer.")
      } else {
        setView(normalized)
      }
    } catch (err) {
      setErrorText(describeRetargetingError(err))
    } finally {
      setLoading(false)
    }
  }, [businessId, customerId])

  useEffect(() => {
    let cancelled = false
    async function fetchOnMount() {
      setLoading(true)
      setErrorText(null)
      try {
        const path = retargetingPath(businessId, customerId)
        const res = await clientApi(path)
        if (cancelled) return
        const normalized = normalizeRetargeting(res)
        if (!normalized) {
          setErrorText("Observed signals could not be read from the server's answer.")
        } else {
          setView(normalized)
        }
      } catch (err) {
        if (!cancelled) {
          setErrorText(describeRetargetingError(err))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchOnMount()
    return () => {
      cancelled = true
    }
  }, [businessId, customerId])

  if (loading) {
    return (
      <div className="stack" aria-live="polite">
        <p className="muted">Loading observed signals…</p>
        <div className="grid-kpi">
          <Skeleton variant="card" height="5rem" />
          <Skeleton variant="card" height="5rem" />
          <Skeleton variant="card" height="5rem" />
        </div>
      </div>
    )
  }

  if (errorText) {
    return (
      <div className="stack" aria-live="polite">
        <Banner variant="danger" title="Could not load observed signals">
          {errorText}
        </Banner>
        <div>
          <Button variant="secondary" size="sm" onClick={loadSignals}>
            Retry
          </Button>
        </div>
      </div>
    )
  }

  if (!view) {
    return null
  }

  const isEmpty = isEmptyRetargeting(view)

  return (
    <div className="stack">
      <Banner variant="info" title="Observed signals only">
        These are website sessions, events and campaign conversions already recorded for this customer. Bizora
        does not build an audience or a retargeting recommendation from them.
      </Banner>

      <div className="grid-kpi">
        <KpiTile title="Sessions" value={String(view.sessions.count)} subtext="Recorded for this customer" />
        <KpiTile title="Events" value={String(view.events.count)} subtext="Recorded for this customer" />
        <KpiTile
          title="Conversions"
          value={String(view.conversions.count)}
          subtext="Recorded for this customer"
        />
      </div>

      {isEmpty ? (
        <EmptyState
          title="No observed signals for this customer"
          description="No website sessions, events or campaign conversions are linked to this customer yet."
        />
      ) : (
        <div className="stack">
          {/* Sessions */}
          <div className="stack-sm">
            <h4 className="section-title">Website sessions</h4>
            <DataTable
              openInDrawer={false}
              showDensityToggle={false}
              ariaLabel="Website sessions"
              rows={view.sessions.rows}
              emptyTitle="No website sessions recorded"
              emptyDescription="No sessions recorded."
              columns={[
                {
                  key: 'startedAt',
                  label: 'Started',
                  render: (row) => dateTime(row.startedAt, timezone),
                },
                {
                  key: 'durationSeconds',
                  label: 'Duration',
                  render: (row) => duration(row.durationSeconds),
                },
                {
                  key: 'source',
                  label: 'Source',
                  render: (row) =>
                    row.trafficSource || row.trafficMedium
                      ? [row.trafficSource, row.trafficMedium].filter(Boolean).join(' / ')
                      : '—',
                },
                {
                  key: 'utmCampaign',
                  label: 'Campaign',
                  render: (row) => row.utmCampaign || '—',
                },
                {
                  key: 'deviceType',
                  label: 'Device',
                  render: (row) => row.deviceType || '—',
                },
                {
                  key: 'country',
                  label: 'Country',
                  render: (row) => row.country || '—',
                },
                {
                  key: 'isConverted',
                  label: 'Converted',
                  render: (row) => (row.isConverted ? 'Yes' : 'No'),
                },
                {
                  key: 'landingPath',
                  label: 'Landing page',
                  render: (row) =>
                    row.landingPath ? <span className="font-mono">{row.landingPath}</span> : '—',
                },
              ]}
            />
            {truncationNote(view.sessions, 'sessions') && (
              <p className="muted">{truncationNote(view.sessions, 'sessions')}</p>
            )}
          </div>

          {/* Events */}
          <div className="stack-sm">
            <h4 className="section-title">Website events</h4>
            <DataTable
              openInDrawer={false}
              showDensityToggle={false}
              ariaLabel="Website events"
              rows={view.events.rows}
              emptyTitle="No website events recorded"
              emptyDescription="No events recorded."
              columns={[
                {
                  key: 'occurredAt',
                  label: 'Time',
                  render: (row) => dateTime(row.occurredAt, timezone),
                },
                {
                  key: 'eventType',
                  label: 'Event',
                  render: (row) => <span className="font-mono">{row.eventType}</span>,
                },
                {
                  key: 'pagePath',
                  label: 'Page',
                  render: (row) => (row.pagePath ? <span className="font-mono">{row.pagePath}</span> : '—'),
                },
                {
                  key: 'eventValue',
                  label: 'Value',
                  render: (row) =>
                    row.eventValue !== null ? money(row.eventValue, row.currency || currency) : '—',
                },
                {
                  key: 'productId',
                  label: 'Product',
                  render: (row) => (row.productId ? `#${row.productId}` : '—'),
                },
                {
                  key: 'orderId',
                  label: 'Order',
                  render: (row) => (row.orderId ? `#${row.orderId}` : '—'),
                },
              ]}
            />
            {truncationNote(view.events, 'events') && (
              <p className="muted">{truncationNote(view.events, 'events')}</p>
            )}
          </div>

          {/* Conversions */}
          <div className="stack-sm">
            <h4 className="section-title">Campaign conversions</h4>
            <DataTable
              openInDrawer={false}
              showDensityToggle={false}
              ariaLabel="Campaign conversions"
              rows={view.conversions.rows}
              emptyTitle="No campaign conversions recorded"
              emptyDescription="No conversions recorded."
              columns={[
                {
                  key: 'convertedAt',
                  label: 'Converted at',
                  render: (row) => dateTime(row.convertedAt, timezone),
                },
                {
                  key: 'conversionType',
                  label: 'Type',
                  render: (row) => <span className="font-mono">{row.conversionType}</span>,
                },
                {
                  key: 'conversionValue',
                  label: 'Value',
                  render: (row) =>
                    row.conversionValue !== null ? money(row.conversionValue, row.currency || currency) : '—',
                },
                {
                  key: 'attributionType',
                  label: 'Attribution',
                  render: (row) => row.attributionType || '—',
                },
                {
                  key: 'campaignId',
                  label: 'Campaign',
                  render: (row) => (row.campaignId ? `#${row.campaignId}` : '—'),
                },
                {
                  key: 'orderId',
                  label: 'Order',
                  render: (row) => (row.orderId ? `#${row.orderId}` : '—'),
                },
              ]}
            />
            {truncationNote(view.conversions, 'conversions') && (
              <p className="muted">{truncationNote(view.conversions, 'conversions')}</p>
            )}
          </div>
        </div>
      )}

      <UnavailableState
        title="Audience recommendation not available"
        owner={view.audience.owner}
        reason={view.audience.reason || 'No audience or retargeting recommendation is computed.'}
      />
    </div>
  )
}
