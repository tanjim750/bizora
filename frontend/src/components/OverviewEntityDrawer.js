'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Drawer, Button, Banner, StatusChip, Skeleton } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime, enumLabel } from '@/lib/format'
import {
  overviewEntityTypeLabel,
  overviewEntityPath,
  normalizeOverviewEntity,
  overviewEntityError,
} from '@/lib/overview/entities'

export default function OverviewEntityDrawer({ businessId, entity, timezone, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)

  const closeRef = useRef(onClose)
  useEffect(() => {
    closeRef.current = onClose
  }, [onClose])
  const handleClose = useCallback(() => {
    if (closeRef.current) closeRef.current()
  }, [])

  const isOpen = entity != null
  const entityType = entity?.type
  const entityId = entity?.id

  useEffect(() => {
    if (!businessId || !entityType || !entityId) {
      setData(null)
      setError(null)
      setLoading(false)
      return
    }

    let active = true
    setData(null)
    setError(null)
    setLoading(true)

    try {
      const path = overviewEntityPath(businessId, entityType, entityId)
      clientApi(path)
        .then((res) => {
          if (!active) return
          const normalized = normalizeOverviewEntity(res)
          if (!normalized) {
            setError(
              'This record is not available in the overview. It may be of a type the overview does not cover, or it may have been removed.',
            )
          } else {
            setData(normalized)
          }
          setLoading(false)
        })
        .catch((err) => {
          if (!active) return
          setError(overviewEntityError(err))
          setLoading(false)
        })
    } catch (err) {
      if (active) {
        setError(err.message || 'The record could not be loaded.')
        setLoading(false)
      }
    }

    return () => {
      active = false
    }
  }, [businessId, entityType, entityId, reloadKey])

  const title = isOpen && entity?.type ? `${overviewEntityTypeLabel(entity.type)} details` : 'Record details'
  const subtitle =
    data?.label || (entity?.type && entity?.id ? `${overviewEntityTypeLabel(entity.type)} ${entity.id}` : '')

  const myNodeIds = new Set(data?.graph?.nodes?.map((n) => n.id) || [])
  const isRetryableError =
    error && !error.includes('This record is not available') && !error.includes('access to this business')

  return (
    <Drawer isOpen={isOpen} onClose={handleClose} title={title} subtitle={subtitle} width="min(100vw, 40rem)">
      <div className="stack" style={{ padding: 'var(--space-4)' }}>
        <div role="status" aria-live="polite" className="sr-only">
          {loading ? 'Loading record...' : error ? error : 'Record loaded'}
        </div>

        {loading && (
          <div className="stack-sm">
            <p className="muted">Loading record...</p>
            <Skeleton lines={3} />
          </div>
        )}

        {error && !loading && (
          <Banner variant="danger" title="The record could not be opened">
            <p>{error}</p>
            {isRetryableError && (
              <div style={{ marginTop: 'var(--space-2)' }}>
                <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
                  Try again
                </Button>
              </div>
            )}
          </Banner>
        )}

        {data && !loading && !error && (
          <div className="stack">
            <dl className="snapshot-list">
              <dt>Type</dt>
              <dd>{overviewEntityTypeLabel(data.type)}</dd>
              <dt>ID</dt>
              <dd className="font-mono">{data.id}</dd>
              <dt>Name</dt>
              <dd>{data.label || 'No name stored'}</dd>
              <dt>Domain</dt>
              <dd>{data.domain ? enumLabel(data.domain) : '—'}</dd>
              <dt>Status</dt>
              <dd>{data.status ? <StatusChip status={data.status} /> : '—'}</dd>
              <dt>Last updated</dt>
              <dd>{dateTime(data.updatedAt, timezone)}</dd>
              <dt>As of</dt>
              <dd>{dateTime(data.asOf, timezone)}</dd>
            </dl>

            <div className="stack-sm" style={{ marginTop: 'var(--space-3)' }}>
              <h4>Where it sits in the business graph</h4>
              {data.graph.nodes.length === 0 ? (
                <p className="muted">
                  This record has no node in the business graph. The graph may not cover it yet, or it may not
                  have been built.
                </p>
              ) : (
                <ul className="snapshot-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  {data.graph.nodes.map((node) => (
                    <li key={node.id} style={{ marginBottom: 'var(--space-1)' }}>
                      <span>
                        {node.label}
                        {node.entityType ? (
                          <span className="font-mono">
                            {' '}
                            {`[${node.entityType.toUpperCase()} #${node.entityId}]`}
                          </span>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="stack-sm" style={{ marginTop: 'var(--space-3)' }}>
              <h4>{`Relationships (${data.graph.edges.length})`}</h4>
              {data.graph.edges.length === 0 ? (
                <p className="muted">No stored relationships touch this record.</p>
              ) : (
                <ul className="snapshot-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  {data.graph.edges.map((edge) => {
                    const srcStr =
                      edge.sourceNodeId != null
                        ? `${edge.sourceNodeId}${myNodeIds.has(edge.sourceNodeId) ? ' (this record)' : ''}`
                        : '—'
                    const tgtStr =
                      edge.targetNodeId != null
                        ? `${edge.targetNodeId}${myNodeIds.has(edge.targetNodeId) ? ' (this record)' : ''}`
                        : '—'
                    return (
                      <li key={edge.id} style={{ marginBottom: 'var(--space-1)' }}>
                        <span className="font-mono">{edge.relationshipType}</span>:{' '}
                        <span>{`node ${srcStr} to node ${tgtStr}`}</span>
                      </li>
                    )
                  })}
                </ul>
              )}
              <p className="muted" style={{ marginTop: 'var(--space-2)' }}>
                Only this record's own nodes are listed. The other end of a relationship is shown as a node
                number because this view does not return its name.
              </p>
            </div>
          </div>
        )}
      </div>
    </Drawer>
  )
}
