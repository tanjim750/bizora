'use client'

import { useState, useRef, useCallback } from 'react'
import { Banner, Button, Field, Input } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { enumLabel } from '@/lib/format/index.js'
import { Search } from 'lucide-react'
import {
  SCORE_HELP,
  validateSearchQuery,
  searchPath,
  normalizeSearch,
  scoreLabel,
  searchModeNotice,
  resultCountText,
  searchErrorReason,
} from '@/lib/knowledge/search'

export default function KnowledgeSearch({ businessId }) {
  const [queryInput, setQueryInput] = useState('')
  const [fieldError, setFieldError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)
  const reqSeq = useRef(0)

  const executeSearch = useCallback(
    (q) => {
      const validation = validateSearchQuery(q)
      if (!validation.ok) {
        setFieldError(validation.message)
        return
      }
      setFieldError(null)
      setError(null)
      setLoading(true)

      const currentSeq = ++reqSeq.current
      try {
        const path = searchPath(businessId, validation.query)
        clientApi(path)
          .then((res) => {
            if (currentSeq !== reqSeq.current) return
            setData(normalizeSearch(res))
            setHasSearched(true)
            setLoading(false)
          })
          .catch((err) => {
            if (currentSeq !== reqSeq.current) return
            setError(err)
            setHasSearched(true)
            setLoading(false)
          })
      } catch (err) {
        if (currentSeq === reqSeq.current) {
          setError(err)
          setHasSearched(true)
          setLoading(false)
        }
      }
    },
    [businessId],
  )

  const handleSubmit = (e) => {
    e.preventDefault()
    executeSearch(queryInput)
  }

  const handleRetry = () => {
    executeSearch(queryInput)
  }

  const noticeText = searchModeNotice(
    data
      ? { mode: data.mode, semanticAvailable: data.semanticAvailable }
      : { mode: 'KEYWORD', semanticAvailable: false },
  )

  let liveStatus = ''
  if (loading) {
    liveStatus = 'Searching...'
  } else if (error) {
    liveStatus = searchErrorReason(error)
  } else if (hasSearched && data) {
    liveStatus = resultCountText(data.resultCount, data.limit)
  }

  return (
    <section className="stack-sm" style={{ marginTop: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
      <div role="status" aria-live="polite" className="sr-only">
        {liveStatus}
      </div>

      <h2 style={{ margin: 0, fontSize: 'var(--text-section)' }}>Search the knowledge base</h2>

      <form role="search" aria-label="Search the knowledge base" onSubmit={handleSubmit}>
        <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 20rem' }}>
            <Field label="Search words" htmlFor="kb-search-input" error={fieldError}>
              <Input
                type="search"
                id="kb-search-input"
                placeholder="For example: refund window"
                maxLength={200}
                aria-label="Search words"
                value={queryInput}
                onChange={(e) => {
                  setQueryInput(e.target.value)
                  if (fieldError) setFieldError(null)
                }}
              />
            </Field>
          </div>
          <div style={{ marginTop: '1.65rem' }}>
            <Button variant="primary" icon={Search} loading={loading} type="submit">
              Search
            </Button>
          </div>
        </div>
      </form>

      <p className="muted" style={{ margin: 0 }}>
        {noticeText}
      </p>

      {!hasSearched && !loading && (
        <p className="muted">Type a word or phrase from a policy, a product guide or a support answer.</p>
      )}

      {error && !loading && (
        <Banner variant="danger">
          <p>{searchErrorReason(error)}</p>
          <div style={{ marginTop: 'var(--space-2)' }}>
            <Button variant="secondary" size="sm" onClick={handleRetry}>
              Try again
            </Button>
          </div>
        </Banner>
      )}

      {hasSearched && !loading && !error && data && (
        <>
          {data.results.length === 0 ? (
            <div className="stack-sm" style={{ marginTop: 'var(--space-2)' }}>
              <p>
                <strong>No matches</strong>
              </p>
              <p className="muted">
                Try different words. This search finds text that contains your words; it does not look for
                similar meanings.
              </p>
            </div>
          ) : (
            <div className="stack-sm" style={{ marginTop: 'var(--space-2)' }}>
              <p>
                {`Results for "${data.query}"`} &mdash; {resultCountText(data.resultCount, data.limit)}
              </p>

              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {data.results.map((item) => (
                  <li
                    key={item.chunk_id}
                    style={{
                      padding: 'var(--space-3)',
                      background: 'var(--color-surface-subtle)',
                      borderRadius: 'var(--radius-md)',
                      marginBottom: 'var(--space-2)',
                    }}
                  >
                    <h3 style={{ margin: 0, fontSize: 'var(--text-body)' }}>
                      {item.document_title || 'Untitled document'}
                      {item.version != null && (
                        <small
                          className="muted"
                          style={{ fontWeight: 'normal', marginLeft: 'var(--space-1)' }}
                        >
                          {`v${item.version}`}
                        </small>
                      )}
                    </h3>

                    <div className="muted" style={{ margin: 'var(--space-1) 0' }}>
                      <span>{item.source_name || 'Unnamed source'}</span>
                      {item.section && <span>{` · ${item.section}`}</span>}
                      {item.document_type && <span>{` · ${enumLabel(item.document_type)}`}</span>}
                    </div>

                    {item.snippet && (
                      <p style={{ margin: 'var(--space-1) 0 var(--space-2) 0', whiteSpace: 'pre-wrap' }}>
                        {item.snippet}
                      </p>
                    )}

                    <div>
                      <span className="muted">{scoreLabel(item.score)}</span>
                    </div>
                  </li>
                ))}
              </ul>

              <p className="muted" style={{ marginTop: 'var(--space-2)' }}>
                {SCORE_HELP}
              </p>
            </div>
          )}
        </>
      )}
    </section>
  )
}
