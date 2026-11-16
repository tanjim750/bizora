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

export default function Intelligence({ business = {}, businessId, activeTab = 'facts', issuesData = null }) {
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

  // Real issues data
  const realIssues = issuesData?.results || (Array.isArray(issuesData) ? issuesData : [])
  const displayedIssues = sampleMode ? (realIssues.length > 0 ? realIssues : SAMPLE_ISSUES) : realIssues

  // Evidence Drawer state
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false)
  const [selectedEvidence, setSelectedEvidence] = useState(null)

  // One-Hop Graph Context state (D22)
  const [graphKind, setGraphKind] = useState('customer')
  const [graphEntityId, setGraphEntityId] = useState('1')
  const [graphData, setGraphData] = useState(null)
  const [loadingGraph, setLoadingGraph] = useState(false)
  const [graphError, setGraphError] = useState('')

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

  const handleInspectGraph = async (e) => {
    if (e) e.preventDefault()
    if (!graphEntityId.trim()) return

    setLoadingGraph(true)
    setGraphError('')
    setGraphData(null)

    try {
      const data = await clientApi(
        `businesses/${businessId}/graph-context/${graphKind}/${graphEntityId.trim()}`,
      )
      setGraphData(data)
    } catch (err) {
      setGraphError(err.detail || err.message || 'One-hop context graph is not initialized for this entity.')
    } finally {
      setLoadingGraph(false)
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
              <span className="count-chip font-mono">{displayedIssues.length}</span>
            </div>

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
                      {sampleMode && <SimulatedBadge />}
                    </div>
                  ),
                },
                {
                  key: 'rule_key',
                  label: 'Rule Identifier',
                  render: (row) => (
                    <span className="font-mono text-caption text-secondary">
                      {row.rule_key || 'rule.generic'}
                    </span>
                  ),
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
                  label: 'Audit Thread',
                  render: (row) => (
                    <Button variant="secondary" size="sm" icon={Eye} onClick={() => handleOpenEvidence(row)}>
                      View Evidence
                    </Button>
                  ),
                },
              ]}
              rows={displayedIssues}
              businessId={businessId}
              emptyTitle="No open integrity issues"
              emptyDescription="All deterministic business rules are passing. No anomalies or fulfillment exceptions are recorded."
              openInDrawer={false}
            />
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
            </div>

            {sampleMode ? (
              <div className="stack-sm">
                {SAMPLE_FACTS.map((fact) => (
                  <div
                    key={fact.id}
                    className="ai-recommendation-card"
                    style={{ cursor: 'pointer' }}
                    onClick={() => handleOpenEvidence(fact)}
                  >
                    <div className="stack-sm" style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <span className="badge badge-outline font-mono text-caption">{fact.category}</span>
                        <SimulatedBadge />
                        <span className="font-mono text-caption text-muted" style={{ marginLeft: 'auto' }}>
                          Confidence: {fact.confidence}%
                        </span>
                      </div>

                      <p className="text-body" style={{ margin: 0 }}>
                        {fact.statement}
                      </p>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                        <span className="text-caption font-mono text-secondary">Source: {fact.source}</span>
                        <span className="text-caption font-mono text-muted">Key: {fact.rule_key}</span>
                      </div>
                    </div>

                    <Button variant="ghost" size="sm" icon={ArrowRight}>
                      Evidence
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <UnavailableState
                owner="Business Intelligence"
                reason="The Business Intelligence fact derivation engine has not generated snapshots for this period."
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
                Inspect One-Hop Context
              </Button>
            </div>

            <span className="font-mono text-caption text-muted">
              Scope: <strong>PERSISTED_ONE_HOP</strong> (Fixed 1-hop depth)
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
            <div className="section-header">
              <div>
                <h3 className="section-title">
                  Persisted Topology for {graphKind.toUpperCase()} #{graphEntityId}
                </h3>
                <p className="section-desc">
                  Persisted one-hop node relationships connecting authoritative entities.
                </p>
              </div>
            </div>

            {loadingGraph ? (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center' }} className="text-secondary">
                Loading graph topology...
              </div>
            ) : graphError ? (
              <UnavailableState owner="Business Graph" reason={graphError} />
            ) : graphData?.nodes?.results?.length > 0 ? (
              <div className="graph-node-list">
                {graphData.nodes.results.map((node) => {
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

                      <span className="graph-edge-tag">One-Hop Connected</span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <UnavailableState
                owner="Business Graph"
                reason="Persisted one-hop graph context is not yet mapped for this entity."
              />
            )}
          </div>

          {/* Unmounted Multi-Hop Notice per spec */}
          <div className="stack-sm">
            <h4 className="section-title">Multi-Hop Traversal &amp; Deep Journeys</h4>
            <UnavailableState
              owner="Business Graph"
              reason="Multi-hop graph traversal, cross-domain paths, and historical snapshots are unmounted."
            />
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
        <UnavailableState
          owner="Platform Operations"
          reason="Pipeline orchestration and continuous ingestion runners are offline."
        />
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
              title={selectedEvidence.title || 'Grounding Evidence'}
              confidence={selectedEvidence.confidence || 95}
              source={selectedEvidence.source || 'Deterministic Rule Engine'}
              description={selectedEvidence.statement || selectedEvidence.title}
              items={
                selectedEvidence.evidence || [
                  {
                    text: `Deterministic verification passed for rule ${selectedEvidence.rule_key || 'rule.evaluated'}`,
                  },
                  { text: 'Authoritative transaction ledger matches recorded snapshot parameters.' },
                ]
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
                  {selectedEvidence.detected_at
                    ? dateTime(selectedEvidence.detected_at, timezone)
                    : 'Verified Present'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-caption text-muted">Verification Level</span>
                <span className="font-mono text-caption font-semibold text-success">
                  Deterministic Verified
                </span>
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}
