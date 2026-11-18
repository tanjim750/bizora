'use client'

import React, { useState, useMemo } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  Shield,
  Key,
  Link2,
  AlertTriangle,
  GitMerge,
  History,
  Activity,
  RefreshCw,
  Play,
  RotateCcw,
  CheckCircle2,
  XCircle,
  FileText,
  Lock,
  Layers,
  Settings,
  Database,
  ExternalLink,
  Info,
  Check,
  X,
  Server,
  Zap,
} from 'lucide-react'
import {
  DataTable,
  StatusChip,
  SeverityChip,
  EmptyState,
  UnavailableState,
  SimulatedBadge,
  Button,
  Dialog,
  Drawer,
  Input,
  Field,
  Select,
  Textarea,
  KpiTile,
  PageHeader,
  Tabs,
  CopyableCode,
  ConfirmDialog,
  Banner,
  Tooltip,
} from './ui'
import { dateTime, relativeTime } from '../lib/format/index.js'
import { clientApi, newIdempotencyKey } from '../lib/clientApi'
import { operationBody, describeAttempt, operationErrorText } from '../lib/observability/operations'
import DialyraTelephony from './DialyraTelephony'
import KnowledgeBase from './KnowledgeBase'
import SimulationSandbox from './SimulationSandbox'
import { FailedRecordsList, WebhooksList } from './IntegrationRecordLists'
import TrackingIntegration from './TrackingIntegration'
import ConfigViewNav from './ConfigViewNav'
import ConfigSectionsEditor from './ConfigSectionsEditor'
import ConfigRulesPolicies from './ConfigRulesPolicies'
import ConfigHistory from './ConfigHistory'
import ConfigConnections from './ConfigConnections'

const CONFIG_VIEWS = [
  { key: 'effective', label: 'Effective settings' },
  { key: 'sections', label: 'Edit settings' },
  { key: 'rules', label: 'Rules & policies' },
  { key: 'connections', label: 'Connections' },
  { key: 'history', label: 'Change history' },
]

