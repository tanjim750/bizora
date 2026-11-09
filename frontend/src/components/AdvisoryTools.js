'use client'

import { useState } from 'react'
import { clientApi } from '@/lib/clientApi'
import { businessApiPath } from '@/lib/catalog'
import { fieldValue, recordTitle, statusText } from '@/lib/format'
import { StatusBadge } from './DataTable'

export function AdvisoryTool({ businessId, endpoint, title, payload, inputLabel, inputName }) {
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  async function run(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    try {
      setResult(
        await clientApi(businessApiPath(businessId, endpoint), {
          method: 'POST',
          body: { ...payload, ...(inputName ? { [inputName]: input } : {}) },
        }),
      )
    } catch (failure) {
      setError(failure.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <form className="advisory-tool" onSubmit={run}>
      <h3>{title}</h3>
      {inputName && (
        <>
          <label htmlFor={`${endpoint.replaceAll('/', '-')}-${payload?.conversation_id || 'query'}`}>
            {inputLabel}
          </label>
          <textarea
            id={`${endpoint.replaceAll('/', '-')}-${payload?.conversation_id || 'query'}`}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            required
            rows={3}
            maxLength={2000}
          />
        </>
      )}
      <button className="button button-secondary" disabled={busy}>
        {busy ? 'Working…' : title}
      </button>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {result && (
        <div className="advisory-result" role="status">
          <StatusBadge text="AI suggestion" />
          <pre>{fieldValue(result)}</pre>
          <p>Review this output before taking action. It does not change an authoritative record.</p>
        </div>
      )}
    </form>
  )
}

export function RecordAdvisoryTools({ business, resource, record }) {
  const tools =
    resource === 'conversations'
      ? [
          ['ai/support/suggest-reply', 'Suggest a reply', { conversation_id: record.id }],
          [
            'ai/support/escalate',
            'Evaluate escalation',
            { conversation_id: record.id },
            'Customer message',
            'customer_message',
          ],
          ['ai/support/handover', 'Draft handover summary', { conversation_id: record.id }],
          [
            'ai/support/resume',
            'Review AI resume',
            { conversation_id: record.id },
            'Agent notes',
            'agent_notes',
          ],
          ['ai/summarization/conversation', 'Summarize conversation', { conversation_id: record.id }],
        ]
      : resource === 'calls'
        ? [['ai/summarization/call', 'Summarize call', { call_id: record.id }]]
        : resource === 'campaigns'
          ? [['ai/marketing/explain-campaign', 'Explain campaign', { campaign_id: record.id }]]
          : []
  if (!tools.length) return null
  return (
    <section className="surface">
      <div className="section-header">
        <div>
          <h2>AI advisory tools</h2>
          <p>Generated output needs human review and may be unavailable without a configured provider.</p>
        </div>
        <StatusBadge text="AI suggestion" />
      </div>
      <div className="advisory-tools">
        {tools.map(([endpoint, title, payload, inputLabel, inputName]) => (
          <AdvisoryTool
            key={endpoint}
            businessId={business.id}
            endpoint={endpoint}
            title={title}
            payload={payload}
            inputLabel={inputLabel}
            inputName={inputName}
          />
        ))}
      </div>
    </section>
  )
}

export function AssistantWorkspace({ business, recommendations, issues, hideHeading = false }) {
  const suggestions = Array.isArray(recommendations) ? recommendations : []
  const issueRows = Array.isArray(issues) ? issues : []
  return (
    <>
      {!hideHeading && (
        <div className="page-heading">
          <div>
            <p className="page-context">Assistance</p>
            <h1>AI assistant</h1>
            <p>
              Ask a question about this business. Responses are advisory and must be checked against recorded
              evidence.
            </p>
          </div>
          <StatusBadge text="AI suggestion" />
        </div>
      )}
      <section className="surface">
        <AdvisoryTool
          businessId={business.id}
          endpoint="ai/assistant/query"
          title="Ask the assistant"
          payload={{}}
          inputName="query"
          inputLabel="Question"
        />
      </section>
      <div className="overview-columns">
        <section className="surface">
          <div className="section-header">
            <h2>Recorded recommendations</h2>
            <StatusBadge text="AI suggestion" />
          </div>
          {suggestions.length ? (
            <div className="card-stack">
              {suggestions.map((row) => (
                <div className="list-item" key={row.id}>
                  <strong>{recordTitle(row)}</strong>
                  <StatusBadge text={statusText(row)} />
                  <p>{fieldValue(row.summary || row.description || row.reason)}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">No supported recommendations recorded.</div>
          )}
        </section>
        <section className="surface">
          <div className="section-header">
            <h2>Open issues</h2>
            <span className="count-chip">{issueRows.length}</span>
          </div>
          {issueRows.length ? (
            <div className="card-stack">
              {issueRows.map((row) => (
                <div className="list-item" key={row.id}>
                  <strong>{recordTitle(row)}</strong>
                  <p>{fieldValue(row.description)}</p>
                  <AdvisoryTool
                    businessId={business.id}
                    endpoint="ai/diagnosis/diagnose-issue"
                    title="Diagnose issue"
                    payload={{ issue_id: row.id }}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">No open issues recorded.</div>
          )}
        </section>
      </div>
    </>
  )
}
