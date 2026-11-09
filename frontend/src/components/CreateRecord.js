'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { businessApiPath } from '@/lib/catalog'
import { clientApi } from '@/lib/clientApi'

export default function CreateRecord({ businessId, resource }) {
  const router = useRouter()
  const [pending, setPending] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState('')

  async function submit(event, assess = false) {
    event.preventDefault()
    setPending(true)
    setFeedback('')
    setError('')
    const form = new FormData(event.currentTarget)
    let data
    try {
      data = JSON.parse(form.get('data'))
    } catch {
      setError('Enter a valid JSON object.')
      setPending(false)
      return
    }
    if (!data || Array.isArray(data) || typeof data !== 'object') {
      setError('The record must be a JSON object.')
      setPending(false)
      return
    }
    const connection = form.get('connection_id')
    const body = { data, ...(connection ? { connection_id: Number(connection) } : {}) }
    const path = businessApiPath(businessId, assess ? 'products/assess' : resource)
    try {
      const result = await clientApi(path, {
        method: 'POST',
        body,
        headers: { 'Idempotency-Key': `frontend-${crypto.randomUUID()}` },
      })
      setFeedback(
        assess
          ? `Assessment: ${result.decision || 'review returned'}. No record created.`
          : `Record #${result.id || 'new'} saved internally.`,
      )
      if (!assess) router.refresh()
    } catch (failure) {
      setError(failure.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <details className="surface disclosure">
      <summary>Add canonical {resource.replaceAll('-', ' ')} record</summary>
      <form className="create-record-form" onSubmit={(event) => submit(event)}>
        <p className="helptext">
          Advanced intake. Provide only canonical fields; Django validates tenant ownership, relationships,
          and allowed values. A connection ID is required for source-owned records.
        </p>
        <label htmlFor="record-connection">Integration connection ID, if applicable</label>
        <input id="record-connection" name="connection_id" inputMode="numeric" pattern="[0-9]+" />
        <label htmlFor="record-json">Record fields (JSON object)</label>
        <textarea
          id="record-json"
          name="data"
          rows={8}
          spellCheck={false}
          placeholder='{"display_name": "Customer name"}'
          required
        />
        <div className="button-row">
          <button className="button button-primary" type="submit" disabled={pending}>
            {pending ? 'Saving…' : 'Save internal record'}
          </button>
          {resource === 'products' && (
            <button
              className="button button-secondary"
              type="button"
              disabled={pending}
              onClick={(event) =>
                submit({ preventDefault() {}, currentTarget: event.currentTarget.form }, true)
              }
            >
              Assess product first
            </button>
          )}
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {feedback && (
          <p className="form-success" role="status">
            {feedback}
          </p>
        )}
      </form>
    </details>
  )
}
