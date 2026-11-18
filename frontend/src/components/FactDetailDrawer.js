'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Drawer, Button, Banner, StatusChip, Skeleton } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime } from '@/lib/format'
import { factDetailPath, normalizeFactDetail, factErrorMessage } from '@/lib/intelligence/factDetail'

export default function FactDetailDrawer({ businessId, factId, timezone, onClose }) {
  const isOpen = factId !== null && factId !== undefined
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [statusText, setStatusText] = useState('')

  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  const handleClose = useCallback(() => {
    if (onCloseRef.current) onCloseRef.current()
  }, [])

  useEffect(() => {
    if (!isOpen) {
      setDetail(null)
      setError(null)
      setLoading(false)
      return
    }

    let active = true
    setDetail(null)
    setError(null)
    setLoading(true)
    setStatusText('Loading fact details...')

    let path = null
    try {
      path = factDetailPath(businessId, factId)
    } catch (err) {
      setError(err.message || 'Invalid fact ID')
      setStatusText(err.message || 'Invalid fact ID')
      setLoading(false)
      return
    }

    async function fetchDetail() {
      try {
        const data = await clientApi(path)
        if (!active) return
        const norm = normalizeFactDetail(data)
        if (!norm) {
          setError('The server answered with something that is not a fact.')
          setStatusText('The server answered with something that is not a fact.')
        } else {
          setDetail(norm)
          setStatusText('Fact details loaded')
        }
      } catch (err) {
        if (!active) return
        const msg = factErrorMessage(err)
        setError(msg)
        setStatusText(msg)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    fetchDetail()
    return () => {
      active = false
    }
  }, [businessId, factId, isOpen, reloadKey])

  return (
    <Drawer
      isOpen={isOpen}
      onClose={handleClose}
      title="Fact detail"
      subtitle={`Fact #${factId}`}
      width="min(100vw, 40rem)"
    >
      <div role="status" aria-live="polite" className="sr-only">
        {statusText}
      </div>

      {loading ? (
        <div className="stack-sm">
          <p className="muted">Loading fact details...</p>
          <Skeleton variant="text" width="80%" />
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="90%" />
        </div>
      ) : error ? (
        <div className="stack-sm">
          <Banner variant="danger" title="The fact could not be opened">
            {error}
          </Banner>
          <div>
            <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
              Try again
            </Button>
          </div>
        </div>
      ) : detail ? (
        <div className="stack">
          <div className="stack-sm">
            <h4 className="section-title">Statement</h4>
            <p>{detail.statement}</p>
          </div>

          <dl className="snapshot-list">
            <div>
              <dt>Status</dt>
              <dd>{detail.status ? <StatusChip status={detail.status} size="sm" /> : '—'}</dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd className="font-mono">{detail.factType || '—'}</dd>
            </div>
            <div>
              <dt>Value</dt>
              <dd>
                {detail.value !== null
                  ? `${detail.value}${detail.valueUnit ? ` ${detail.valueUnit}` : ''}`
                  : '—'}
              </dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd>{detail.confidencePercent !== null ? `${detail.confidencePercent}%` : '—'}</dd>
            </div>
            <div>
              <dt>Rule key</dt>
              <dd className="font-mono">{detail.ruleKey || '—'}</dd>
            </div>
            <div>
              <dt>Detected</dt>
              <dd>{detail.detectedAt ? dateTime(detail.detectedAt, timezone) : '—'}</dd>
            </div>
            <div>
              <dt>Valid from</dt>
              <dd>{detail.validFrom ? dateTime(detail.validFrom, timezone) : 'Not set'}</dd>
            </div>
            <div>
              <dt>Valid until</dt>
              <dd>{detail.validTo ? dateTime(detail.validTo, timezone) : 'Not set'}</dd>
            </div>
          </dl>

          {!detail.validFrom && !detail.validTo && (
            <p className="muted">No validity window is stored for this fact.</p>
          )}

          <div className="stack-sm">
            <h4 className="section-title">Stored evidence</h4>
            {detail.evidence.entries.length === 0 ? (
              <p className="muted">No evidence notes are stored for this fact.</p>
            ) : (
              <div className="stack-sm">
                <dl className="snapshot-list">
                  {detail.evidence.entries.map((entry, idx) => (
                    <div key={idx}>
                      <dt className="font-mono">{entry.key}</dt>
                      <dd>{entry.text}</dd>
                    </div>
                  ))}
                </dl>
                {detail.evidence.total > detail.evidence.entries.length && (
                  <p className="muted">
                    {`Showing the first ${detail.evidence.entries.length} of ${detail.evidence.total} entries.`}
                  </p>
                )}
                <p className="muted" style={{ fontSize: 'var(--text-caption)' }}>
                  Entries are shown as plain text exactly as stored. Values under keys that look like
                  credentials are hidden.
                </p>
              </div>
            )}
          </div>

          <p className="muted">This view is read only.</p>
        </div>
      ) : null}
    </Drawer>
  )
}
