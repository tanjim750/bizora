'use client'

import React, { useState, useRef } from 'react'
import {
  Button,
  Field,
  Input,
  Select,
  Checkbox,
  Banner,
  EmptyState,
  Skeleton,
  StatusChip,
} from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime, enumLabel } from '@/lib/format'
import {
  GRAPH_ENTITY_TYPES,
  GRAPH_DIRECTIONS,
  GRAPH_DIRECTION_LABELS,
  PATH_MAX_HOPS,
  PATH_RESULT_LIMIT,
  pathSearchPath,
  normalizePathSearch,
  graphErrorMessage,
} from '@/lib/intelligence/graphExplore'

const HOP_OPTIONS = Array.from({ length: PATH_MAX_HOPS }, (_, i) => ({
  value: String(i + 1),
  label: `${i + 1} ${i === 0 ? 'hop' : 'hops'}`,
}))

const ENTITY_OPTIONS = GRAPH_ENTITY_TYPES.map((type) => ({
  value: type,
  label: enumLabel(type),
}))

const DIRECTION_OPTIONS = GRAPH_DIRECTIONS.map((dir) => ({
  value: dir,
  label: GRAPH_DIRECTION_LABELS[dir] || dir,
}))

export default function GraphPathFinder({ businessId, timezone }) {
  const [startType, setStartType] = useState('CUSTOMER')
  const [startId, setStartId] = useState('')
  const [endType, setEndType] = useState('ORDER')
  const [endId, setEndId] = useState('')
  const [direction, setDirection] = useState('BIDIRECTIONAL')
  const [maxDepth, setMaxDepth] = useState('3')
  const [explain, setExplain] = useState(true)
  const [minConfidence, setMinConfidence] = useState('')

  const [loading, setLoading] = useState(false)
  const [submittedOnce, setSubmittedOnce] = useState(false)
  const [validationError, setValidationError] = useState(null)
  const [searchError, setSearchError] = useState(null)
  const [result, setResult] = useState(null)
  const [searchedHops, setSearchedHops] = useState(3)
  const [statusText, setStatusText] = useState('')

  const reqCounter = useRef(0)

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmittedOnce(true)
    setValidationError(null)
    setSearchError(null)

    let path = null
    try {
      path = pathSearchPath(businessId, {
        startType,
        startId,
        endType,
        endId,
        direction,
        maxDepth: Number(maxDepth),
        explain,
        minConfidence: minConfidence.trim() ? minConfidence.trim() : undefined,
      })
    } catch (err) {
      setValidationError(err.message || 'Invalid parameters')
      setStatusText(err.message || 'Invalid parameters')
      return
    }

    const reqId = ++reqCounter.current
    setLoading(true)
    setStatusText('Searching the graph...')

    try {
      const data = await clientApi(path)
      if (reqId !== reqCounter.current) return
      const normalized = normalizePathSearch(data)
      setResult(normalized)
      setSearchedHops(Number(maxDepth))
      if (normalized.paths.length === 0) {
        setStatusText('No path found')
      } else {
        const count = normalized.paths.length
        setStatusText(`Found ${count} ${count === 1 ? 'path' : 'paths'}`)
      }
    } catch (err) {
      if (reqId !== reqCounter.current) return
      const errMsg = graphErrorMessage(err, {
        notFound:
          'The start or end entity is not in this business graph. Check the type and ID. If the record is new, rebuild the graph first.',
      })
      setSearchError(errMsg)
      setStatusText(errMsg)
    } finally {
      if (reqId === reqCounter.current) {
        setLoading(false)
      }
    }
  }

  return (
    <div className="stack">
      <div className="stack-sm">
        <h4 className="section-title">Find a path between two entities</h4>
        <p className="muted">
          Pick a start and an end record. The search follows stored relationships only and never invents a
          connection.
        </p>
      </div>

      <form onSubmit={handleSubmit} aria-label="Path search" className="stack-sm">
        <div className="grid-kpi">
          <Field label="Start entity type">
            <Select
              value={startType}
              onChange={(e) => setStartType(e.target.value)}
              options={ENTITY_OPTIONS}
            />
          </Field>

          <Field label="Start entity ID" hint="Whole number, for example 12.">
            <Input
              type="text"
              inputMode="numeric"
              value={startId}
              onChange={(e) => setStartId(e.target.value)}
              placeholder="e.g. 12"
            />
          </Field>

          <Field label="End entity type">
            <Select value={endType} onChange={(e) => setEndType(e.target.value)} options={ENTITY_OPTIONS} />
          </Field>

          <Field label="End entity ID" hint="Whole number, for example 12.">
            <Input
              type="text"
              inputMode="numeric"
              value={endId}
              onChange={(e) => setEndId(e.target.value)}
              placeholder="e.g. 45"
            />
          </Field>

          <Field
            label="Direction"
            hint="Either direction also finds a route from an order back to its customer."
          >
            <Select
              value={direction}
              onChange={(e) => setDirection(e.target.value)}
              options={DIRECTION_OPTIONS}
            />
          </Field>

          <Field label="Maximum hops" hint="A larger number searches more routes and can take longer.">
            <Select value={maxDepth} onChange={(e) => setMaxDepth(e.target.value)} options={HOP_OPTIONS} />
          </Field>
        </div>

        <Field hint="Also shows the facts and issues stored for each entity on the path.">
          <Checkbox checked={explain} onChange={(e) => setExplain(e.target.checked)}>
            Explain each step
          </Checkbox>
        </Field>

        <details className="stack-sm">
          <summary style={{ cursor: 'pointer', fontWeight: 500 }}>Filters</summary>
          <div style={{ marginTop: 'var(--space-2)' }}>
            <Field
              label="Minimum confidence"
              hint="Optional, from 0 to 1. Relationships below it are ignored."
            >
              <Input
                type="text"
                inputMode="decimal"
                value={minConfidence}
                onChange={(e) => setMinConfidence(e.target.value)}
                placeholder="e.g. 0.8"
              />
            </Field>
          </div>
        </details>

        <div>
          <Button variant="primary" type="submit" loading={loading} disabled={loading}>
            Find paths
          </Button>
        </div>
      </form>

      <div role="status" aria-live="polite" className="sr-only">
        {statusText}
      </div>

      {validationError ? (
        <Banner variant="danger" title="The path search did not run">
          {validationError}
        </Banner>
      ) : loading ? (
        <div className="stack-sm">
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="80%" />
          <Skeleton variant="text" width="50%" />
        </div>
      ) : searchError ? (
        <Banner variant="danger" title="The path search failed">
          {searchError}
        </Banner>
      ) : !submittedOnce ? (
        <p className="muted">Choose two entities and select Find paths.</p>
      ) : result && result.paths.length === 0 ? (
        <EmptyState
          title="No path found"
          description={`There is no stored connection between these two entities within ${searchedHops} hops, in the chosen direction and with the chosen filters. Missing relationships are never invented.`}
        />
      ) : result && result.paths.length > 0 ? (
        <div className="stack">
          <p style={{ fontWeight: 600 }}>
            {`Found ${result.paths.length} ${result.paths.length === 1 ? 'path' : 'paths'}`}
          </p>

          {result.mayHaveMore && (
            <Banner variant="info">
              {'The server returns at most 10 paths and 10 were found. More connections may exist.'}
            </Banner>
          )}

          <ol className="stack" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {result.paths.map((p, pIdx) => (
              <li
                key={pIdx}
                style={{
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--space-4)',
                  background: 'var(--color-surface-subtle)',
                }}
              >
                <h5 className="section-title">
                  {p.length === 0
                    ? `Path ${pIdx + 1}: start and end are the same entity`
                    : `Path ${pIdx + 1}: ${p.length} ${p.length === 1 ? 'hop' : 'hops'}`}
                </h5>

                <ol
                  className="stack-sm"
                  style={{
                    listStyle: 'none',
                    padding: 0,
                    margin: 'var(--space-2) 0 0 0',
                  }}
                >
                  {p.steps.map((step, sIdx) => (
                    <li
                      key={sIdx}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 'var(--space-1)',
                      }}
                    >
                      <div>
                        <strong>{step.node.label}</strong>{' '}
                        <span className="font-mono">{`[${step.node.type} #${step.node.entityId}]`}</span>
                      </div>

                      {step.edge && (
                        <div className="muted" style={{ fontSize: 'var(--text-caption)' }}>
                          <span className="font-mono">{step.edge.relationshipType}</span>
                          {step.edge.confidencePercent !== null &&
                            ` · ${step.edge.confidencePercent}% confidence`}
                          {step.edge.ruleKey && ` · Rule ${step.edge.ruleKey}`}
                          {step.edge.source && ` · Source ${step.edge.source}`}
                          {step.edge.validFrom && ` · Valid from ${dateTime(step.edge.validFrom, timezone)}`}
                          {step.edge.validTo && ` · Valid until ${dateTime(step.edge.validTo, timezone)}`}
                        </div>
                      )}

                      {p.explained && (step.facts.length > 0 || step.issues.length > 0) && (
                        <details style={{ marginTop: 'var(--space-1)' }}>
                          <summary style={{ cursor: 'pointer', fontSize: 'var(--text-caption)' }}>
                            {`Facts (${step.facts.length}) and issues (${step.issues.length})`}
                          </summary>
                          <div className="stack-sm" style={{ marginTop: 'var(--space-2)' }}>
                            {step.facts.map((fact) => (
                              <div
                                key={fact.id}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 'var(--space-2)',
                                }}
                              >
                                <span>{`${fact.factType}: ${fact.statement}`}</span>
                                <StatusChip status={fact.status} size="sm" />
                              </div>
                            ))}
                            {step.issues.map((issue) => (
                              <div
                                key={issue.id}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 'var(--space-2)',
                                }}
                              >
                                <span>{`${issue.severity} · ${issue.title}`}</span>
                                <StatusChip status={issue.status} size="sm" />
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </li>
                  ))}
                </ol>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  )
}
