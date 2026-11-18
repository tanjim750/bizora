'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Drawer, Button, Banner, Skeleton } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime } from '@/lib/format'
import {
  canViewPayloads,
  payloadDiagnosticPath,
  normalizePayloadDiagnostic,
  describePayload,
  markerSummary,
  PAYLOAD_NOTICES,
  payloadErrorMessage,
} from '@/lib/observability/payloads'

export default function PayloadDiagnosticDrawer({ businessId, payloadId, role, timezone, onClose }) {
  const isOpen = payloadId !== null && payloadId !== undefined
  const isAllowed = canViewPayloads(role)

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [statusText, setStatusText] = useState('')

  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  const handleClose = useCallback(() => {
    if (onCloseRef.current) onCloseRef.current()
  }, [])

  useEffect(() => {
    if (!isOpen || !isAllowed) {
      setData(null)
      setRevealed(false)
      setError(null)
      setLoading(false)
      return
    }

    let active = true
    setData(null)
    setRevealed(false)
    setError(null)
    setLoading(true)
    setStatusText('Loading diagnostic payload...')

    let path = null
    try {
      path = payloadDiagnosticPath(businessId, payloadId)
    } catch (err) {
      setError(err.message || 'Invalid payload ID')
      setStatusText(err.message || 'Invalid payload ID')
      setLoading(false)
      return
    }

    async function fetchPayload() {
      try {
        const res = await clientApi(path)
        if (!active) return
        const norm = normalizePayloadDiagnostic(res)
        if (!norm) {
          setError('The server answered with something that is not a payload.')
          setStatusText('The server answered with something that is not a payload.')
        } else {
          setData(norm)
          setStatusText('Payload loaded. Content is hidden until you choose to show it.')
        }
      } catch (err) {
        if (!active) return
        const msg = payloadErrorMessage(err)
        setError(msg)
        setStatusText(msg)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    fetchPayload()
    return () => {
      active = false
      setData(null)
      setRevealed(false)
    }
  }, [businessId, payloadId, isAllowed, isOpen, reloadKey])

  const described = data ? describePayload(data.body) : null
  const summaryText = described ? markerSummary(described.markers) : ''

  return (
    <Drawer
      isOpen={isOpen}
      onClose={handleClose}
      title="Diagnostic payload"
      subtitle={`Payload #${payloadId}`}
      width="min(100vw, 44rem)"
    >
      <div role="status" aria-live="polite" className="sr-only">
        {statusText}
      </div>

      {!isAllowed ? (
        <Banner variant="warning">Only owners and managers can open diagnostic payloads.</Banner>
      ) : loading ? (
        <div className="stack-sm">
          <p className="muted">Loading diagnostic payload...</p>
          <Skeleton variant="text" width="80%" />
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="90%" />
        </div>
      ) : error ? (
        <div className="stack-sm">
          <Banner variant="danger" title="The payload could not be opened">
            {error}
          </Banner>
          <div>
            <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
              Try again
            </Button>
          </div>
        </div>
      ) : data && described ? (
        <div className="stack">
          <Banner variant="warning" title="Sensitive content">
            <p>{PAYLOAD_NOTICES.personalData}</p>
            <p>{PAYLOAD_NOTICES.handling}</p>
          </Banner>

          <p className="muted">{PAYLOAD_NOTICES.audit}</p>

          <dl className="snapshot-list">
            <div>
              <dt>Payload</dt>
              <dd className="font-mono">{data.id}</dd>
            </div>
            <div>
              <dt>Connection</dt>
              <dd className="font-mono">{data.connectionId !== null ? data.connectionId : '—'}</dd>
            </div>
            <div>
              <dt>Received</dt>
              <dd>{dateTime(data.receivedAt, timezone)}</dd>
            </div>
            <div>
              <dt>Provider time</dt>
              <dd>{data.sourceAt ? dateTime(data.sourceAt, timezone) : 'Not provided'}</dd>
            </div>
            <div>
              <dt>Signature</dt>
              <dd>{data.signatureVerified ? 'Verified' : 'Not verified'}</dd>
            </div>
            <div>
              <dt>Digest</dt>
              <dd className="font-mono" style={{ wordBreak: 'break-all' }}>
                {data.digest || '—'}
              </dd>
            </div>
          </dl>

          {summaryText && <p className="muted">{summaryText}</p>}

          {described.hints.length > 0 && (
            <Banner variant="danger">
              {`This payload appears to contain ${described.hints.join(' and ')}. Handle it as personal data.`}
            </Banner>
          )}

          <div className="stack-sm">
            <div>
              <Button
                variant="secondary"
                size="sm"
                aria-expanded={revealed}
                onClick={() => setRevealed((r) => !r)}
              >
                {revealed ? 'Hide payload content' : 'Show payload content'}
              </Button>
            </div>

            {revealed && (
              <div>
                {described.text ? (
                  <div className="stack-sm">
                    <pre
                      tabIndex={0}
                      aria-label="Diagnostic payload content"
                      style={{
                        maxHeight: '60vh',
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        padding: 'var(--space-3)',
                        background: 'var(--color-surface-subtle)',
                        fontSize: 'var(--text-caption)',
                      }}
                    >
                      {described.text}
                    </pre>
                    {described.previewTruncated && (
                      <p className="muted">
                        {`Showing the first 20000 of ${described.totalChars} characters.`}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="muted">The server returned no payload content.</p>
                )}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </Drawer>
  )
}
