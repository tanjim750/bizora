'use client'

import React, { useState, useMemo } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Send,
  Shield,
  Layers,
  ArrowRight,
  Clock,
  ExternalLink,
  Bot,
  Zap,
  Info,
  Check,
  X,
  FileText,
  AlertCircle,
} from 'lucide-react'
import {
  DataTable,
  StatusChip,
  SeverityChip,
  ConfidenceMeter,
  EmptyState,
  UnavailableState,
  SimulatedBadge,
  Button,
  Dialog,
  Input,
  Field,
  Select,
  Textarea,
  CopyableCode,
  Banner,
  KpiTile,
  Tabs,
} from '@/components/ui'
import { businessPath, businessApiPath, WRITER_ROLES } from '@/lib/catalog'
import { dateTime, relativeTime } from '@/lib/format'
import { clientApi } from '@/lib/clientApi'

export default function AiStudio({
  business = {},
  businessId,
  activeTab = 'assistant',
  recommendations = [],
  actions = [],
  issues = [],
}) {
  const router = useRouter()
  const canWrite = WRITER_ROLES.has(business?.role)
  const timezone = business?.timezone || 'Asia/Dhaka'

  const aiTabs = [
    { id: 'assistant', label: 'AI Assistant', icon: Bot, href: `/business/${businessId}/ai/assistant` },
    { id: 'actions', label: 'Action Proposals', icon: Zap, href: `/business/${businessId}/ai/actions` },
    { id: 'audit', label: 'Audit Trail', icon: FileText, href: `/business/${businessId}/ai/audit` },
  ]

  // ==========================================
  // ASSISTANT QUERY STATE (E1)
  // ==========================================
  const [queryText, setQueryText] = useState('')
  const [querying, setQuerying] = useState(false)
  const [queryError, setQueryError] = useState('')
  const [queryResult, setQueryResult] = useState(null)

  const handleQuerySubmit = async (e) => {
    e.preventDefault()
    if (!queryText.trim() || queryText.length < 3) return

    setQuerying(true)
    setQueryError('')
    setQueryResult(null)

    try {
      const data = await clientApi(`businesses/${businessId}/ai/assistant/query`, {
        method: 'POST',
        body: JSON.stringify({
          query: queryText.trim(),
          conversation_id: null,
        }),
      })
      setQueryResult(data)
    } catch (err) {
      setQueryError(
        err.detail || err.message || 'Assistant query failed. Verify backend services are active.',
      )
    } finally {
      setQuerying(false)
    }
  }

  // ==========================================
  // ACTION PROPOSALS REVIEW STATE (E11, E16)
  // ==========================================
  const allActions = Array.isArray(actions) ? actions : actions?.results || []
  const [actionStatusFilter, setActionStatusFilter] = useState('ALL')
  const [reviewingActionId, setReviewingActionId] = useState(null)
  const [reviewNote, setReviewNote] = useState('')
  const [reviewBusy, setReviewBusy] = useState(false)
  const [reviewError, setReviewError] = useState('')
  const [reviewSuccess, setReviewSuccess] = useState('')

  const filteredActions = useMemo(() => {
    return allActions.filter((act) => {
      if (actionStatusFilter !== 'ALL' && act.status !== actionStatusFilter) return false
      return true
    })
  }, [allActions, actionStatusFilter])

  const handleExecuteReview = async (actionId, decision) => {
    if (!reviewNote.trim() || reviewNote.length < 3 || reviewNote.length > 1000) {
      setReviewError('Review note must be between 3 and 1000 characters.')
      return
    }

    setReviewBusy(true)
    setReviewError('')
    setReviewSuccess('')

    try {
      const endpoint = decision === 'APPROVED' ? `actions/${actionId}/approve` : `actions/${actionId}/reject`
      const res = await clientApi(endpoint, {
        method: 'POST',
        body: JSON.stringify({ note: reviewNote.trim() }),
      })

      setReviewSuccess(`Action marked as ${decision}. Note recorded. Execution is simulated.`)
      setReviewNote('')
      setReviewingActionId(null)
      router.refresh()
    } catch (err) {
      setReviewError(err.detail || err.message || `Failed to record ${decision.toLowerCase()} review.`)
    } finally {
      setReviewBusy(false)
    }
  }

  return (
    <div className="workspace-page stack-lg">
      <Tabs tabs={aiTabs} activeTab={activeTab} ariaLabel="AI Studio Workspace Navigation" />

      {/* ============================================================== */}
      {/* TAB 1: AI ASSISTANT (E1)                                       */}
      {/* ============================================================== */}
      {activeTab === 'assistant' && (
        <div className="ai-workspace-layout">
          <Banner variant="info">
            Answers are advisory and synthesized from recorded business facts and customer evidence.
          </Banner>

          {/* Query Formulation Panel */}
          <form className="ai-query-panel" onSubmit={handleQuerySubmit}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <Bot size={18} className="text-primary" />
                <h3 className="section-title" style={{ margin: 0 }}>
                  Ask Bizora Assistant
                </h3>
              </div>
              <span className="text-caption font-mono text-muted">{queryText.length} / 2000 chars</span>
            </div>

            <Textarea
              placeholder="e.g. What are our top unfulfilled orders this week, and are there active courier delivery exceptions?"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              rows={3}
              maxLength={2000}
              required
              aria-label="Assistant inquiry text"
            />

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 'var(--space-2)',
              }}
            >
              <span className="text-caption text-secondary">
                Inquiries are cross-referenced with domain facts, recent activity, and SLA integrity rules.
              </span>

              <Button
                type="submit"
                variant="primary"
                icon={Send}
                loading={querying}
                disabled={queryText.trim().length < 3 || querying}
              >
                {querying ? 'Synthesizing Answers (~10-15s)...' : 'Ask Assistant'}
              </Button>
            </div>
          </form>

          {/* Query Error Banner */}
          {queryError && <Banner variant="danger">{queryError}</Banner>}

          {/* Active Query Result */}
          {queryResult && (
            <div className="ai-answer-box">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: 'var(--space-2)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  <Sparkles size={16} className="text-primary" />
                  <span className="font-semibold text-caption text-secondary">ADVISORY SYNTHESIS</span>
                  <SimulatedBadge />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  {queryResult.model_name && (
                    <span className="badge badge-outline font-mono text-caption">
                      {queryResult.model_name}
                    </span>
                  )}
                  {queryResult.tokens_used != null && (
                    <span className="text-caption font-mono text-muted">
                      {queryResult.tokens_used} tokens
                    </span>
                  )}
                </div>
              </div>

              {/* Formatted Answer Body */}
              <div className="ai-answer-text">{queryResult.answer || 'No advisory text was returned.'}</div>

              {/* Grounding Facts & Evidence */}
              {queryResult.grounding_facts?.length > 0 && (
                <div className="ai-grounding-section">
                  <span className="font-semibold text-caption text-secondary">
                    GROUNDED IN THE FOLLOWING VERIFIED FACTS:
                  </span>
                  <div className="stack-sm">
                    {queryResult.grounding_facts.map((fact, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: 'var(--space-2)',
                          padding: 'var(--space-2) var(--space-3)',
                          background: 'var(--color-surface-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--color-border)',
                        }}
                      >
                        <CheckCircle2
                          size={16}
                          className="text-success"
                          style={{ marginTop: 2, flexShrink: 0 }}
                        />
                        <span className="text-body text-secondary">
                          {typeof fact === 'string'
                            ? fact
                            : fact.statement || fact.fact || JSON.stringify(fact)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Open Issues Referenced */}
              {queryResult.open_issues?.length > 0 && (
                <div className="ai-grounding-section">
                  <span className="font-semibold text-caption text-secondary">
                    ASSOCIATED INTEGRITY ISSUES REFERENCED:
                  </span>
                  <div className="stack-sm">
                    {queryResult.open_issues.map((iss, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: 'var(--space-2) var(--space-3)',
                          border: '1px solid var(--color-border)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <span className="font-semibold text-body">
                          {iss.title || `Issue #${iss.id || iss}`}
                        </span>
                        {iss.severity && <SeverityChip severity={iss.severity} size="sm" />}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Workflow Recommendations (E10) */}
          <div className="stack-sm">
            <div className="section-header">
              <div>
                <h3 className="section-title">Operational Recommendations</h3>
                <p className="section-desc">
                  Proactive suggestions derived from cross-domain anomalies and customer engagement trends.
                </p>
              </div>
            </div>

            {recommendations.length > 0 ? (
              <div className="stack-sm">
                {recommendations.map((rec) => (
                  <div key={rec.id} className="ai-recommendation-card">
                    <div className="stack-sm" style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <span className="badge badge-outline font-mono text-caption">
                          {rec.category || 'WORKFLOW'}
                        </span>
                        <h4 className="font-semibold text-body" style={{ margin: 0 }}>
                          {rec.title}
                        </h4>
                        {rec.priority && <SeverityChip severity={rec.priority} size="sm" />}
                      </div>

                      <p className="text-body text-secondary" style={{ margin: 0 }}>
                        {rec.description}
                      </p>

                      {rec.rationale && (
                        <span className="text-caption text-muted">Rationale: {rec.rationale}</span>
                      )}
                    </div>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setQueryText(`Analyze recommendation: ${rec.title}`)
                      }}
                    >
                      Inquire
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No active recommendations"
                description="Workflow recommendations will appear as operations data and anomaly detection accumulates."
              />
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: ACTION PROPOSALS (E11, E16)                             */}
      {/* ============================================================== */}
      {activeTab === 'actions' && (
        <div className="stack-lg">
          <Banner variant="warning">
            <strong>Execution is simulated.</strong> Action approvals record an audit entry but do not trigger
            automated external mutation.
          </Banner>

          {reviewSuccess && <Banner variant="success">{reviewSuccess}</Banner>}
          {reviewError && <Banner variant="danger">{reviewError}</Banner>}

          {/* Filter Pills */}
          <div
            className="surface card-padding"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 'var(--space-2)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
              <span className="font-semibold text-caption text-secondary">Status:</span>
              {['ALL', 'SUGGESTED', 'APPROVED', 'REJECTED', 'EXECUTED'].map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => setActionStatusFilter(st)}
                  className={`badge ${actionStatusFilter === st ? 'badge-primary' : 'badge-outline'}`}
                  style={{ cursor: 'pointer', padding: '4px 8px', fontSize: 'var(--text-caption)' }}
                >
                  {st}
                </button>
              ))}
            </div>

            <span className="text-caption font-mono text-muted">{filteredActions.length} proposals</span>
          </div>

          {/* Action Cards List */}
          {filteredActions.length > 0 ? (
            <div className="stack">
              {filteredActions.map((act) => {
                const isUnderReview = reviewingActionId === act.id
                const isSuggested = act.status === 'SUGGESTED'

                return (
                  <div key={act.id} className="ai-action-card">
                    <div className="ai-action-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <span className="badge badge-outline font-mono text-caption">
                          {act.action_type || 'PROPOSAL'}
                        </span>
                        <h3 className="section-title" style={{ margin: 0 }}>
                          {act.title}
                        </h3>
                        <StatusChip status={act.status || 'SUGGESTED'} size="sm" />
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                        {act.confidence_score != null && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
                            <span className="text-caption text-muted">Confidence:</span>
                            <ConfidenceMeter confidence={act.confidence_score} />
                          </div>
                        )}
                        {act.risk_score && <SeverityChip severity={act.risk_score} size="sm" />}
                      </div>
                    </div>

                    <p className="text-body text-secondary" style={{ margin: 0 }}>
                      {act.description}
                    </p>

                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-4)',
                        flexWrap: 'wrap',
                      }}
                    >
                      <span className="text-caption font-mono text-muted">
                        Target: {act.target_entity_type || 'ENTITY'} #{act.target_entity_id || '—'}
                      </span>
                      <span className="text-caption font-mono text-muted">
                        Proposed: {act.created_at ? dateTime(act.created_at, timezone) : '—'}
                      </span>
                      {act.approval_note && (
                        <span className="text-caption text-secondary">
                          Reviewer Note: <em>&ldquo;{act.approval_note}&rdquo;</em>
                        </span>
                      )}
                    </div>

                    {/* Review Form (E16) */}
                    {isSuggested && canWrite && (
                      <div
                        style={{
                          marginTop: 'var(--space-2)',
                          borderTop: '1px solid var(--color-border)',
                          paddingTop: 'var(--space-3)',
                        }}
                      >
                        {!isUnderReview ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setReviewingActionId(act.id)
                              setReviewNote('')
                              setReviewError('')
                            }}
                          >
                            Review Proposal
                          </Button>
                        ) : (
                          <div className="stack-sm">
                            <Field
                              label="Review Decision Note (3 to 1000 characters required)"
                              htmlFor={`note-${act.id}`}
                              hint="Auditable justification required by autonomous governance policy."
                              required
                            >
                              <Textarea
                                id={`note-${act.id}`}
                                rows={2}
                                placeholder="State justification for approval or rejection..."
                                value={reviewNote}
                                onChange={(e) => setReviewNote(e.target.value)}
                                maxLength={1000}
                              />
                            </Field>

                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'flex-end',
                                gap: 'var(--space-2)',
                              }}
                            >
                              <Button variant="ghost" size="sm" onClick={() => setReviewingActionId(null)}>
                                Cancel
                              </Button>

                              <Button
                                variant="danger"
                                size="sm"
                                icon={X}
                                loading={reviewBusy}
                                disabled={reviewNote.trim().length < 3 || reviewBusy}
                                onClick={() => handleExecuteReview(act.id, 'REJECTED')}
                              >
                                Reject
                              </Button>

                              <Button
                                variant="primary"
                                size="sm"
                                icon={Check}
                                loading={reviewBusy}
                                disabled={reviewNote.trim().length < 3 || reviewBusy}
                                onClick={() => handleExecuteReview(act.id, 'APPROVED')}
                              >
                                Approve (Simulated)
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <EmptyState
              title="No action proposals"
              description="No automated action proposals are currently pending or recorded."
            />
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 3: AUDIT TRAIL                                             */}
      {/* ============================================================== */}
      {activeTab === 'audit' && (
        <UnavailableState
          owner="AI Intelligence"
          reason="AI audit log event stream is unmounted; no read route exists."
        />
      )}
    </div>
  )
}
