'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { clientApi } from '@/lib/clientApi'
import { businessApiPath } from '@/lib/catalog'
import { fieldValue, recordTitle, statusText } from '@/lib/format'
import { StatusBadge } from './DataTable'

function ReviewForm({ path, idField, id, decisions, detail }) {
  const router = useRouter()
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [pending, startTransition] = useTransition()

  async function submit(decision) {
    setError('')
    setSuccess('')
    try {
      const result = await clientApi(path, { method: 'POST', body: { [idField]: id, decision, reason } })
      setSuccess(
        detail
          ? `Review recorded. ${fieldValue(result.execution?.reason || 'Execution remains separate.')}`
          : 'Review recorded. No records were merged.',
      )
      startTransition(() => router.refresh())
    } catch (failure) {
      setError(failure.message)
    }
  }

  return (
    <div className="review-controls">
      <label htmlFor={`${idField}-${id}`}>Review reason</label>
      <textarea
        id={`${idField}-${id}`}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        rows={2}
        required
        maxLength={2000}
      />
      <div className="button-row">
        {decisions.map((decision) => (
          <button
            key={decision.value}
            className={`button ${decision.value === 'REJECTED' ? 'button-secondary' : 'button-primary'}`}
            type="button"
            disabled={pending || !reason.trim()}
            onClick={() => submit(decision.value)}
          >
            {pending ? 'Saving…' : decision.label}
          </button>
        ))}
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {success && (
        <p className="form-success" role="status">
          {success}
        </p>
      )}
    </div>
  )
}

export function ActionReview({ business, actions, hideHeading = false }) {
  const rows = Array.isArray(actions) ? actions : actions?.results || []
  return (
    <>
      {!hideHeading && (
        <div className="page-heading">
          <div>
            <p className="page-context">Assistance</p>
            <h1>AI proposals</h1>
            <p>
              Suggestions are advisory. Approval records a human decision; provider execution is separate.
            </p>
          </div>
          <StatusBadge text="AI suggestion" />
        </div>
      )}
      <div className="card-stack">
        {rows.map((action) => (
          <article className="surface review-card" key={action.id}>
            <div className="section-header">
              <div>
                <h2>{recordTitle(action)}</h2>
                <p>Proposal #{action.id}</p>
              </div>
              <StatusBadge text={statusText(action)} />
            </div>
            <dl className="review-meta">
              <div>
                <dt>Proposed action</dt>
                <dd>{fieldValue(action.action_type || action.type)}</dd>
              </div>
              <div>
                <dt>Reason</dt>
                <dd>{fieldValue(action.reason || action.description)}</dd>
              </div>
            </dl>
            {action.status === 'SUGGESTED' && (
              <ReviewForm
                path={businessApiPath(business.id, `actions/${action.id}/review`)}
                idField="action_id"
                id={action.id}
                detail
                decisions={[
                  { value: 'APPROVED', label: 'Approve proposal' },
                  { value: 'REJECTED', label: 'Reject proposal' },
                ]}
              />
            )}
          </article>
        ))}
        {rows.length === 0 && (
          <div className="surface empty-state">
            <h2>No proposals recorded</h2>
            <p>Suggestions will appear when an authorized AI service records them.</p>
          </div>
        )}
      </div>
    </>
  )
}

function IdentityCard({ business, row, kind }) {
  const [plan, setPlan] = useState(null)
  const [error, setError] = useState('')
  const [pending, startTransition] = useTransition()
  async function dryRun() {
    setError('')
    setPlan(null)
    try {
      setPlan(
        await clientApi(businessApiPath(business.id, `identity/merge-candidates/${row.id}/dry-run`), {
          method: 'POST',
          body: {},
        }),
      )
    } catch (failure) {
      setError(failure.message)
    }
  }
  return (
    <article className="surface review-card">
      <div className="section-header">
        <div>
          <h2>
            {kind === 'conflict' ? 'Identity conflict' : 'Merge candidate'} #{row.id}
          </h2>
          <p>Business #{business.id} · review required</p>
        </div>
        <StatusBadge text={statusText(row)} />
      </div>
      <dl className="review-meta">
        <div>
          <dt>Evidence</dt>
          <dd>
            <pre>{fieldValue(row.evidence)}</pre>
          </dd>
        </div>
        <div>
          <dt>Rule</dt>
          <dd>{fieldValue(row.rule_key)}</dd>
        </div>
      </dl>
      {kind === 'candidate' && (
        <>
          <button
            className="button button-secondary"
            disabled={pending}
            type="button"
            onClick={() => startTransition(dryRun)}
          >
            Generate impact plan
          </button>
          {plan && (
            <div className="plan-result">
              <strong>Plan only — no records merged</strong>
              <pre>{fieldValue(plan)}</pre>
            </div>
          )}
        </>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <ReviewForm
        path={businessApiPath(
          business.id,
          `identity/${kind === 'conflict' ? 'review-conflict' : 'review-merge'}`,
        )}
        idField={kind === 'conflict' ? 'conflict_id' : 'candidate_id'}
        id={row.id}
        decisions={
          kind === 'conflict'
            ? [
                { value: 'RESOLVED', label: 'Resolve conflict' },
                { value: 'IGNORED', label: 'Ignore conflict' },
              ]
            : [
                { value: 'APPROVED', label: 'Approve candidate' },
                { value: 'REJECTED', label: 'Reject candidate' },
              ]
        }
      />
    </article>
  )
}

export function IdentityReview({ business, conflicts, candidates, hideHeading = false }) {
  const conflictRows = conflicts?.results || []
  const candidateRows = candidates?.results || []
  return (
    <>
      {!hideHeading && (
        <div className="page-heading">
          <div>
            <p className="page-context">Administration</p>
            <h1>Identity review</h1>
            <p>Review evidence and impact before changing identity decisions.</p>
          </div>
          <StatusBadge text="Review required" />
        </div>
      )}
      <div className="alert alert-warning">
        <strong>Merge execution is blocked.</strong> An impact plan and candidate approval do not consolidate
        records.
      </div>
      <div className="overview-columns">
        <section>
          <h2>Conflicts ({conflicts?.count ?? 0})</h2>
          <div className="card-stack">
            {conflictRows.map((row) => (
              <IdentityCard key={row.id} business={business} row={row} kind="conflict" />
            ))}
            {conflictRows.length === 0 && <div className="surface empty-state">No conflicts recorded.</div>}
          </div>
        </section>
        <section>
          <h2>Merge candidates ({candidates?.count ?? 0})</h2>
          <div className="card-stack">
            {candidateRows.map((row) => (
              <IdentityCard key={row.id} business={business} row={row} kind="candidate" />
            ))}
            {candidateRows.length === 0 && (
              <div className="surface empty-state">No merge candidates recorded.</div>
            )}
          </div>
        </section>
      </div>
    </>
  )
}
