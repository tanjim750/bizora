'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Button, Banner, EmptyState, Skeleton, DataTable, Drawer } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime, enumLabel } from '@/lib/format'
import { graphErrorMessage } from '@/lib/intelligence/graphExplore'
import {
  SNAPSHOT_LIST_CAP,
  snapshotTypeLabel,
  snapshotListPath,
  snapshotDetailPath,
  normalizeSnapshotList,
  normalizeSnapshotDetail,
} from '@/lib/intelligence/graphSnapshots'

export default function GraphSnapshots({ businessId, timezone }) {
  const [snapshots, setSnapshots] = useState([])
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState(null)
  const [statusText, setStatusText] = useState('')

  const [openId, setOpenId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState(null)

  const handleCloseDrawer = useCallback(() => {
    setOpenId(null)
  }, [])

  const loadSnapshots = useCallback(async () => {
    setListLoading(true)
    setListError(null)
    setStatusText('Loading snapshots...')
    try {
      const data = await clientApi(snapshotListPath(businessId))
      const list = normalizeSnapshotList(data)
      setSnapshots(list)
      if (list.length === 0) {
        setStatusText('No snapshots yet')
      } else {
        setStatusText(`${list.length} snapshots`)
      }
    } catch (err) {
      const msg = graphErrorMessage(err)
      setListError(msg)
      setStatusText(msg)
    } finally {
      setListLoading(false)
    }
  }, [businessId])

  useEffect(() => {
    loadSnapshots()
  }, [loadSnapshots])

  const loadDetail = useCallback(
    async (id) => {
      setDetailLoading(true)
      setDetailError(null)
      try {
        const path = snapshotDetailPath(businessId, id)
        const data = await clientApi(path)
        const norm = normalizeSnapshotDetail(data)
        if (!norm) {
          setDetailError('This snapshot was not found for this business.')
        } else {
          setDetail(norm)
        }
      } catch (err) {
        setDetailError(
          graphErrorMessage(err, {
            notFound: 'This snapshot was not found for this business.',
          }),
        )
      } finally {
        setDetailLoading(false)
      }
    },
    [businessId],
  )

  useEffect(() => {
    if (!openId) {
      setDetail(null)
      setDetailError(null)
      setDetailLoading(false)
      return
    }
    let active = true
    async function fetchActive() {
      setDetailLoading(true)
      setDetailError(null)
      try {
        const path = snapshotDetailPath(businessId, openId)
        const data = await clientApi(path)
        if (!active) return
        const norm = normalizeSnapshotDetail(data)
        if (!norm) {
          setDetailError('This snapshot was not found for this business.')
        } else {
          setDetail(norm)
        }
      } catch (err) {
        if (!active) return
        setDetailError(
          graphErrorMessage(err, {
            notFound: 'This snapshot was not found for this business.',
          }),
        )
      } finally {
        if (active) {
          setDetailLoading(false)
        }
      }
    }
    fetchActive()
    return () => {
      active = false
    }
  }, [businessId, openId])

  return (
    <div className="stack">
      <div className="stack-sm">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h4 className="section-title">Saved snapshots</h4>
            <p className="muted">
              A snapshot is a stored copy of part of the graph. This screen only lists and opens them; it does
              not create or change any.
            </p>
          </div>
          <div>
            <Button variant="secondary" size="sm" onClick={loadSnapshots}>
              Refresh
            </Button>
          </div>
        </div>
      </div>

      <div role="status" aria-live="polite" className="sr-only">
        {statusText}
      </div>

      {listLoading ? (
        <div className="stack-sm">
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="80%" />
          <Skeleton variant="text" width="50%" />
        </div>
      ) : listError ? (
        <div className="stack-sm">
          <Banner variant="danger" title="Snapshots could not be loaded">
            {listError}
          </Banner>
          <div>
            <Button variant="secondary" size="sm" onClick={loadSnapshots}>
              Try again
            </Button>
          </div>
        </div>
      ) : snapshots.length === 0 ? (
        <EmptyState
          title="No snapshots yet"
          description="No snapshot has been saved for this business. Owners and managers can create snapshots through the API."
        />
      ) : (
        <div className="stack-sm">
          <DataTable
            openInDrawer={false}
            showDensityToggle={false}
            ariaLabel="Saved graph snapshots"
            rows={snapshots.slice(0, SNAPSHOT_LIST_CAP)}
            columns={[
              {
                key: 'name',
                label: 'Name',
                render: (r) => <strong>{r.name}</strong>,
              },
              {
                key: 'type',
                label: 'Type',
                render: (r) => snapshotTypeLabel(r.snapshotType),
              },
              {
                key: 'entities',
                label: 'Entities',
                render: (r) => <span className="font-mono">{r.nodeCount !== null ? r.nodeCount : '—'}</span>,
              },
              {
                key: 'relationships',
                label: 'Relationships',
                render: (r) => <span className="font-mono">{r.edgeCount !== null ? r.edgeCount : '—'}</span>,
              },
              {
                key: 'created',
                label: 'Created',
                render: (r) => dateTime(r.generatedAt, timezone),
              },
              {
                key: 'action',
                label: '',
                render: (r) => (
                  <Button size="sm" aria-label={`Open snapshot ${r.name}`} onClick={() => setOpenId(r.id)}>
                    Open
                  </Button>
                ),
              },
            ]}
          />
          {snapshots.length > SNAPSHOT_LIST_CAP && (
            <p className="muted">{`Showing the newest 50 of ${snapshots.length} snapshots.`}</p>
          )}
        </div>
      )}

      <Drawer
        isOpen={openId !== null}
        title={detail?.name || 'Snapshot'}
        subtitle={snapshotTypeLabel(detail?.snapshotType)}
        width="min(100vw, 48rem)"
        onClose={handleCloseDrawer}
      >
        {detailLoading ? (
          <p className="muted">Loading snapshot...</p>
        ) : detailError ? (
          <div className="stack-sm">
            <Banner variant="danger" title="The snapshot could not be opened">
              {detailError}
            </Banner>
            {openId && (
              <div>
                <Button variant="secondary" size="sm" onClick={() => loadDetail(openId)}>
                  Try again
                </Button>
              </div>
            )}
          </div>
        ) : detail ? (
          <div className="stack">
            <Banner variant="info">
              {`This is a stored copy taken on ${dateTime(detail.generatedAt, timezone)}. It does not change when the live graph changes, so it can differ from what the graph shows now.`}
            </Banner>

            <dl className="snapshot-list">
              <div>
                <dt>Type</dt>
                <dd>{snapshotTypeLabel(detail.snapshotType)}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{dateTime(detail.generatedAt, timezone)}</dd>
              </div>
              <div>
                <dt>Entities (stored count)</dt>
                <dd className="font-mono">
                  {detail.storedNodeCount !== null ? detail.storedNodeCount : '—'}
                </dd>
              </div>
              <div>
                <dt>Relationships (stored count)</dt>
                <dd className="font-mono">
                  {detail.storedEdgeCount !== null ? detail.storedEdgeCount : '—'}
                </dd>
              </div>
              <div>
                <dt>Timeline events</dt>
                <dd className="font-mono">{detail.timelineCount}</dd>
              </div>
            </dl>

            {!detail.countsMatch && (
              <Banner variant="warning">
                {`The stored counts (${detail.storedNodeCount} entities, ${detail.storedEdgeCount} relationships) differ from what this answer contains (${detail.loadedNodeCount} entities, ${detail.loadedEdgeCount} relationships).`}
              </Banner>
            )}

            <div className="stack-sm">
              <h4 className="section-title">Filters used when it was saved</h4>
              {detail.filters.length === 0 ? (
                <p className="muted">No filters were applied.</p>
              ) : (
                <dl className="snapshot-list">
                  {detail.filters.map((f) => (
                    <div key={f.key}>
                      <dt>{f.label}</dt>
                      <dd>{f.value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>

            {detail.summary.length > 0 && (
              <div className="stack-sm">
                <h4 className="section-title">Summary stored with the snapshot</h4>
                <dl className="snapshot-list">
                  {detail.summary.map((s, idx) => (
                    <div key={idx}>
                      <dt>{s.label}</dt>
                      <dd>{s.value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}

            <div className="stack-sm">
              <h4 className="section-title">{`Entities (${detail.loadedNodeCount})`}</h4>
              <DataTable
                openInDrawer={false}
                showDensityToggle={false}
                ariaLabel="Snapshot entities"
                rows={detail.nodes}
                columns={[
                  {
                    key: 'name',
                    label: 'Name',
                    render: (r) => <strong>{r.label}</strong>,
                  },
                  {
                    key: 'type',
                    label: 'Type',
                    render: (r) => enumLabel(r.entityType),
                  },
                  {
                    key: 'id',
                    label: 'ID',
                    render: (r) => <span className="font-mono">{`#${r.entityId}`}</span>,
                  },
                ]}
              />
              {detail.nodesCapped && (
                <p className="muted">{`Showing the first 100 of ${detail.loadedNodeCount}.`}</p>
              )}
            </div>

            <div className="stack-sm">
              <h4 className="section-title">{`Relationships (${detail.loadedEdgeCount})`}</h4>
              <DataTable
                openInDrawer={false}
                showDensityToggle={false}
                ariaLabel="Snapshot relationships"
                rows={detail.edges}
                columns={[
                  {
                    key: 'from',
                    label: 'From',
                    render: (r) => r.sourceLabel || '—',
                  },
                  {
                    key: 'relationship',
                    label: 'Relationship',
                    render: (r) => <span className="font-mono">{r.relationshipType}</span>,
                  },
                  {
                    key: 'to',
                    label: 'To',
                    render: (r) => r.targetLabel || '—',
                  },
                  {
                    key: 'confidence',
                    label: 'Confidence',
                    render: (r) => (r.confidencePercent !== null ? `${r.confidencePercent}%` : '—'),
                  },
                ]}
              />
              {detail.edgesCapped && (
                <p className="muted">{`Showing the first 100 of ${detail.loadedEdgeCount}.`}</p>
              )}
            </div>

            {detail.timelineCount > 0 && (
              <div className="stack-sm">
                <h4 className="section-title">{`Timeline (${detail.timelineCount})`}</h4>
                <ol className="stack-sm" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  {detail.timeline.map((t, idx) => (
                    <li
                      key={idx}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 'var(--space-1)',
                      }}
                    >
                      <div>
                        <strong>{t.stage || 'Event'}:</strong> {t.label}{' '}
                        <span className="font-mono">{`[${t.entityType} #${t.entityId}]`}</span>
                      </div>
                      <div className="muted">{dateTime(t.timestamp, timezone)}</div>
                    </li>
                  ))}
                </ol>
                {detail.timelineCapped && (
                  <p className="muted">{`Showing the first 20 of ${detail.timelineCount}.`}</p>
                )}
              </div>
            )}
          </div>
        ) : null}
      </Drawer>
    </div>
  )
}
