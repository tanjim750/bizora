'use client'

import Link from 'next/link'
import { useState } from 'react'
import { clientApi } from '@/lib/clientApi'
import { businessApiPath, detailPath, MANAGER_ROLES } from '@/lib/catalog'
import { assessmentPayload, reviewedMapping } from '@/lib/productReview'
import { fieldValue } from '@/lib/format'
import { StatusBadge } from './DataTable'

export default function ProductAssessment({ businessId, role }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [payload, setPayload] = useState(null)
  const [candidates, setCandidates] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [reason, setReason] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [feedback, setFeedback] = useState('')
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    setPayload(null)
    setCandidates([])
    setSelectedId('')
    setConfirmed(false)
    setFeedback('')
    const form = new FormData(event.currentTarget)
    try {
      const request = assessmentPayload({
        name: form.get('name'),
        sku: form.get('sku'),
        connectionId: form.get('connection_id'),
        externalProductId: form.get('external_product_id'),
      })
      const assessment = await clientApi(businessApiPath(businessId, 'products/assess'), {
        method: 'POST',
        body: request,
      })
      setPayload(request)
      setResult(assessment)
      if (assessment.decision === 'REVIEW') {
        const details = await Promise.all(
          (assessment.candidate_ids || []).map(async (id) => {
            const detail = await clientApi(businessApiPath(businessId, `products/${id}`))
            return detail.record || detail
          }),
        )
        setCandidates(details)
      }
    } catch (failure) {
      setError(failure.message)
    } finally {
      setBusy(false)
    }
  }
  async function mapSource(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setFeedback('')
    try {
      if (!confirmed) throw new Error('Confirm that you compared the source with the selected product.')
      const body = reviewedMapping(result, selectedId, reason, payload)
      const latest = await clientApi(businessApiPath(businessId, 'products/assess'), {
        method: 'POST',
        body: payload,
      })
      if (latest.decision !== 'REVIEW' || !latest.candidate_ids?.includes(Number(selectedId)))
        throw new Error('Source identity changed. Assess the product again before mapping.')
      await clientApi(businessApiPath(businessId, 'product-references'), {
        method: 'POST',
        body,
        headers: { 'Idempotency-Key': `frontend-${crypto.randomUUID()}` },
      })
      setFeedback('Reviewed source mapping saved internally. No external provider was changed.')
      setResult(null)
    } catch (failure) {
      setError(failure.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="surface">
      <div className="section-header">
        <div>
          <h2>Assess a product</h2>
          <p>Compare source identity and SKU evidence before recording a mapping.</p>
        </div>
      </div>
      <form className="filter-grid" onSubmit={submit}>
        <div>
          <label htmlFor="assess-name">Name</label>
          <input id="assess-name" name="name" required />
        </div>
        <div>
          <label htmlFor="assess-sku">SKU</label>
          <input id="assess-sku" name="sku" required />
        </div>
        <div>
          <label htmlFor="assess-connection">Connection ID for a source product</label>
          <input id="assess-connection" name="connection_id" inputMode="numeric" pattern="[0-9]+" />
        </div>
        <div>
          <label htmlFor="assess-external-id">External product ID</label>
          <input id="assess-external-id" name="external_product_id" />
        </div>
        <button className="button button-secondary" disabled={busy}>
          {busy ? 'Assessing…' : 'Assess product'}
        </button>
      </form>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {result && (
        <div className="plan-result" role="status">
          <StatusBadge
            text={result.decision === 'REVIEW' ? 'Needs review' : result.decision || 'Assessment'}
          />
          <p>Assessment only — no product was created or mapped.</p>
          <p>Rule: {fieldValue(result.rule)}</p>
          {result.decision === 'REUSE' && result.product_id && (
            <Link href={detailPath(businessId, 'products', result.product_id)}>
              Open authoritative product #{result.product_id}
            </Link>
          )}
          {result.decision === 'CREATE' && <p>No deterministic source match or shared SKU was found.</p>}
          {result.decision === 'REVIEW' && (
            <>
              <p>A shared SKU is not proof of identity. Compare each candidate with the source record.</p>
              <div className="card-stack">
                {candidates.map((candidate) => (
                  <div className="list-item" key={candidate.id}>
                    <strong>
                      {candidate.name} · #{candidate.id}
                    </strong>
                    <p>
                      SKU: {fieldValue(candidate.sku)} · Category: {fieldValue(candidate.category)}
                    </p>
                    <Link
                      href={detailPath(businessId, 'products', candidate.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Inspect product record
                    </Link>
                  </div>
                ))}
              </div>
              {MANAGER_ROLES.has(role) && payload?.connection_id && candidates.length > 0 && (
                <form className="create-record-form" onSubmit={mapSource}>
                  <h3>Record reviewed source mapping</h3>
                  <p>
                    Connection #{payload.connection_id} · external product{' '}
                    {payload.data.external_reference.external_product_id}
                  </p>
                  <label htmlFor="assess-candidate">Canonical product</label>
                  <select
                    id="assess-candidate"
                    value={selectedId}
                    onChange={(event) => setSelectedId(event.target.value)}
                    required
                  >
                    <option value="">Choose a reviewed candidate</option>
                    {candidates.map((candidate) => (
                      <option value={candidate.id} key={candidate.id}>
                        {candidate.name} · #{candidate.id}
                      </option>
                    ))}
                  </select>
                  <label htmlFor="assess-reason">Evidence for this decision</label>
                  <textarea
                    id="assess-reason"
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    required
                    rows={3}
                  />
                  <label>
                    <input
                      type="checkbox"
                      checked={confirmed}
                      onChange={(event) => setConfirmed(event.target.checked)}
                      required
                    />
                    I compared the source product with the selected canonical record.
                  </label>
                  <button className="button button-primary" disabled={busy || !selectedId || !confirmed}>
                    {busy ? 'Saving…' : 'Save reviewed mapping'}
                  </button>
                </form>
              )}
              {!MANAGER_ROLES.has(role) && <p>A manager must review and record a source mapping.</p>}
            </>
          )}
        </div>
      )}
      {feedback && (
        <p className="form-success" role="status">
          {feedback}
        </p>
      )}
    </section>
  )
}
