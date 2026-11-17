'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  FileText,
  Share2,
  BarChart2,
  Layers,
  AlertTriangle,
  CheckCircle2,
  Shield,
  User,
  ShoppingBag,
  Package,
  Search,
  ExternalLink,
  Info,
  Sparkles,
  ArrowRight,
  Database,
  Eye,
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
  Drawer,
  Input,
  Field,
  Select,
  Checkbox,
  EvidencePanel,
  Banner,
  Tabs,
} from '@/components/ui'
import { dateTime, relativeTime } from '@/lib/format'
import { clientApi } from '@/lib/clientApi'
import { metricsPath, snapshotsPath, normalizeList } from '@/lib/intelligence/metrics'
import {
  PIPELINE_RUN_PATH,
  GRAPH_REBUILD_PATH,
  rebuildBody,
  summarizePipelineResult,
  summarizeRebuildResult,
  isManager,
} from '@/lib/intelligence/pipeline'
import {
  FACTS_PATH,
  ISSUES_PATH,
  issuePatchPath,
  issuePatchBody,
  confidencePercent,
} from '@/lib/intelligence/facts'
import {
  ENTITY_KINDS,
  REBUILD_BODY,
  traversalPath,
  buildGraphView,
  graphErrorKind,
  journeyPath,
  buildJourneyView,
} from '@/lib/intelligence/graph'

// Sample data for demo mode (SIMULATED)
const SAMPLE_FACTS = [
  {
    id: 'f-101',
    category: 'REVENUE',
    statement:
      'Gross sales volume reached BDT 248,500.00 across 182 verified orders during the 30-day rolling window.',
    confidence: 96,
    source: 'Authoritative Commerce Ledger',
    rule_key: 'bi.revenue.rolling_30d.gross',
  },
  {
    id: 'f-102',
    category: 'FULFILLMENT',
    statement:
      'Standard delivery completion rate is 97.4% with an average carrier dispatch interval of 4.2 hours.',
    confidence: 91,
    source: 'Carrier Dispatch Telemetry',
    rule_key: 'bi.delivery.sla_fulfillment_rate',
  },
  {
    id: 'f-103',
    category: 'CUSTOMER',
    statement:
      'Repeat purchase frequency for active customers stands at 1.48 orders per buyer within 90 days.',
    confidence: 88,
    source: 'Deterministic Identity Graph',
    rule_key: 'bi.customer.repeat_rate.90d',
  },
]

const SAMPLE_ISSUES = [
  {
    id: 'iss-sim-1',
    title: 'High Courier Exception Rate on RedX Outbound Shipments',
    severity: 'HIGH',
    rule_key: 'anom.delivery.failure_rate.high',
    status: 'OPEN',
    detected_at: new Date(Date.now() - 3600000 * 4).toISOString(),
    affected_entity: 'Shipments Courier #2',
    evidence: [
      {
        text: 'Courier returned 4 delivery failures in the last 2 hours (threshold: >= 2).',
        source: 'RedX Integration Log',
      },
      {
        text: 'Delivery address validation succeeded, indicating routing failure on carrier side.',
        source: 'Address Validation Service',
      },
    ],
  },
]

