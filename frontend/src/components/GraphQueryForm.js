'use client'

import React, { useState, useRef } from 'react'
import { Button, Field, Input, Select, Banner, EmptyState, Skeleton, DataTable } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { enumLabel } from '@/lib/format'
import {
  graphQueryPath,
  normalizeGraphQuery,
  describeGraphQuery,
  QUERY_ROW_CAP,
} from '@/lib/intelligence/graphQuery'
import {
  GRAPH_ENTITY_TYPES,
  GRAPH_RELATIONSHIP_TYPES,
  graphErrorMessage,
} from '@/lib/intelligence/graphExplore'

const ENTITY_TYPE_OPTIONS = [
  { value: '', label: 'Any entity (list relationships)' },
  ...GRAPH_ENTITY_TYPES.map((t) => ({ value: t, label: enumLabel(t) })),
]

const RELATIONSHIP_OPTIONS = [
  { value: '', label: 'Any relationship' },
  ...GRAPH_RELATIONSHIP_TYPES.map((r) => ({ value: r, label: r })),
]

export default function GraphQueryForm({ businessId }) {
  const [entityType, setEntityType] = useState('')
  const [entityId, setEntityId] = useState('')
  const [relationshipType, setRelationshipType] = useState('')
  const [limit, setLimit] = useState('100')
  const [minConfidence, setMinConfidence] = useState('')

  const [loading, setLoading] = useState(false)
  const [submittedOnce, setSubmittedOnce] = useState(false)
  const [submittedOptions, setSubmittedOptions] = useState(null)
  const [validationError, setValidationError] = useState(null)
  const [searchError, setSearchError] = useState(null)
  const [result, setResult] = useState(null)
  const [statusText, setStatusText] = useState('')

  const reqCounter = useRef(0)

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmittedOnce(true)
    setValidationError(null)
    setSearchError(null)

    const opts = {
      entityType: entityType || undefined,
      entityId: entityId.trim() || undefined,
      relationshipType: relationshipType || undefined,
      limit: limit.trim() ? Number(limit.trim()) : 100,
      minConfidence: minConfidence.trim() || undefined,
    }

    let path = null
    try {
      path = graphQueryPath(businessId, opts)
    } catch (err) {
      setValidationError(err.message || 'Invalid parameters')
      setStatusText(err.message || 'Invalid parameters')
      return
    }

    const reqId = ++reqCounter.current
    setLoading(true)
    setStatusText('Running the query...')
    setSubmittedOptions(opts)

    try {
      const data = await clientApi(path)
      if (reqId !== reqCounter.current) return
      const normalized = normalizeGraphQuery(data)
      setResult(normalized)
      if (normalized.nodes.length === 0 && normalized.edges.length === 0) {
        setStatusText('Nothing matched')
      } else {
        setStatusText(`${normalized.nodeCount} entities and ${normalized.edgeCount} relationships`)
      }
    } catch (err) {
      if (reqId !== reqCounter.current) return
      const errMsg = graphErrorMessage(err, {
        notFound:
          'That entity is not in the graph. Check the type and ID. If the record is new, rebuild the graph first.',
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
        <h4 className="section-title">Query the graph</h4>
        <p className="muted">
          Either list relationships of one kind, or look around one entity. Results come from the stored graph
          only.
        </p>
      </div>

      <form onSubmit={handleSubmit} aria-label="Graph query" className="stack-sm">
        <div className="grid-kpi">
          <Field label="Entity type">
            <Select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              options={ENTITY_TYPE_OPTIONS}
            />
          </Field>

          <Field
            label="Entity ID"
            hint="Needed when an entity type is chosen. Leave both empty to list relationships."
          >
            <Input
              type="text"
              inputMode="numeric"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="e.g. 5"
            />
          </Field>

          <Field label="Relationship type">
            <Select
              value={relationshipType}
              onChange={(e) => setRelationshipType(e.target.value)}
              options={RELATIONSHIP_OPTIONS}
            />
          </Field>

          <Field
            label="Limit"
            hint="From 1 to 1000. With an entity it caps the number of nodes, otherwise the number of relationships."
          >
            <Input
              type="text"
              inputMode="numeric"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              placeholder="100"
            />
          </Field>
        </div>

        <details className="stack-sm">
          <summary style={{ cursor: 'pointer', fontWeight: 500 }}>Filters</summary>
          <div style={{ marginTop: 'var(--space-2)' }}>
            <Field label="Minimum confidence" hint="Optional, from 0 to 1.">
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
            Run query
          </Button>
        </div>
      </form>

      <div role="status" aria-live="polite" className="sr-only">
        {statusText}
      </div>

      {validationError ? (
        <Banner variant="danger" title="The query did not run">
          {validationError}
        </Banner>
      ) : loading ? (
        <div className="stack-sm">
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="80%" />
          <Skeleton variant="text" width="50%" />
        </div>
      ) : searchError ? (
        <Banner variant="danger" title="The query failed">
          {searchError}
        </Banner>
      ) : !submittedOnce ? (
        <p className="muted">Choose what to look for and select Run query.</p>
      ) : result && result.nodes.length === 0 && result.edges.length === 0 ? (
        <EmptyState
          title="Nothing matched"
          description="No stored relationships match this query. If the graph has never been built, an owner or manager can rebuild it from the Data Pipeline tab."
        />
      ) : result && (result.nodes.length > 0 || result.edges.length > 0) ? (
        <div className="stack">
          <div className="stack-sm">
            <p className="muted">{`What ran: ${describeGraphQuery(submittedOptions || {})}`}</p>
            <p style={{ fontWeight: 600 }}>
              {`${result.nodeCount} entities and ${result.edgeCount} relationships`}
              {result.depthReached !== null ? ` · depth reached ${result.depthReached}` : ''}
            </p>
          </div>

          {result.truncated && (
            <Banner variant="warning">
              {`The server stopped at the limit of ${submittedOptions?.limit ?? 100}. Raise the limit or narrow the query to see more.`}
            </Banner>
          )}

          {result.hiddenEdges > 0 && (
            <p className="muted">
              {`${result.hiddenEdges} relationships were left out because one of their entities is not in the answer.`}
            </p>
          )}

          {result.nodes.length > 0 && (
            <div className="stack-sm">
              <h5 className="section-title">Entities</h5>
              <DataTable
                openInDrawer={false}
                showDensityToggle={false}
                ariaLabel="Entities"
                rows={result.nodes.slice(0, QUERY_ROW_CAP)}
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
              {result.nodes.length > QUERY_ROW_CAP && (
                <p className="muted">{`Showing the first 200 of ${result.nodes.length}.`}</p>
              )}
            </div>
          )}

          {result.edges.length > 0 && (
            <div className="stack-sm">
              <h5 className="section-title">Relationships</h5>
              <DataTable
                openInDrawer={false}
                showDensityToggle={false}
                ariaLabel="Relationships"
                rows={result.edges.slice(0, QUERY_ROW_CAP)}
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
              {result.edges.length > QUERY_ROW_CAP && (
                <p className="muted">{`Showing the first 200 of ${result.edges.length}.`}</p>
              )}
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