export default function Admin({
  businessId,
  business,
  currentTab = 'identity',
  initialCanonical = [],
  initialExternal = [],
  initialLinks = [],
  initialConflicts = [],
  initialMergeCandidates = [],
  initialHistory = [],
  initialObservabilitySummary = null,
  initialConnections = [],
  initialConfiguration = null,
}) {
  const router = useRouter()

  // Sub-tabs for Identity
  const [identitySubTab, setIdentitySubTab] = useState('canonical')

  // Sub-tabs for Integrations
  const [integrationsSubTab, setIntegrationsSubTab] = useState('connections')

  // Configuration section selector
  const [configSection, setConfigSection] = useState('profile')
  const [show409Banner, setShow409Banner] = useState(false)
  const [configView, setConfigView] = useState('effective')

  // Merge Dry-Run Plan Card (D24)
  const [dryRunPlan, setDryRunPlan] = useState(null)
  const [isDryRunLoading, setIsDryRunLoading] = useState(false)
  const [dryRunError, setDryRunError] = useState(null)

  // Review Merge Dialog (D14)
  const [selectedMergeCandidate, setSelectedMergeCandidate] = useState(null)
  const [mergeReviewDecision, setMergeReviewDecision] = useState('APPROVED')
  const [mergeReviewReason, setMergeReviewReason] = useState('')
  const [isReviewingMerge, setIsReviewingMerge] = useState(false)

  // Review Conflict Dialog (D14)
  const [selectedConflict, setSelectedConflict] = useState(null)
  const [identityReviewError, setIdentityReviewError] = useState('')
  const [conflictReviewStatus, setConflictReviewStatus] = useState('RESOLVED')
  const [conflictReviewReason, setConflictReviewReason] = useState('')
  const [isReviewingConflict, setIsReviewingConflict] = useState(false)

  // Connection Test Operation
  const [testingConnectionId, setTestingConnectionId] = useState(null)
  const [operationResult, setOperationResult] = useState(null)

  // Sync Retry Confirm
  const [selectedSyncId, setSelectedSyncId] = useState(null)
  const [isRetryingSync, setIsRetryingSync] = useState(false)

  // Admin Workspaces Tabs
  const adminTabs = [
    { key: 'identity', label: 'Identity Resolution', href: `/business/${businessId}/admin/identity` },
    { key: 'integrations', label: 'Integrations & Sync', href: `/business/${businessId}/admin/integrations` },
    {
      key: 'configuration',
      label: 'Configuration & Policies',
      href: `/business/${businessId}/admin/configuration`,
    },
    { key: 'knowledge', label: 'Knowledge Base', href: `/business/${businessId}/admin/knowledge` },
    { key: 'simulation', label: 'Simulation & Sandbox', href: `/business/${businessId}/admin/simulation` },
  ]

  // Execute D24 Merge Dry-Run
  const handleRunMergeDryRun = async (candidateId) => {
    setIsDryRunLoading(true)
    setDryRunPlan(null)
    setDryRunError(null)

    try {
      const res = await clientApi(
        `businesses/${businessId}/identity/merge-candidates/${candidateId}/dry-run`,
        {
          method: 'POST',
          body: {},
        },
      )
      setDryRunPlan(res)
    } catch (err) {
      setDryRunPlan(null)
      setDryRunError(err.message || 'Merge planner unavailable. Please try again.')
    } finally {
      setIsDryRunLoading(false)
    }
  }

  // Handle Review Conflict (D14)
  const handleSubmitConflictReview = async (e) => {
    e.preventDefault()
    setIdentityReviewError('')
    setIsReviewingConflict(true)

    try {
      await clientApi(`businesses/${businessId}/identity/review-conflict`, {
        method: 'POST',
        body: {
          conflict_id: selectedConflict.id,
          decision: conflictReviewStatus,
          reason: conflictReviewReason,
        },
      })
      setSelectedConflict(null)
      router.refresh()
    } catch (err) {
      setIdentityReviewError(err.message || 'Conflict review failed. Please try again.')
    } finally {
      setIsReviewingConflict(false)
    }
  }

  // Handle Review Merge (D14)
  const handleSubmitMergeReview = async (e) => {
    e.preventDefault()
    setIdentityReviewError('')
    setIsReviewingMerge(true)

    try {
      await clientApi(`businesses/${businessId}/identity/review-merge`, {
        method: 'POST',
        body: {
          candidate_id: selectedMergeCandidate.id,
          decision: mergeReviewDecision,
          reason: mergeReviewReason,
        },
      })
      setSelectedMergeCandidate(null)
      router.refresh()
    } catch (err) {
      setIdentityReviewError(err.message || 'Merge review failed. Please try again.')
    } finally {
      setIsReviewingMerge(false)
    }
  }

  // Handle Connection Test (Attempt recorded — Succeeded / Attempt recorded — Failed)
  const handleTestConnection = async (connId) => {
    setTestingConnectionId(connId)
    setOperationResult(null)

    try {
      const res = await clientApi(`businesses/${businessId}/observability/connections/${connId}/test`, {
        method: 'POST',
        body: operationBody(newIdempotencyKey()),
      })
      const outcome = describeAttempt('connection_test', res)
      setOperationResult({
        connId,
        status: outcome.text,
        tone: outcome.tone,
      })
    } catch (err) {
      setOperationResult({
        connId,
        status: operationErrorText(err),
        tone: 'danger',
      })
    } finally {
      setTestingConnectionId(null)
    }
  }

  // Handle Sync Retry
  const handleRetrySync = async () => {
    if (!selectedSyncId) return
    setIsRetryingSync(true)

    try {
      const res = await clientApi(`businesses/${businessId}/observability/syncs/${selectedSyncId}/retry`, {
        method: 'POST',
        body: operationBody(newIdempotencyKey()),
      })
      const outcome = describeAttempt('sync_retry', res)
      setOperationResult({
        connId: selectedSyncId,
        status: outcome.text,
        tone: outcome.tone,
      })
    } catch (err) {
      setOperationResult({
        connId: selectedSyncId,
        status: operationErrorText(err),
        tone: 'danger',
      })
    } finally {
      setIsRetryingSync(false)
      setSelectedSyncId(null)
    }
  }

  // Effective Configuration Data
  const effectiveSections = initialConfiguration?.sections || null

  return (
    <div className="workspace-page">
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspace' },
          { label: business?.name || 'Workspace', href: `/business/${businessId}/overview` },
          { label: 'Admin' },
        ]}
        title="Administration & Controls"
        description="Entity identity resolution, integration sync status, business governance rules, and system configuration."
        badge="Restricted · Manager Access"
      />

      <Tabs tabs={adminTabs} activeKey={currentTab} className="workspace-tabs" />

      {/* =========================================================================
          TAB 1: IDENTITY RESOLUTION
          ========================================================================= */}
      {currentTab === 'identity' && (
        <div className="stack section-gap">
          {/* Identity Sub-navigation */}
          <div className="admin-subnav">
            <button
              type="button"
              className={`admin-subnav-btn ${identitySubTab === 'canonical' ? 'is-active' : ''}`}
              onClick={() => setIdentitySubTab('canonical')}
            >
              Canonical ({initialCanonical.length})
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${identitySubTab === 'external' ? 'is-active' : ''}`}
              onClick={() => setIdentitySubTab('external')}
            >
              External ({initialExternal.length})
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${identitySubTab === 'links' ? 'is-active' : ''}`}
              onClick={() => setIdentitySubTab('links')}
            >
              Links ({initialLinks.length})
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${identitySubTab === 'conflicts' ? 'is-active' : ''}`}
              onClick={() => setIdentitySubTab('conflicts')}
            >
              Conflicts ({initialConflicts.length})
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${identitySubTab === 'merge-candidates' ? 'is-active' : ''}`}
              onClick={() => setIdentitySubTab('merge-candidates')}
            >
              Merge Candidates ({initialMergeCandidates.length})
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${identitySubTab === 'history' ? 'is-active' : ''}`}
              onClick={() => setIdentitySubTab('history')}
            >
              Audit History ({initialHistory.length})
            </button>
          </div>

          {dryRunError && <Banner variant="danger">{dryRunError}</Banner>}

          {/* D24 Merge Dry-Run Plan Card Display */}
          {dryRunPlan && (
            <div className="merge-dryrun-card stack-sm">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 'var(--space-2)',
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  <GitMerge size={16} className="text-primary" />
                  <span className="font-semibold text-body">
                    Merge Dry-Run Plan (D24): {dryRunPlan.plan_id}
                  </span>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setDryRunPlan(null)}>
                  Close Plan
                </Button>
              </div>

              <div className="grid-kpi mt-2">
                <KpiTile
                  title="Execution Status"
                  value={dryRunPlan.execution}
                  subtext={dryRunPlan.execution_reason}
                />
                <KpiTile title="Readiness" value={dryRunPlan.readiness} subtext="Adapter contract state" />
                <KpiTile
                  title="Dependencies"
                  value={String(dryRunPlan.dependencies?.length || 7)}
                  subtext="Owner services required"
                />
              </div>

              <div className="mt-2">
                <span className="text-caption text-secondary font-semibold">Plan Fingerprint:</span>
                <CopyableCode value={dryRunPlan.fingerprint} label="Fingerprint" className="mt-1" />
              </div>

              {/* Acknowledgements List */}
              {dryRunPlan.acknowledgements && (
                <div className="mt-2">
                  <span className="text-caption text-secondary font-semibold">Owner Acknowledgements:</span>
                  <ul className="stack-sm mt-1" style={{ listStyle: 'none', padding: 0 }}>
                    {dryRunPlan.acknowledgements.map((ack, idx) => (
                      <li
                        key={idx}
                        className="journey-card"
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                      >
                        <span className="font-medium text-caption">{ack.owner}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <StatusChip status={ack.status} size="sm" />
                          <span className="text-caption text-secondary">{ack.reason}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Permanently Disabled Execute Merge Button */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  marginTop: 'var(--space-3)',
                }}
              >
                <Tooltip content="Blocked by design. Consolidation across domain boundaries requires manual operator review.">
                  <Button variant="danger" size="sm" icon={Lock} disabled>
                    Execute Merge
                  </Button>
                </Tooltip>
                <span className="text-caption text-muted font-mono">Blocked by design.</span>
              </div>
            </div>
          )}

          {/* Sub-view 1: Canonical */}
          {identitySubTab === 'canonical' && (
            <DataTable
              rows={initialCanonical}
              columns={[
                {
                  key: 'canonical_key',
                  label: 'Canonical Identity Key',
                  render: (row) => <CopyableCode value={row.canonical_key} label="Canonical Key" />,
                },
                {
                  key: 'entity_type',
                  label: 'Entity Type',
                  render: (row) => <StatusChip status={row.entity_type} size="sm" />,
                },
                {
                  key: 'entity_id',
                  label: 'Internal Entity ID',
                  render: (row) => <span className="font-mono text-body">#{row.entity_id}</span>,
                },
                {
                  key: 'status',
                  label: 'Status',
                  render: (row) => <StatusChip status={row.status} size="sm" />,
                },
                {
                  key: 'created_at',
                  label: 'Created',
                  priority: 'low',
                  className: 'table-col-priority-low',
                  render: (row) => (
                    <span className="text-caption text-secondary">{dateTime(row.created_at)}</span>
                  ),
                },
              ]}
            />
          )}

          {/* Sub-view 2: External */}
          {identitySubTab === 'external' && (
            <DataTable
              rows={initialExternal}
              columns={[
                {
                  key: 'external_id',
                  label: 'External Identifier',
                  render: (row) => <CopyableCode value={row.external_id} label="External ID" />,
                },
                {
                  key: 'provider',
                  label: 'Provider',
                  render: (row) => <span className="font-mono text-caption">{row.provider}</span>,
                },
                {
                  key: 'identity_type',
                  label: 'Identity Type',
                  render: (row) => <StatusChip status={row.identity_type} size="sm" />,
                },
                {
                  key: 'identity_value',
                  label: 'Identity Value',
                  priority: 'low',
                  className: 'table-col-priority-low',
                  render: (row) => <span className="font-mono text-body">{row.identity_value}</span>,
                },
                {
                  key: 'last_seen_at',
                  label: 'Last Seen',
                  render: (row) => <span className="text-caption">{dateTime(row.last_seen_at)}</span>,
                },
              ]}
            />
          )}

          {/* Sub-view 3: Links */}
          {identitySubTab === 'links' && (
            <DataTable
              rows={initialLinks}
              columns={[
                {
                  key: 'canonical_identity',
                  label: 'Canonical ID',
                  render: (row) => <span className="font-mono">#{row.canonical_identity}</span>,
                },
                {
                  key: 'external_identity',
                  label: 'External ID',
                  render: (row) => <span className="font-mono">#{row.external_identity}</span>,
                },
                {
                  key: 'match_type',
                  label: 'Match Type',
                  render: (row) => <StatusChip status={row.match_type} size="sm" />,
                },
                {
                  key: 'confidence',
                  label: 'Confidence',
                  align: 'right',
                  render: (row) => (
                    <span className="font-mono font-semibold">
                      {Math.round((row.confidence || 0) * 100)}%
                    </span>
                  ),
                },
                {
                  key: 'rule_key',
                  label: 'Rule Key',
                  priority: 'low',
                  className: 'table-col-priority-low',
                  render: (row) => (
                    <span className="font-mono text-caption text-secondary">{row.rule_key}</span>
                  ),
                },
                {
                  key: 'status',
                  label: 'Status',
                  render: (row) => <StatusChip status={row.status} size="sm" />,
                },
              ]}
            />
          )}

          {/* Sub-view 4: Conflicts */}
          {identitySubTab === 'conflicts' && (
            <div>
              {initialConflicts.length === 0 ? (
                <EmptyState
                  title="No identity conflicts"
                  description="No identity conflicts require review."
                />
              ) : (
                <DataTable
                  rows={initialConflicts}
                  columns={[
                    {
                      key: 'conflict_type',
                      label: 'Conflict Type',
                      render: (row) => <StatusChip status={row.conflict_type} size="sm" />,
                    },
                    {
                      key: 'description',
                      label: 'Description',
                      render: (row) => (
                        <span className="font-mono text-caption">{row.description || '—'}</span>
                      ),
                    },
                    {
                      key: 'status',
                      label: 'Status',
                      render: (row) => <StatusChip status={row.status} size="sm" />,
                    },
                    {
                      key: 'actions',
                      label: '',
                      align: 'right',
                      render: (row) => (
                        <Button variant="outline" size="sm" onClick={() => setSelectedConflict(row)}>
                          Review Conflict
                        </Button>
                      ),
                    },
                  ]}
                />
              )}
            </div>
          )}

          {/* Sub-view 5: Merge Candidates */}
          {identitySubTab === 'merge-candidates' && (
            <div>
              {initialMergeCandidates.length === 0 ? (
                <EmptyState
                  title="No merge candidates"
                  description="No duplicate identities have been queued for merge consolidation."
                />
              ) : (
                <DataTable
                  rows={initialMergeCandidates}
                  columns={[
                    {
                      key: 'candidate_identity',
                      label: 'Source Identity',
                      render: (row) => <span className="font-mono">#{row.candidate_identity}</span>,
                    },
                    {
                      key: 'primary_identity',
                      label: 'Target Identity',
                      render: (row) => <span className="font-mono">#{row.primary_identity}</span>,
                    },
                    {
                      key: 'confidence',
                      label: 'Confidence',
                      align: 'right',
                      render: (row) => (
                        <span className="font-mono font-semibold">
                          {Math.round((row.confidence || 0) * 100)}%
                        </span>
                      ),
                    },
                    {
                      key: 'status',
                      label: 'Status',
                      render: (row) => <StatusChip status={row.status} size="sm" />,
                    },
                    {
                      key: 'actions',
                      label: '',
                      align: 'right',
                      render: (row) => (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <Button
                            variant="outline"
                            size="sm"
                            loading={isDryRunLoading}
                            onClick={() => handleRunMergeDryRun(row.id)}
                          >
                            Dry-Run Plan
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setSelectedMergeCandidate(row)}
                          >
                            Review
                          </Button>
                        </div>
                      ),
                    },
                  ]}
                />
              )}
            </div>
          )}

          {/* Sub-view 6: History */}
          {identitySubTab === 'history' && (
            <DataTable
              rows={initialHistory}
              columns={[
                {
                  key: 'action',
                  label: 'Resolution Action',
                  render: (row) => <StatusChip status={row.action} size="sm" />,
                },
                {
                  key: 'rule_key',
                  label: 'Rule Key',
                  render: (row) => <span className="font-mono text-caption">{row.rule_key}</span>,
                },
                {
                  key: 'actor',
                  label: 'Actor',
                  render: (row) => (
                    <span className="text-caption font-mono">
                      {row.actor ? `User #${row.actor}` : 'SYSTEM'}
                    </span>
                  ),
                },
                {
                  key: 'created_at',
                  label: 'Timestamp',
                  render: (row) => (
                    <span className="text-caption font-semibold">{dateTime(row.created_at)}</span>
                  ),
                },
              ]}
            />
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 2: INTEGRATIONS & SYNC
          ========================================================================= */}
      {currentTab === 'integrations' && (
        <div className="stack section-gap">
          {/* Health Summary Band */}
          <div className="grid-kpi">
            <KpiTile
              title="Integration Health"
              value={initialObservabilitySummary?.status || 'UNKNOWN'}
              subtext={`As of ${dateTime(initialObservabilitySummary?.as_of || new Date())}`}
              icon={Activity}
            />
            <KpiTile
              title="Connected Adapters"
              value={String(initialObservabilitySummary?.connection_count || initialConnections.length)}
              subtext="Authorized data providers"
              icon={Server}
            />
            <KpiTile
              title="Active Error Groups"
              value={String(initialObservabilitySummary?.active_error_groups || 0)}
              subtext="Aggregated ingestion issues"
              icon={AlertTriangle}
            />
            <KpiTile
              title="Failed Webhooks"
              value={String(initialObservabilitySummary?.failed_webhooks || 0)}
              subtext="Replayable inbound hooks"
              icon={Zap}
            />
          </div>

          {operationResult && (
            <Banner
              variant={
                ['info', 'success', 'warning', 'danger'].includes(operationResult.tone)
                  ? operationResult.tone
                  : 'info'
              }
            >
              <span>{operationResult.status}</span>
            </Banner>
          )}

          {/* Integrations Sub-navigation */}
          <div className="admin-subnav">
            <button
              type="button"
              className={`admin-subnav-btn ${integrationsSubTab === 'connections' ? 'is-active' : ''}`}
              onClick={() => setIntegrationsSubTab('connections')}
            >
              Connections ({initialConnections.length})
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${integrationsSubTab === 'syncs' ? 'is-active' : ''}`}
              onClick={() => setIntegrationsSubTab('syncs')}
            >
              Sync Operations
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${integrationsSubTab === 'failed-records' ? 'is-active' : ''}`}
              onClick={() => setIntegrationsSubTab('failed-records')}
            >
              Failed Records
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${integrationsSubTab === 'webhooks' ? 'is-active' : ''}`}
              onClick={() => setIntegrationsSubTab('webhooks')}
            >
              Inbound Webhooks
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${integrationsSubTab === 'dialyra' ? 'is-active' : ''}`}
              onClick={() => setIntegrationsSubTab('dialyra')}
            >
              Dialyra Telephony & SIP
            </button>
            <button
              type="button"
              className={`admin-subnav-btn ${integrationsSubTab === 'tracking' ? 'is-active' : ''}`}
              onClick={() => setIntegrationsSubTab('tracking')}
            >
              Tracking
            </button>
          </div>

          {/* Sub-view: Connections */}
          {integrationsSubTab === 'connections' && (
            <DataTable
              rows={initialConnections}
              columns={[
                {
                  key: 'provider',
                  label: 'Provider Adapter',
                  render: (row) => (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span className="font-semibold text-body">{row.provider}</span>
                      {row.is_mock && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
                          <SimulatedBadge size="sm" />
                          <span className="text-caption text-secondary">Mock connection</span>
                        </div>
                      )}
                    </div>
                  ),
                },
                {
                  key: 'lifecycle_status',
                  label: 'Lifecycle',
                  render: (row) => <StatusChip status={row.lifecycle_status} size="sm" />,
                },
                {
                  key: 'health',
                  label: 'Health',
                  render: (row) => (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <StatusChip status={row.health?.status || 'UNKNOWN'} size="sm" />
                      <span className="text-caption text-secondary">
                        {row.health?.reason || 'No observations'}
                      </span>
                    </div>
                  ),
                },
                {
                  key: 'actions',
                  label: '',
                  align: 'right',
                  render: (row) => (
                    <Button
                      variant="outline"
                      size="sm"
                      loading={testingConnectionId === row.id}
                      onClick={() => handleTestConnection(row.id)}
                    >
                      Test Connection
                    </Button>
                  ),
                },
              ]}
            />
          )}

          {/* Sub-view: Syncs */}
          {integrationsSubTab === 'syncs' && (
            <div className="stack-sm">
              <DataTable
                rows={[
                  {
                    id: 1,
                    provider: 'Simulated commerce',
                    resource: 'products',
                    status: 'COMPLETED',
                    items_synced: 42,
                    started_at: '2026-11-10T13:36:46Z',
                  },
                ]}
                columns={[
                  {
                    key: 'provider',
                    label: 'Provider',
                    render: (row) => <span className="font-semibold">{row.provider}</span>,
                  },
                  {
                    key: 'resource',
                    label: 'Resource',
                    render: (row) => <span className="font-mono">{row.resource}</span>,
                  },
                  {
                    key: 'status',
                    label: 'Sync Status',
                    render: (row) => <StatusChip status={row.status} size="sm" />,
                  },
                  {
                    key: 'items_synced',
                    label: 'Items Synced',
                    align: 'right',
                    render: (row) => <span className="font-mono">{row.items_synced}</span>,
                  },
                  {
                    key: 'started_at',
                    label: 'Started At',
                    render: (row) => <span className="text-caption">{dateTime(row.started_at)}</span>,
                  },
                  {
                    key: 'actions',
                    label: '',
                    align: 'right',
                    render: (row) => (
                      <Button variant="outline" size="sm" onClick={() => setSelectedSyncId(row.id)}>
                        Retry Sync
                      </Button>
                    ),
                  },
                ]}
              />
            </div>
          )}

          {/* Sub-view: Failed Records */}
          {integrationsSubTab === 'failed-records' && (
            <FailedRecordsList businessId={businessId} role={business?.role} timezone={business?.timezone} />
          )}

          {/* Sub-view: Inbound Webhooks */}
          {integrationsSubTab === 'webhooks' && (
            <WebhooksList businessId={businessId} role={business?.role} timezone={business?.timezone} />
          )}

          {/* Sub-view: Dialyra Telephony & SIP Trunks */}
          {integrationsSubTab === 'dialyra' && <DialyraTelephony businessId={businessId} />}
          {integrationsSubTab === 'tracking' && (
            <TrackingIntegration businessId={businessId} role={business?.role} />
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 3: CONFIGURATION & POLICIES
          ========================================================================= */}
      {currentTab === 'configuration' && configView === 'effective' && effectiveSections && (
        <div className="stack section-gap">
          <ConfigViewNav views={CONFIG_VIEWS} value={configView} onChange={setConfigView} />
          {/* Version chip & 409 stale banner toggle */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 'var(--space-2)',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <span className="font-semibold text-body">Active Business Configuration</span>
              <span
                className="font-mono text-caption text-secondary"
                style={{
                  background: 'var(--color-surface-subtle)',
                  border: '1px solid var(--color-border)',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                {configSection.toUpperCase()} version: v{effectiveSections[configSection]?.version ?? 0}
              </span>
            </div>

            <Button variant="ghost" size="sm" onClick={() => setShow409Banner(!show409Banner)}>
              {show409Banner ? 'Dismiss 409 Notice' : 'Preview 409 Concurrency Banner'}
            </Button>
          </div>

          {show409Banner && (
            <Banner variant="warning">
              <span>Someone else changed this configuration. Reload to continue.</span>
            </Banner>
          )}

          {/* Section Switcher */}
          <div className="admin-subnav">
            {['profile', 'general', 'ai', 'rules'].map((sec) => (
              <button
                key={sec}
                type="button"
                className={`admin-subnav-btn ${configSection === sec ? 'is-active' : ''}`}
                onClick={() => setConfigSection(sec)}
              >
                {sec.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Effective Settings Structured Key-Value Grid (Structured UI, zero raw JSON) */}
          <div className="journey-card stack-sm">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: 'var(--space-2)',
                borderBottom: '1px solid var(--color-border)',
                flexWrap: 'wrap',
                gap: 'var(--space-2)',
              }}
            >
              <span className="font-semibold text-body">
                Effective Settings: {configSection.toUpperCase()}
              </span>
              <span className="text-caption text-secondary">Authoritative System Configuration</span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: 'var(--space-3)',
                marginTop: 'var(--space-2)',
              }}
            >
              {Object.entries(effectiveSections[configSection]?.settings || {}).map(([key, val]) => (
                <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <span className="text-caption font-semibold text-secondary">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </span>
                  <span className="font-mono text-body">
                    {val === null || val === undefined || val === ''
                      ? '—'
                      : typeof val === 'object'
                        ? Array.isArray(val)
                          ? val.join(', ') || '—'
                          : Object.entries(val)
                              .map(([k, v]) => `${k}: ${v}`)
                              .join('; ') || '—'
                        : String(val)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {currentTab === 'configuration' && configView === 'effective' && !effectiveSections && (
        <div className="stack section-gap">
          <ConfigViewNav views={CONFIG_VIEWS} value={configView} onChange={setConfigView} />
          <UnavailableState
            title="Configuration unavailable"
            owner="Business Configuration"
            reason="The configuration service could not be loaded. Reload to try again."
          />
        </div>
      )}

      {currentTab === 'configuration' && configView !== 'effective' && (
        <div className="stack section-gap">
          <ConfigViewNav views={CONFIG_VIEWS} value={configView} onChange={setConfigView} />
          {configView === 'sections' && (
            <ConfigSectionsEditor
              businessId={businessId}
              role={business?.role}
              timezone={business?.timezone}
            />
          )}
          {configView === 'rules' && (
            <ConfigRulesPolicies
              businessId={businessId}
              role={business?.role}
              timezone={business?.timezone}
            />
          )}
          {configView === 'connections' && (
            <ConfigConnections businessId={businessId} role={business?.role} timezone={business?.timezone} />
          )}
          {configView === 'history' && (
            <ConfigHistory businessId={businessId} timezone={business?.timezone} />
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 4: KNOWLEDGE BASE (READ ONLY)
          ========================================================================= */}
      {currentTab === 'knowledge' && (
        <KnowledgeBase
          businessId={businessId}
          timezone={business?.timezone}
          title="Memory & Knowledge Base"
        />
      )}

      {/* =========================================================================
          TAB 5: SIMULATION & SANDBOX (READ ONLY)
          ========================================================================= */}
      {currentTab === 'simulation' && (
        <SimulationSandbox connections={initialConnections} title="Prototype Simulation & Sandbox" />
      )}

      {/* =========================================================================
          REVIEW CONFLICT DIALOG (D14)
          ========================================================================= */}
      {selectedConflict && (
        <Dialog
          isOpen={true}
          onClose={() => {
            setSelectedConflict(null)
            setIdentityReviewError('')
          }}
          title={`Review Identity Conflict #${selectedConflict.id}`}
          confirmLabel="Submit Resolution"
          onConfirm={handleSubmitConflictReview}
          isLoading={isReviewingConflict}
        >
          <form onSubmit={handleSubmitConflictReview} className="stack-sm">
            {identityReviewError && <Banner variant="danger">{identityReviewError}</Banner>}
            <Field label="Resolution Action" required htmlFor="conflict-review-status">
              <Select
                id="conflict-review-status"
                aria-label="Resolution Action"
                value={conflictReviewStatus}
                onChange={(e) => setConflictReviewStatus(e.target.value)}
              >
                <option value="REVIEWING">REVIEWING (Mark In Progress)</option>
                <option value="RESOLVED">RESOLVED (Confirm Resolution)</option>
                <option value="IGNORED">IGNORED (Acknowledge and Dismiss)</option>
              </Select>
            </Field>

            <Field label="Resolution Reason & Audit Note" required htmlFor="conflict-review-reason">
              <Textarea
                id="conflict-review-reason"
                aria-label="Resolution Reason"
                placeholder="Explain the identity verification finding..."
                value={conflictReviewReason}
                onChange={(e) => setConflictReviewReason(e.target.value)}
                required
                rows={3}
              />
            </Field>
            <button type="submit" style={{ display: 'none' }} aria-hidden="true" />
          </form>
        </Dialog>
      )}

      {/* =========================================================================
          REVIEW MERGE CANDIDATE DIALOG (D14)
          ========================================================================= */}
      {selectedMergeCandidate && (
        <Dialog
          isOpen={true}
          onClose={() => {
            setSelectedMergeCandidate(null)
            setIdentityReviewError('')
          }}
          title={`Review Merge Candidate #${selectedMergeCandidate.id}`}
          confirmLabel="Record Decision"
          onConfirm={handleSubmitMergeReview}
          isLoading={isReviewingMerge}
        >
          <form onSubmit={handleSubmitMergeReview} className="stack-sm">
            {identityReviewError && <Banner variant="danger">{identityReviewError}</Banner>}
            <Field label="Review Decision" required htmlFor="merge-review-decision">
              <Select
                id="merge-review-decision"
                aria-label="Review Decision"
                value={mergeReviewDecision}
                onChange={(e) => setMergeReviewDecision(e.target.value)}
              >
                <option value="APPROVED">APPROVED (Authorize Consolidation Plan)</option>
                <option value="REJECTED">REJECTED (Reject Identity Merge)</option>
              </Select>
            </Field>

            <Field label="Manager Decision Reason" required htmlFor="merge-review-reason">
              <Textarea
                id="merge-review-reason"
                aria-label="Manager Decision Reason"
                placeholder="Explain the merge authorization rationale..."
                value={mergeReviewReason}
                onChange={(e) => setMergeReviewReason(e.target.value)}
                required
                rows={3}
              />
            </Field>
            <button type="submit" style={{ display: 'none' }} aria-hidden="true" />
          </form>
        </Dialog>
      )}

      {/* =========================================================================
          CONFIRM SYNC RETRY DIALOG
          ========================================================================= */}
      <ConfirmDialog
        isOpen={Boolean(selectedSyncId)}
        onClose={() => setSelectedSyncId(null)}
        title="Confirm Sync Operation Retry"
        message="Are you sure you want to trigger a manual retry for this integration sync? Inbound records will be queued for reprocessing."
        confirmLabel="Retry Sync"
        onConfirm={handleRetrySync}
        isLoading={isRetryingSync}
      />
    </div>
  )
}