export default function Intelligence({
  business = {},
  businessId,
  activeTab = 'facts',
  factsData = null,
  issuesData = null,
  loadErrors = {},
}) {
  const router = useRouter()
  const timezone = business?.timezone || 'Asia/Dhaka'

  const intelligenceTabs = [
    {
      id: 'facts',
      label: 'Facts & Issues',
      icon: FileText,
      href: `/business/${businessId}/intelligence/facts`,
    },
    { id: 'graph', label: 'Context Graph', icon: Share2, href: `/business/${businessId}/intelligence/graph` },
    {
      id: 'metrics',
      label: 'Metrics & Analysis',
      icon: BarChart2,
      href: `/business/${businessId}/intelligence/metrics`,
    },
    {
      id: 'pipeline',
      label: 'Data Pipeline',
      icon: Database,
      href: `/business/${businessId}/intelligence/pipeline`,
    },
  ]

  // Optional Sample Data (SIMULATED) toggle per spec
  const [sampleMode, setSampleMode] = useState(false)

  // Real facts and issues data
  const realFacts = factsData?.results || (Array.isArray(factsData) ? factsData : [])
  const displayedFacts = sampleMode ? (realFacts.length > 0 ? realFacts : SAMPLE_FACTS) : realFacts

  const realIssues = issuesData?.results || (Array.isArray(issuesData) ? issuesData : [])
  const displayedIssues = sampleMode ? (realIssues.length > 0 ? realIssues : SAMPLE_ISSUES) : realIssues

  // Triage state
  const [triageLoadingId, setTriageLoadingId] = useState(null)
  const [triageError, setTriageError] = useState('')

  const handleTriageIssue = async (issueId, newStatus) => {
    setTriageLoadingId(issueId)
    setTriageError('')
    try {
      const body = issuePatchBody(newStatus)
      await clientApi(issuePatchPath(businessId, issueId), {
        method: 'PATCH',
        body: JSON.stringify(body),
      })
      router.refresh()
    } catch (err) {
      setTriageError(err?.detail || err?.message || 'Failed to update issue status.')
    } finally {
      setTriageLoadingId(null)
    }
  }

  // Evidence Drawer state
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false)
  const [selectedEvidence, setSelectedEvidence] = useState(null)

  // Context Graph state (FE-W4, FE-W5)
  const [graphKind, setGraphKind] = useState('customer')
  const [graphEntityId, setGraphEntityId] = useState('1')
  const [graphData, setGraphData] = useState(null)
  const [loadingGraph, setLoadingGraph] = useState(false)
  const [graphError, setGraphError] = useState('')
  const [graphErrorKindVal, setGraphErrorKindVal] = useState('')
  const [rebuildingGraphInTab, setRebuildingGraphInTab] = useState(false)
  const [journeyData, setJourneyData] = useState(null)
  const [loadingJourney, setLoadingJourney] = useState(false)
  const [journeyError, setJourneyError] = useState('')
  const [journeyErrorKindVal, setJourneyErrorKindVal] = useState('')

  // Metrics Tab State (FE-W1)
  const [metricsList, setMetricsList] = useState([])
  const [loadingMetrics, setLoadingMetrics] = useState(false)
  const [metricsError, setMetricsError] = useState('')
  const [selectedMetric, setSelectedMetric] = useState(null)
  const [snapshotsList, setSnapshotsList] = useState([])
  const [loadingSnapshots, setLoadingSnapshots] = useState(false)
  const [snapshotsError, setSnapshotsError] = useState('')

  useEffect(() => {
    if (activeTab !== 'metrics' || !businessId) return
    let active = true
    setLoadingMetrics(true)
    setMetricsError('')
    clientApi(metricsPath(businessId, { limit: 100, offset: 0 }))
      .then((data) => {
        if (!active) return
        const norm = normalizeList(data)
        setMetricsList(norm.results)
      })
      .catch((err) => {
        if (!active) return
        setMetricsError(err?.detail || err?.message || 'Failed to load metrics.')
      })
      .finally(() => {
        if (active) setLoadingMetrics(false)
      })
    return () => {
      active = false
    }
  }, [activeTab, businessId])

  const handleSelectMetric = (metric) => {
    setSelectedMetric(metric)
    setLoadingSnapshots(true)
    setSnapshotsError('')
    setSnapshotsList([])
    clientApi(snapshotsPath(businessId, metric.key, { limit: 50, offset: 0 }))
      .then((data) => {
        const norm = normalizeList(data)
        setSnapshotsList(norm.results)
      })
      .catch((err) => {
        setSnapshotsError(err?.detail || err?.message || 'Failed to load metric snapshots.')
      })
      .finally(() => {
        setLoadingSnapshots(false)
      })
  }

  // Pipeline Tab State (FE-W2)
  const canManage = isManager(business?.role)
  const [runningPipeline, setRunningPipeline] = useState(false)
  const [pipelineError, setPipelineError] = useState('')
  const [pipelineResult, setPipelineResult] = useState(null)
  const [rebuildingGraph, setRebuildingGraph] = useState(false)
  const [rebuildError, setRebuildError] = useState('')
  const [rebuildResult, setRebuildResult] = useState(null)

  const handleRunPipeline = async () => {
    setRunningPipeline(true)
    setPipelineError('')
    setPipelineResult(null)
    try {
      const data = await clientApi(PIPELINE_RUN_PATH(businessId), {
        method: 'POST',
      })
      setPipelineResult(summarizePipelineResult(data))
      router.refresh()
    } catch (err) {
      setPipelineError(err?.detail || err?.message || 'Pipeline execution failed.')
    } finally {
      setRunningPipeline(false)
    }
  }

  const handleRebuildGraph = async () => {
    setRebuildingGraph(true)
    setRebuildError('')
    setRebuildResult(null)
    try {
      const body = rebuildBody({ clean: false })
      const data = await clientApi(GRAPH_REBUILD_PATH(businessId), {
        method: 'POST',
        body: JSON.stringify(body),
      })
      setRebuildResult(summarizeRebuildResult(data))
      router.refresh()
    } catch (err) {
      setRebuildError(err?.detail || err?.message || 'Graph rebuild failed.')
    } finally {
      setRebuildingGraph(false)
    }
  }

  const handleInspectGraph = async (e) => {
    if (e) e.preventDefault()
    const trimmed = graphEntityId ? String(graphEntityId).trim() : ''
    let idBig
    try {
      idBig = BigInt(trimmed)
    } catch {
      setGraphError('Please enter a valid entity ID between 1 and 9223372036854775807.')
      return
    }
    if (idBig <= 0n || idBig > 9223372036854775807n) {
      setGraphError('Please enter a valid entity ID between 1 and 9223372036854775807.')
      return
    }

    setLoadingGraph(true)
    setGraphError('')
    setGraphErrorKindVal('')
    setGraphData(null)

    // Reset journey state
    setJourneyData(null)
    setJourneyError('')
    setJourneyErrorKindVal('')
    const isJourneySupported = graphKind === 'customer' || graphKind === 'order'
    if (isJourneySupported) {
      setLoadingJourney(true)
    }

    const traversalTask = (async () => {
      try {
        // Calls businesses/<id>/graph/traversal/ via traversalPath
        const path = traversalPath(businessId, graphKind, trimmed)
        const data = await clientApi(path)
        const view = buildGraphView(data)
        setGraphData(view)
      } catch (err) {
        const kind = graphErrorKind(err)
        setGraphErrorKindVal(kind)
        if (kind === 'not_built') {
          setGraphError('The business graph has not been built yet.')
        } else if (kind === 'not_found') {
          setGraphError('This entity is not in the graph. Rebuild the graph if it is new.')
        } else {
          setGraphError(err.detail || err.message || 'Failed to inspect graph.')
        }
      } finally {
        setLoadingGraph(false)
      }
    })()

    const journeyTask = (async () => {
      if (!isJourneySupported) return
      try {
        const jPath = journeyPath(businessId, graphKind, trimmed)
        const jRaw = await clientApi(jPath)
        const jView = buildJourneyView(jRaw)
        setJourneyData(jView)
      } catch (err) {
        const kind = graphErrorKind(err)
        setJourneyErrorKindVal(kind)
        if (kind === 'not_built') {
          setJourneyError('The business graph has not been built yet.')
        } else if (kind === 'not_found') {
          setJourneyError('This entity is not in the graph. Rebuild the graph if it is new.')
        } else {
          setJourneyError(err.detail || err.message || 'Failed to load journey.')
        }
      } finally {
        setLoadingJourney(false)
      }
    })()

    await Promise.all([traversalTask, journeyTask])
  }

  const handleRebuildGraphInTab = async () => {
    setRebuildingGraphInTab(true)
    try {
      await clientApi(GRAPH_REBUILD_PATH(businessId), {
        method: 'POST',
        body: JSON.stringify(REBUILD_BODY),
      })
      await handleInspectGraph()
    } catch (err) {
      setGraphError(err.detail || err.message || 'Failed to rebuild graph.')
      setJourneyError(err.detail || err.message || 'Failed to rebuild graph.')
    } finally {
      setRebuildingGraphInTab(false)
    }
  }

  // Load initial graph on graph tab open
  useEffect(() => {
    if (activeTab === 'graph' && !graphData && !loadingGraph && !graphError) {
      handleInspectGraph()
    }
  }, [activeTab])

  const handleOpenEvidence = (item) => {
    setSelectedEvidence(item)
    setEvidenceDrawerOpen(true)
  }

  return (
    <div className="workspace-page stack-lg">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-3)',
        }}
      >
        <Tabs tabs={intelligenceTabs} activeTab={activeTab} ariaLabel="Intelligence Workspace Navigation" />

        {/* Optional Demo Mode Toggle per spec */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Checkbox
            id="sample-mode-switch"
            checked={sampleMode}
            onChange={(e) => setSampleMode(e.target.checked)}
            label="Sample data (SIMULATED)"
          />
          {sampleMode && <SimulatedBadge />}
        </div>
      </div>

      {/* ============================================================== */}
      {/* TAB 1: FACTS & ISSUES                                          */}
      {/* ============================================================== */}
      {activeTab === 'facts' && (
        <div className="stack-lg">
          {sampleMode && (
            <Banner variant="info">
              <strong>SIMULATED DEMO MODE ACTIVE.</strong> Displaying verified sample business facts and
              integrity rules for demonstration.
            </Banner>
          )}

          {/* Open Integrity Issues Table */}
          <section className="surface card-padding stack-sm" aria-labelledby="issues-title">
            <div className="section-header">
              <div>
                <h3 id="issues-title" className="section-title">
                  Open Business Integrity Issues
                </h3>
                <p className="section-desc">
                  Real-time rule engine detections, fulfillment exceptions, and data integrity anomalies.
                </p>
              </div>
              <span className="count-chip font-mono">
                {issuesData?.total_count ?? displayedIssues.length}
              </span>
            </div>

            {triageError && (
              <Banner variant="danger">
                <strong>Triage error:</strong> {triageError}
              </Banner>
            )}

            {loadErrors?.issues ? (
              <UnavailableState owner="Business Intelligence" reason={loadErrors.issues} />
            ) : displayedIssues.length === 0 ? (
              <EmptyState icon={AlertTriangle} title="No open issues" description="No open issues." />
            ) : (
              <DataTable
                columns={[
                  {
                    key: 'severity',
                    label: 'Severity',
                    render: (row) => <SeverityChip severity={row.severity} size="sm" />,
                  },
                  {
                    key: 'title',
                    label: 'Issue Summary',
                    render: (row) => (
                      <div>
                        <div className="font-semibold text-body">{row.title || `Issue #${row.id}`}</div>
                        {sampleMode && !realIssues.length && <SimulatedBadge />}
                      </div>
                    ),
                  },
                  {
                    key: 'issue_type',
                    label: 'Issue Type',
                    render: (row) => (
                      <span className="badge badge-secondary">{row.issue_type || 'GENERAL'}</span>
                    ),
                  },
                  {
                    key: 'confidence',
                    label: 'Confidence',
                    render: (row) => {
                      const pct = confidencePercent(row.confidence) ?? row.confidence
                      return (
                        <span className="font-mono text-caption text-secondary">
                          {pct != null ? `${pct}%` : '—'}
                        </span>
                      )
                    },
                  },
                  {
                    key: 'detected_at',
                    label: 'Detected',
                    render: (row) => (
                      <span className="font-mono text-caption text-muted">
                        {row.detected_at ? dateTime(row.detected_at, timezone) : '—'}
                      </span>
                    ),
                  },
                  {
                    key: 'status',
                    label: 'Status',
                    render: (row) => <StatusChip status={row.status || 'OPEN'} size="sm" />,
                  },
                  {
                    key: 'actions',
                    label: 'Audit & Actions',
                    render: (row) => (
                      <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={Eye}
                          onClick={() => handleOpenEvidence(row)}
                        >
                          Evidence
                        </Button>
                        {canManage && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={row.status === 'ACKNOWLEDGED' || triageLoadingId === row.id}
                              onClick={() => handleTriageIssue(row.id, 'ACKNOWLEDGED')}
                            >
                              Acknowledge
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={row.status === 'RESOLVED' || triageLoadingId === row.id}
                              onClick={() => handleTriageIssue(row.id, 'RESOLVED')}
                            >
                              Resolve
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={row.status === 'DISMISSED' || triageLoadingId === row.id}
                              onClick={() => handleTriageIssue(row.id, 'DISMISSED')}
                            >
                              Dismiss
                            </Button>
                          </>
                        )}
                      </div>
                    ),
                  },
                ]}
                data={displayedIssues}
                keyExtractor={(row) => row.id || row.rule_key}
              />
            )}
          </section>

          {/* Business Facts Section */}
          <section className="surface card-padding stack-sm" aria-labelledby="facts-title">
            <div className="section-header">
              <div>
                <h3 id="facts-title" className="section-title">
                  Authoritative Business Facts
                </h3>
                <p className="section-desc">
                  Deterministic domain facts aggregated from authoritative commerce, fulfillment, and identity
                  ledgers.
                </p>
              </div>
              <span className="count-chip font-mono">{factsData?.total_count ?? displayedFacts.length}</span>
            </div>

            {loadErrors?.facts ? (
              <UnavailableState owner="Business Intelligence" reason={loadErrors.facts} />
            ) : displayedFacts.length === 0 ? (
              <EmptyState icon={FileText} title="No facts yet" description="No facts yet." />
            ) : (
              <DataTable
                columns={[
                  {
                    key: 'statement',
                    label: 'Statement',
                    render: (row) => (
                      <div>
                        <div className="font-semibold text-body">{row.statement || '—'}</div>
                        {sampleMode && !realFacts.length && <SimulatedBadge />}
                      </div>
                    ),
                  },
                  {
                    key: 'fact_type',
                    label: 'Fact Type',
                    render: (row) => (
                      <span className="badge badge-secondary">
                        {row.fact_type || row.category || 'GENERAL'}
                      </span>
                    ),
                  },
                  {
                    key: 'value',
                    label: 'Value',
                    render: (row) => (
                      <span className="font-mono text-caption">
                        {row.value != null
                          ? `${row.value}${row.value_unit ? ` ${row.value_unit}` : ''}`
                          : '—'}
                      </span>
                    ),
                  },
                  {
                    key: 'confidence',
                    label: 'Confidence',
                    render: (row) => {
                      const pct = confidencePercent(row.confidence) ?? row.confidence
                      return (
                        <span className="font-mono text-caption text-secondary">
                          {pct != null ? `${pct}%` : '—'}
                        </span>
                      )
                    },
                  },
                  {
                    key: 'status',
                    label: 'Status',
                    render: (row) => <StatusChip status={row.status || 'VERIFIED'} size="sm" />,
                  },
                  {
                    key: 'rule_key',
                    label: 'Rule Key',
                    render: (row) => (
                      <span className="font-mono text-caption text-muted">{row.rule_key || '—'}</span>
                    ),
                  },
                  {
                    key: 'actions',
                    label: 'Evidence',
                    render: (row) => (
                      <Button
                        variant="secondary"
                        size="sm"
                        icon={Eye}
                        onClick={() => handleOpenEvidence(row)}
                      >
                        View
                      </Button>
                    ),
                  },
                ]}
                data={displayedFacts}
                keyExtractor={(row) => row.id || row.rule_key}
              />
            )}
          </section>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: CONTEXT GRAPH (D22)                                     */}
      {/* ============================================================== */}
      {activeTab === 'graph' && (
        <div className="stack-lg">
          {/* Query Formulation Toolbar */}
          <form className="intelligence-toolbar" onSubmit={handleInspectGraph}>
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <span className="font-semibold text-caption text-secondary">Entity Kind:</span>
                <Select
                  value={graphKind}
                  onChange={(e) => setGraphKind(e.target.value)}
                  aria-label="Entity Kind"
                  style={{ width: '130px' }}
                >
                  <option value="customer">Customer</option>
                  <option value="order">Order</option>
                  <option value="product">Product</option>
                  <option value="conversation">Conversation</option>
                  <option value="shipment">Shipment</option>
                </Select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <label htmlFor="graph-entity-id-input" className="font-semibold text-caption text-secondary">
                  Entity ID:
                </label>
                <Input
                  id="graph-entity-id-input"
                  aria-label="Entity ID"
                  type="number"
                  min="1"
                  placeholder="e.g. 1"
                  value={graphEntityId}
                  onChange={(e) => setGraphEntityId(e.target.value)}
                  style={{ width: '100px' }}
                  required
                />
              </div>

              <Button type="submit" variant="primary" size="sm" icon={Search} loading={loadingGraph}>
                Inspect Graph
              </Button>
            </div>

            <span className="font-mono text-caption text-muted">
              Scope: <strong>Depth 2, up to 100 nodes</strong>
            </span>
          </form>

          {/* Graph Legend (Shapes & Icons - Never color alone) */}
          <div className="graph-legend-container" role="region" aria-label="Entity Graph Legend">
            <span className="font-semibold text-caption text-secondary">GRAPH LEGEND:</span>

            <div className="graph-legend-item">
              <div className="graph-legend-symbol circle" aria-hidden="true">
                <User size={12} />
              </div>
              <span>Customer (Circle)</span>
            </div>

            <div className="graph-legend-item">
              <div className="graph-legend-symbol diamond" aria-hidden="true">
                <ShoppingBag size={10} />
              </div>
              <span>Order (Diamond)</span>
            </div>

            <div className="graph-legend-item">
              <div className="graph-legend-symbol square" aria-hidden="true">
                <Package size={12} />
              </div>
              <span>Product (Square)</span>
            </div>

            <div className="graph-legend-item">
              <div className="graph-legend-symbol hexagon" aria-hidden="true">
                <Shield size={12} />
              </div>
              <span>Identity (Hexagon)</span>
            </div>
          </div>

          {/* Graph Visualization / Node List */}
          <div className="surface card-padding stack-sm">
            <div
              className="section-header"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 'var(--space-2)',
              }}
            >
              <div>
                <h3 className="section-title">
                  Topology for {graphKind.toUpperCase()} #{graphEntityId}
                </h3>
                <p className="section-desc">
                  Graph nodes and relationships connecting authoritative entities.
                </p>
              </div>

              {graphData && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  {graphData.truncated && <span className="badge badge-warning">Truncated</span>}
                  {graphData.hiddenEdges > 0 && (
                    <span className="badge badge-neutral">
                      {graphData.hiddenEdges} {graphData.hiddenEdges === 1 ? 'edge hidden' : 'edges hidden'}
                    </span>
                  )}
                </div>
              )}
            </div>

            {loadingGraph ? (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center' }} className="text-secondary">
                Loading graph topology...
              </div>
            ) : graphError ? (
              <div className="stack-md">
                <UnavailableState owner="Business Graph" reason={graphError} />
                {graphErrorKindVal === 'not_built' && canManage && (
                  <div>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleRebuildGraphInTab}
                      loading={rebuildingGraphInTab}
                    >
                      Rebuild graph
                    </Button>
                  </div>
                )}
              </div>
            ) : graphData?.nodes?.length > 0 ? (
              <div className="stack-md">
                <div className="graph-node-list">
                  {graphData.nodes.map((node) => {
                    const isCircle = node.entity_type === 'CUSTOMER'
                    const isDiamond = node.entity_type === 'ORDER'
                    const isSquare = node.entity_type === 'PRODUCT'
                    const symbolClass = isCircle
                      ? 'circle'
                      : isDiamond
                        ? 'diamond'
                        : isSquare
                          ? 'square'
                          : 'hexagon'

                    return (
                      <div key={node.id} className="graph-node-item">
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                          <div className={`graph-legend-symbol ${symbolClass}`} aria-hidden="true">
                            {isCircle ? (
                              <User size={12} />
                            ) : isDiamond ? (
                              <ShoppingBag size={10} />
                            ) : isSquare ? (
                              <Package size={12} />
                            ) : (
                              <Shield size={12} />
                            )}
                          </div>

                          <div>
                            <span className="font-semibold text-body">
                              {node.label || `${node.entity_type} #${node.entity_id}`}
                            </span>
                            <span
                              className="text-caption font-mono text-muted"
                              style={{ marginLeft: 'var(--space-2)' }}
                            >
                              [{node.entity_type}]
                            </span>
                          </div>
                        </div>

                        <span className="graph-edge-tag">Node #{node.id}</span>
                      </div>
                    )
                  })}
                </div>

                {graphData.edges?.length > 0 && (
                  <div className="stack-xs" style={{ marginTop: 'var(--space-3)' }}>
                    <h4
                      className="font-semibold text-caption text-secondary"
                      style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
                    >
                      Graph Relationships ({graphData.edges.length})
                    </h4>
                    <div className="stack-xs">
                      {graphData.edges.map((edge) => (
                        <div
                          key={edge.id}
                          className="surface-secondary"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: 'var(--space-2) var(--space-3)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: 'var(--font-caption)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          <span>
                            <strong>{edge.sourceLabel}</strong>
                            {' -- '}
                            <span className="text-secondary">{edge.relationship_type}</span>
                            {' --> '}
                            <strong>{edge.targetLabel}</strong>
                          </span>
                          {typeof edge.confidence === 'number' && (
                            <span className="text-muted text-caption">
                              {Math.round(edge.confidence * 100)}%
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <UnavailableState
                owner="Business Graph"
                reason="Graph context is not yet mapped for this entity."
              />
            )}
          </div>

          {/* Journey timeline section (FE-W5) */}
          <div className="surface card-padding stack-sm">
            <div className="section-header">
              <div>
                <h3 className="section-title">Journey timeline</h3>
                <p className="section-desc">
                  Chronological lifecycle stages and domain events connecting customer and order milestones.
                </p>
              </div>
            </div>

            {graphKind !== 'customer' && graphKind !== 'order' ? (
              <UnavailableState
                owner="Business Graph"
                reason="Journeys are available for customers and orders."
              />
            ) : loadingJourney ? (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center' }} className="text-secondary">
                Loading journey timeline...
              </div>
            ) : journeyError ? (
              <div className="stack-md">
                <UnavailableState owner="Business Graph" reason={journeyError} />
                {journeyErrorKindVal === 'not_built' && canManage && (
                  <div>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleRebuildGraphInTab}
                      loading={rebuildingGraphInTab}
                    >
                      Rebuild graph
                    </Button>
                  </div>
                )}
              </div>
            ) : journeyData ? (
              <div className="stack-md">
                {/* Headline summary chips */}
                {journeyData.headline?.length > 0 && (
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: 'var(--space-2)',
                    }}
                  >
                    {journeyData.headline.map((item, idx) => (
                      <div
                        key={idx}
                        className="surface-secondary"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 'var(--space-2)',
                          padding: 'var(--space-1) var(--space-3)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: 'var(--font-caption)',
                        }}
                      >
                        <span className="text-secondary">{item.label}:</span>
                        <strong className="font-mono">{String(item.value)}</strong>
                      </div>
                    ))}
                  </div>
                )}

                {/* Timeline ordered list */}
                {journeyData.timeline?.length > 0 ? (
                  <ol
                    className="stack-xs"
                    style={{
                      margin: 0,
                      padding: 0,
                      listStyle: 'none',
                    }}
                  >
                    {journeyData.timeline.map((item, idx) => (
                      <li
                        key={idx}
                        className="surface-secondary"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          flexWrap: 'wrap',
                          gap: 'var(--space-2)',
                          padding: 'var(--space-2) var(--space-3)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <span className="badge badge-neutral" style={{ fontSize: 'var(--font-caption)' }}>
                            {item.stage}
                          </span>
                          <span className="font-semibold text-body">{item.label}</span>
                          <span className="font-mono text-muted text-caption">
                            [{item.entityType} #{item.entityId}]
                          </span>
                        </div>

                        {item.timestamp && (
                          <span className="font-mono text-caption text-secondary">
                            {dateTime(item.timestamp, timezone)}
                          </span>
                        )}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <div className="text-muted text-caption" style={{ padding: 'var(--space-3)' }}>
                    No journey timeline events found.
                  </div>
                )}
              </div>
            ) : (
              <UnavailableState owner="Business Graph" reason="No journey data available for this entity." />
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 3: METRICS & ANALYSIS                                      */}
      {/* ============================================================== */}
      {activeTab === 'metrics' && (
        <div className="stack-lg">
          <div aria-live="polite" className="sr-only">
            {loadingMetrics ? 'Loading metrics registry...' : ''}
            {loadingSnapshots ? 'Loading metric observations...' : ''}
          </div>

          {metricsError && (
            <Banner variant="danger">
              <strong>Failed to load metrics:</strong> {metricsError}
            </Banner>
          )}

          {loadingMetrics ? (
            <div className="surface card-padding text-muted">Loading metrics registry...</div>
          ) : metricsList.length === 0 ? (
            <EmptyState
              icon={BarChart2}
              title="No metrics yet"
              description="No metrics yet. A manager can run the data pipeline on the Pipeline tab."
            />
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: 'var(--space-4)',
              }}
            >
              <section className="surface card-padding stack-sm" aria-labelledby="metrics-title">
                <div className="section-header">
                  <div>
                    <h2 id="metrics-title" className="section-title">
                      Metrics Registry
                    </h2>
                    <p className="text-secondary text-caption">
                      Verified KPI metrics and calculated observation definitions.
                    </p>
                  </div>
                  <span className="count-chip font-mono">{metricsList.length}</span>
                </div>

                <DataTable
                  columns={[
                    {
                      key: 'name',
                      label: 'Metric Name',
                      render: (row) => <div className="font-semibold text-body">{row.name || row.key}</div>,
                    },
                    {
                      key: 'key',
                      label: 'Key',
                      render: (row) => (
                        <span className="font-mono text-caption text-secondary">{row.key}</span>
                      ),
                    },
                    {
                      key: 'category',
                      label: 'Category',
                      render: (row) => <span className="badge badge-secondary">{row.category}</span>,
                    },
                    {
                      key: 'unit',
                      label: 'Unit',
                      render: (row) => <span className="font-mono text-caption">{row.unit || '—'}</span>,
                    },
                    {
                      key: 'value_type',
                      label: 'Type',
                      render: (row) => <span className="text-caption text-muted">{row.value_type}</span>,
                    },
                    {
                      key: 'actions',
                      label: 'Snapshots',
                      render: (row) => (
                        <Button
                          variant={selectedMetric?.key === row.key ? 'primary' : 'secondary'}
                          size="sm"
                          onClick={() => handleSelectMetric(row)}
                        >
                          View
                        </Button>
                      ),
                    },
                  ]}
                  data={metricsList}
                  keyExtractor={(row) => row.key || row.id}
                />
              </section>

              <section className="surface card-padding stack-sm" aria-labelledby="snapshots-title">
                <div className="section-header">
                  <div>
                    <h2 id="snapshots-title" className="section-title">
                      {selectedMetric
                        ? `Snapshots: ${selectedMetric.name || selectedMetric.key}`
                        : 'Metric Snapshots'}
                    </h2>
                    <p className="text-secondary text-caption">
                      {selectedMetric
                        ? `Observations recorded for ${selectedMetric.key}`
                        : 'Select a metric from the registry to inspect calculated snapshots.'}
                    </p>
                  </div>
                  {selectedMetric && <span className="count-chip font-mono">{snapshotsList.length}</span>}
                </div>

                {snapshotsError && (
                  <Banner variant="danger">
                    <strong>Failed to load snapshots:</strong> {snapshotsError}
                  </Banner>
                )}

                {!selectedMetric ? (
                  <div className="empty-state-card text-muted">
                    Select a metric from the list to view its observations.
                  </div>
                ) : loadingSnapshots ? (
                  <div className="text-muted">Loading snapshots...</div>
                ) : snapshotsList.length === 0 ? (
                  <div className="empty-state-card text-muted">Not computed for this period.</div>
                ) : (
                  <DataTable
                    columns={[
                      {
                        key: 'value',
                        label: 'Value',
                        render: (row) => (
                          <span className="font-mono font-semibold text-body">
                            {row.value != null ? String(row.value) : '—'}{' '}
                            {selectedMetric.unit ? (
                              <span className="text-muted font-normal text-caption">
                                {selectedMetric.unit}
                              </span>
                            ) : null}
                          </span>
                        ),
                      },
                      {
                        key: 'period_type',
                        label: 'Period',
                        render: (row) => <span className="badge badge-secondary">{row.period_type}</span>,
                      },
                      {
                        key: 'window',
                        label: 'Time Window',
                        render: (row) => (
                          <span className="font-mono text-caption text-secondary">
                            {row.period_start ? dateTime(row.period_start, timezone) : '—'} to{' '}
                            {row.period_end ? dateTime(row.period_end, timezone) : '—'}
                          </span>
                        ),
                      },
                      {
                        key: 'dimension',
                        label: 'Dimension',
                        render: (row) => (
                          <span className="font-mono text-caption text-muted">
                            {row.dimension_type
                              ? `${row.dimension_type}: ${row.dimension_value || 'all'}`
                              : '—'}
                          </span>
                        ),
                      },
                    ]}
                    data={snapshotsList}
                    keyExtractor={(row, idx) => row.id || idx}
                  />
                )}
              </section>
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 4: DATA PIPELINE                                           */}
      {/* ============================================================== */}
      {activeTab === 'pipeline' && (
        <div className="stack-lg">
          <div aria-live="polite" className="sr-only">
            {runningPipeline ? 'Running data pipeline...' : ''}
            {rebuildingGraph ? 'Rebuilding context graph...' : ''}
          </div>

          <section className="surface card-padding stack-md" aria-labelledby="pipeline-heading">
            <div>
              <h2 id="pipeline-heading" className="section-title">
                Data Pipeline & Graph Orchestration
              </h2>
              <p className="text-secondary text-body" style={{ marginTop: 'var(--space-1)' }}>
                Run the data pipeline first to synchronize the registry, calculate metric snapshots, and
                reconcile facts; then rebuild the graph.
              </p>
            </div>

            {!canManage ? (
              <div className="empty-state-card text-muted">
                Only owners and managers can run the pipeline.
              </div>
            ) : (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                  gap: 'var(--space-4)',
                }}
              >
                {/* Stage 1: Pipeline */}
                <div
                  className="surface stack-sm"
                  style={{
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-4)',
                  }}
                >
                  <div className="stack-xs">
                    <h3 className="card-title">1. Business Intelligence Pipeline</h3>
                    <p className="text-secondary text-caption">
                      Executes canonical reconciliation, seeds registry metrics, computes default-period
                      snapshots, and correlates open issues.
                    </p>
                  </div>

                  <div style={{ marginTop: 'var(--space-2)' }}>
                    <Button
                      variant="primary"
                      onClick={handleRunPipeline}
                      disabled={runningPipeline || rebuildingGraph}
                    >
                      {runningPipeline ? 'Running pipeline...' : 'Run data pipeline'}
                    </Button>
                  </div>

                  {pipelineError && (
                    <Banner variant="danger">
                      <strong>Pipeline error:</strong> {pipelineError}
                    </Banner>
                  )}

                  {pipelineResult && !pipelineError && (
                    <div className="stack-xs" style={{ marginTop: 'var(--space-3)' }}>
                      <h4 className="text-caption font-semibold uppercase text-secondary">Pipeline Result</h4>
                      <dl
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'auto 1fr',
                          gap: 'var(--space-1) var(--space-3)',
                          margin: 0,
                        }}
                      >
                        {pipelineResult.map((item, idx) => (
                          <React.Fragment key={idx}>
                            <dt className="text-caption text-secondary">{item.label}:</dt>
                            <dd className="text-caption font-mono font-semibold">{item.value}</dd>
                          </React.Fragment>
                        ))}
                      </dl>
                    </div>
                  )}
                </div>

                {/* Stage 2: Graph */}
                <div
                  className="surface stack-sm"
                  style={{
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-4)',
                  }}
                >
                  <div className="stack-xs">
                    <h3 className="card-title">2. Context Graph Rebuild</h3>
                    <p className="text-secondary text-caption">
                      Rebuilds knowledge graph nodes and cross-domain entity relationships for contextual
                      traversals.
                    </p>
                  </div>

                  <div style={{ marginTop: 'var(--space-2)' }}>
                    <Button
                      variant="secondary"
                      onClick={handleRebuildGraph}
                      disabled={runningPipeline || rebuildingGraph}
                    >
                      {rebuildingGraph ? 'Rebuilding graph...' : 'Rebuild graph'}
                    </Button>
                  </div>

                  {rebuildError && (
                    <Banner variant="danger">
                      <strong>Rebuild error:</strong> {rebuildError}
                    </Banner>
                  )}

                  {rebuildResult && !rebuildError && (
                    <div className="stack-xs" style={{ marginTop: 'var(--space-3)' }}>
                      <h4 className="text-caption font-semibold uppercase text-secondary">Rebuild Result</h4>
                      <dl
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'auto 1fr',
                          gap: 'var(--space-1) var(--space-3)',
                          margin: 0,
                        }}
                      >
                        {rebuildResult.map((item, idx) => (
                          <React.Fragment key={idx}>
                            <dt className="text-caption text-secondary">{item.label}:</dt>
                            <dd className="text-caption font-mono font-semibold">{item.value}</dd>
                          </React.Fragment>
                        ))}
                      </dl>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      {/* ============================================================== */}
      {/* EVIDENCE DRAWER                                                */}
      {/* ============================================================== */}
      <Drawer
        open={evidenceDrawerOpen}
        onClose={() => setEvidenceDrawerOpen(false)}
        title={
          selectedEvidence
            ? `Audit Thread: ${selectedEvidence.title || selectedEvidence.rule_key}`
            : 'Evidence Thread'
        }
      >
        {selectedEvidence && (
          <div className="stack-lg">
            <EvidencePanel
              title={selectedEvidence.title || selectedEvidence.statement || 'Grounding Evidence'}
              confidence={
                confidencePercent(selectedEvidence.confidence) ??
                (typeof selectedEvidence.confidence === 'number' ? selectedEvidence.confidence : 95)
              }
              source={selectedEvidence.source || 'Deterministic Rule Engine'}
              description={
                selectedEvidence.statement || selectedEvidence.description || selectedEvidence.title
              }
              items={
                Array.isArray(selectedEvidence.evidence) && selectedEvidence.evidence.length > 0
                  ? selectedEvidence.evidence.map((ev) =>
                      typeof ev === 'string'
                        ? { text: ev }
                        : { text: ev.text || ev.description || JSON.stringify(ev) },
                    )
                  : selectedEvidence.metadata?.evidence &&
                      Array.isArray(selectedEvidence.metadata.evidence) &&
                      selectedEvidence.metadata.evidence.length > 0
                    ? selectedEvidence.metadata.evidence.map((ev) =>
                        typeof ev === 'string'
                          ? { text: ev }
                          : { text: ev.text || ev.description || JSON.stringify(ev) },
                      )
                    : [{ text: 'No evidence rows were stored for this item.' }]
              }
            />

            <div className="surface card-padding stack-sm">
              <span className="font-semibold text-caption text-secondary">METADATA AUDIT</span>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-caption text-muted">Rule Key</span>
                <span className="font-mono text-caption">{selectedEvidence.rule_key || '—'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-caption text-muted">Timestamp</span>
                <span className="font-mono text-caption">
                  {selectedEvidence.detected_at ? dateTime(selectedEvidence.detected_at, timezone) : '—'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-caption text-muted">Status</span>
                <span className="font-mono text-caption">{selectedEvidence.status || '—'}</span>
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}
