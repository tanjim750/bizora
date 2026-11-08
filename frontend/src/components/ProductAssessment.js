'use client'

import { useState } from 'react'
import { clientApi } from '@/lib/clientApi'
import { businessApiPath } from '@/lib/catalog'
import { fieldValue } from '@/lib/format'
import { StatusBadge } from './DataTable'

export default function ProductAssessment({ businessId }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    const form = new FormData(event.currentTarget)
    const connection = form.get('connection_id')
    try {
      setResult(
        await clientApi(businessApiPath(businessId, 'products/assess'), {
          method: 'POST',
          body: {
            data: { name: form.get('name'), sku: form.get('sku') },
            ...(connection ? { connection_id: Number(connection) } : {}),
          },
        }),
      )
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
          <p>Check source and SKU evidence before creating or mapping a product.</p>
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
          <label htmlFor="assess-connection">Connection ID, if applicable</label>
          <input id="assess-connection" name="connection_id" inputMode="numeric" pattern="[0-9]+" />
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
          <p>Assessment only — no product was created.</p>
          <pre>{fieldValue(result)}</pre>
        </div>
      )}
    </section>
  )
}
