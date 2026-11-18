'use client'

import { useState, useEffect, useCallback } from 'react'
import { Banner, Button, DataTable, Drawer, EmptyState, Pagination, StatusChip } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime } from '@/lib/format'
import { changesPath } from '@/lib/configuration/paths'
import { normalizePage, actorLabel } from '@/lib/configuration/normalize'
import {
  kindLabel,
  normalizeChange,
  itemLabel,
  normalizeRevision,
  subjectFromChange,
  historyPathFor,
  formatDiffValue,
  withDiffs,
} from '@/lib/configuration/history'

export default function ConfigHistory({ businessId, timezone }) {
  const [page, setPage] = useState(1)
  const [feed, setFeed] = useState({ results: [], count: 0 })
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)

  const [drawerSubject, setDrawerSubject] = useState(null)
  const [drawerPage, setDrawerPage] = useState(1)
  const [drawerRevs, setDrawerRevs] = useState([])
  const [drawerCount, setDrawerCount] = useState(0)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [drawerError, setDrawerError] = useState(null)
  const [drawerNotFound, setDrawerNotFound] = useState(false)

  const loadFeed = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const data = await clientApi(changesPath(businessId, { page, pageSize: 25 }))
      const norm = normalizePage(data, normalizeChange)
      setFeed(norm)
    } catch (err) {
      setLoadError(err)
    } finally {
      setLoading(false)
    }
  }, [businessId, page])

  useEffect(() => {
    loadFeed()
  }, [loadFeed])

  const loadHistory = useCallback(async () => {
    if (!drawerSubject) return
    setDrawerLoading(true)
    setDrawerError(null)
    setDrawerNotFound(false)
    try {
      const path = historyPathFor(businessId, drawerSubject, {
        page: drawerPage,
        pageSize: 25,
      })
      const data = await clientApi(path)
      const norm = normalizePage(data, normalizeRevision)
      setDrawerCount(norm.count)
      setDrawerRevs(withDiffs(norm.results))
    } catch (err) {
      if (err?.status === 404) {
        setDrawerNotFound(true)
      } else {
        setDrawerError(err?.detail || err?.message || 'Could not load versions')
      }
    } finally {
      setDrawerLoading(false)
    }
  }, [businessId, drawerSubject, drawerPage])

  useEffect(() => {
    if (drawerSubject) {
      loadHistory()
    }
  }, [drawerSubject, drawerPage, loadHistory])

  const handleOpenVersions = (row) => {
    const subj = subjectFromChange(row)
    if (!subj) return
    setDrawerSubject({
      ...subj,
      kindLabel: kindLabel(row.section),
      itemLabel: itemLabel(row),
    })
    setDrawerPage(1)
  }

  const columns = [
    {
      key: 'created_at',
      label: 'When',
      render: (row) => dateTime(row.created_at, timezone),
    },
    {
      key: 'section',
      label: 'What',
      render: (row) => kindLabel(row.section),
    },
    {
      key: 'item',
      label: 'Item',
      render: (row) => <span className="font-mono">{itemLabel(row)}</span>,
    },
    {
      key: 'version',
      label: 'Version',
      align: 'right',
      render: (row) => <span className="font-mono">v{row.version}</span>,
    },
    {
      key: 'actor',
      label: 'Who',
      render: (row) => actorLabel(row.actor_id),
    },
    {
      key: 'actions',
      label: '',
      align: 'right',
      render: (row) => {
        const canView = subjectFromChange(row) !== null
        if (!canView) return null
        return (
          <Button size="sm" variant="secondary" onClick={() => handleOpenVersions(row)}>
            View versions
          </Button>
        )
      },
    },
  ]

  return (
    <div className="stack" style={{ gap: 'var(--space-4, 16px)' }}>
      <p className="text-caption text-secondary">
        Every saved change creates a new version. Each row is a change notice recorded when a setting was
        saved; it does not say that other parts of Bizora have applied the change.{' '}
        {'Versions cannot be restored from here'}: to go back, edit the values and save a new version.
      </p>

      <div aria-live="polite" className="sr-only">
        {loading
          ? 'Loading configuration changes…'
          : loadError
            ? loadError.detail || 'Could not load configuration changes'
            : ''}
      </div>

      <DataTable
        ariaLabel="Configuration changes"
        showDensityToggle={false}
        openInDrawer={false}
        isLoading={loading}
        error={loadError}
        onRetry={loadFeed}
        emptyTitle="No configuration changes yet"
        emptyDescription="Saved changes will appear here."
        columns={columns}
        rows={feed.results}
        pagination={{
          page,
          pageSize: 25,
          total: feed.count,
          onPageChange: setPage,
        }}
      />

      {drawerSubject && (
        <Drawer
          isOpen
          onClose={() => setDrawerSubject(null)}
          title={`Versions: ${drawerSubject.kindLabel} ${drawerSubject.itemLabel}`}
          width="36rem"
        >
          <div className="stack" style={{ gap: 'var(--space-4, 16px)' }}>
            {drawerLoading && <p className="text-caption text-secondary">Loading versions…</p>}

            {drawerNotFound && (
              <EmptyState
                title="No saved versions yet"
                description="This item has not been saved through configuration yet."
              />
            )}

            {drawerError && (
              <Banner variant="danger" title="Could not load versions">
                {drawerError}
              </Banner>
            )}

            {!drawerLoading && !drawerNotFound && !drawerError && (
              <>
                <ol
                  className="stack"
                  style={{
                    gap: 'var(--space-4, 16px)',
                    listStyle: 'none',
                    padding: 0,
                    margin: 0,
                  }}
                >
                  {drawerRevs.map((rev) => (
                    <li key={rev.version} className="journey-card stack-sm">
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: 'var(--space-2)',
                        }}
                      >
                        <span className="font-semibold text-body">Version {rev.version}</span>
                        {rev.status && <StatusChip status={rev.status} label={rev.status} size="sm" />}
                      </div>

                      <p className="text-caption text-secondary">
                        {dateTime(rev.created_at, timezone)} · {actorLabel(rev.actor_id)}
                      </p>

                      {rev.reason && <p className="text-caption text-secondary">Reason: {rev.reason}</p>}

                      {rev.note ? (
                        <p className="text-caption text-secondary">{rev.note}</p>
                      ) : (
                        <ul
                          className="stack"
                          style={{
                            gap: '4px',
                            margin: 0,
                            paddingLeft: 'var(--space-4)',
                          }}
                        >
                          {rev.diff?.map((d) => (
                            <li key={d.path} className="font-mono text-caption">
                              {d.path}: {formatDiffValue(d.before)} → {formatDiffValue(d.after)}
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ol>

                {drawerCount > 25 && (
                  <Pagination
                    page={drawerPage}
                    pageSize={25}
                    total={drawerCount}
                    onPageChange={setDrawerPage}
                  />
                )}
              </>
            )}
          </div>
        </Drawer>
      )}
    </div>
  )
}
