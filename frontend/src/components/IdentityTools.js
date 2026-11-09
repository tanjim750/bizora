'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { clientApi } from '@/lib/clientApi'
import { businessApiPath } from '@/lib/catalog'
import { fieldValue, label } from '@/lib/format'

const COMMANDS = [
  { key: 'canonical', title: 'Create or find canonical identity', fields: ['entity_type', 'entity_id'] },
  {
    key: 'register',
    title: 'Register external identity',
    fields: ['connection_id', 'entity_type', 'identity_type', 'value', 'external_id'],
  },
  { key: 'resolve', title: 'Resolve external identity', fields: ['external_identity_id'] },
  { key: 'resolve-many', title: 'Resolve multiple identities', fields: ['external_identity_ids'] },
  {
    key: 'link',
    title: 'Link reviewed identity',
    fields: ['external_identity_id', 'canonical_identity_id', 'reason'],
  },
  { key: 'unlink', title: 'Unlink reviewed identity', fields: ['link_id', 'reason'] },
  {
    key: 'set-status',
    title: 'Set canonical identity status',
    fields: ['canonical_identity_id', 'status', 'reason'],
  },
  {
    key: 'enrich-external',
    title: 'Enrich external evidence',
    fields: ['external_identity_id', 'metadata', 'observed_at', 'reason'],
  },
  { key: 'verify-contact', title: 'Verify contact', fields: ['contact_id', 'reason'] },
  {
    key: 'identified-link',
    title: 'Link identified visitor',
    fields: ['visitor_id', 'identification_event_id', 'external_identity_id'],
  },
  { key: 'anonymous-link', title: 'Link anonymous purchase', fields: ['visitor_id', 'purchase_event_id'] },
  { key: 'detect-merges', title: 'Detect merge candidates', fields: [] },
  { key: 'validate-links', title: 'Validate links', fields: [] },
]

const NUMERIC = new Set([
  'entity_id',
  'connection_id',
  'external_identity_id',
  'canonical_identity_id',
  'link_id',
  'contact_id',
  'visitor_id',
  'identification_event_id',
  'purchase_event_id',
])

function IdentityCommand({ businessId, command }) {
  const router = useRouter()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  async function submit(event) {
    event.preventDefault()
    setPending(true)
    setError('')
    setResult(null)
    const values = Object.fromEntries(new FormData(event.currentTarget).entries())
    try {
      for (const field of command.fields) {
        if (NUMERIC.has(field)) values[field] = Number(values[field])
        if (field === 'external_identity_ids')
          values[field] = values[field]
            .split(',')
            .map((item) => Number(item.trim()))
            .filter(Number.isSafeInteger)
        if (field === 'metadata') values[field] = JSON.parse(values[field])
      }
      const response = await clientApi(businessApiPath(businessId, `identity/${command.key}`), {
        method: 'POST',
        body: values,
      })
      setResult(response)
      router.refresh()
    } catch (failure) {
      setError(failure.message)
    } finally {
      setPending(false)
    }
  }
  return (
    <details className="command-card">
      <summary>{command.title}</summary>
      <form onSubmit={submit}>
        <p className="helptext">
          This command records a reviewed identity decision. It does not merge canonical records.
        </p>
        {command.fields.map((field) => (
          <div className="form-field" key={field}>
            <label htmlFor={`${command.key}-${field}`}>{label(field)} *</label>
            {field === 'status' ? (
              <select name={field} id={`${command.key}-${field}`} required>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
                <option value="SUPERSEDED">Superseded</option>
              </select>
            ) : field === 'metadata' || field === 'reason' ? (
              <textarea
                name={field}
                id={`${command.key}-${field}`}
                rows={field === 'metadata' ? 5 : 2}
                required
                placeholder={field === 'metadata' ? '{"source":"reviewed"}' : undefined}
              />
            ) : (
              <input
                name={field}
                id={`${command.key}-${field}`}
                required
                inputMode={NUMERIC.has(field) || field === 'external_identity_ids' ? 'numeric' : undefined}
                pattern={NUMERIC.has(field) ? '[1-9][0-9]*' : undefined}
              />
            )}
          </div>
        ))}
        <button className="button button-primary" disabled={pending}>
          {pending ? 'Saving…' : command.title}
        </button>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {result && (
          <div className="plan-result" role="status">
            <strong>Command completed</strong>
            <pre>{fieldValue(result)}</pre>
          </div>
        )}
      </form>
    </details>
  )
}

export default function IdentityTools({ businessId }) {
  return (
    <section className="command-section">
      <div className="section-header">
        <div>
          <h2>Identity management</h2>
          <p>Manager commands for source evidence, links, status, and candidate detection.</p>
        </div>
      </div>
      <div className="command-grid">
        {COMMANDS.map((command) => (
          <IdentityCommand key={command.key} businessId={businessId} command={command} />
        ))}
      </div>
    </section>
  )
}
