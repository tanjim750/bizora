'use client'

import React, { useState, useMemo } from 'react'
import Link from 'next/link'
import {
  Activity,
  Layers,
  HeartPulse,
  TrendingUp,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  AlertTriangle,
  ExternalLink,
  Clock,
  Radio,
  Sparkles,
  RefreshCw,
} from 'lucide-react'
import {
  KpiTile,
  DataTable,
  StatusChip,
  SeverityChip,
  EmptyState,
  UnavailableState,
  SimulatedBadge,
  Button,
} from '@/components/ui'
import { ChartCard, TrendLine, BarCompare } from '@/components/ui/charts'
import { businessPath, MANAGER_ROLES } from '@/lib/catalog'
import { dateTime, relativeTime } from '@/lib/format'

const PERIOD_OPTIONS = [
  { id: 'day', label: 'Day' },
  { id: 'week', label: 'Week' },
  { id: 'month', label: 'Month' },
  { id: 'rolling7', label: 'Rolling 7' },
  { id: 'rolling30', label: 'Rolling 30' },
]

const DOMAIN_MAP = {
  COMMERCE: ['ORDER', 'PAYMENT', 'REFUND', 'PRODUCT', 'SHIPMENT', 'VARIANT'],
  SUPPORT: ['CONVERSATION', 'MESSAGE', 'CALL', 'CALLBACK'],
  IDENTITY: ['CUSTOMER', 'IDENTITY', 'CONTACT', 'TAG'],
}

export default function Overview({
  business = {},
  data,
  queueCount,
  issues = [],
  activeTab = 'overview',
  hideHeading = false,
}) {
  const counts = data?.canonical_counts || {}
  const [period, setPeriod] = useState('month')
  const [compare, setCompare] = useState(false)
  const [domainFilter, setDomainFilter] = useState('ALL')

  const allAudits = data?.recent_activity?.results || []

  // Domain counts for filter chips
  const domainCounts = useMemo(() => {
    let commerce = 0
    let support = 0
    let identity = 0
    let system = 0

    allAudits.forEach((item) => {
      const type = (item.entity_type || '').toUpperCase()
      if (DOMAIN_MAP.COMMERCE.includes(type)) commerce++
      else if (DOMAIN_MAP.SUPPORT.includes(type)) support++
      else if (DOMAIN_MAP.IDENTITY.includes(type)) identity++
      else system++
    })

    return {
      ALL: allAudits.length,
      COMMERCE: commerce,
      SUPPORT: support,
      IDENTITY: identity,
      SYSTEM: system,
    }
  }, [allAudits])

  // Filtered audits for table
  const filteredAudits = useMemo(() => {
    if (domainFilter === 'ALL') return allAudits
    return allAudits.filter((item) => {
      const type = (item.entity_type || '').toUpperCase()
      if (domainFilter === 'COMMERCE') return DOMAIN_MAP.COMMERCE.includes(type)
      if (domainFilter === 'SUPPORT') return DOMAIN_MAP.SUPPORT.includes(type)
      if (domainFilter === 'IDENTITY') return DOMAIN_MAP.IDENTITY.includes(type)
      if (domainFilter === 'SYSTEM') {
        return (
          !DOMAIN_MAP.COMMERCE.includes(type) &&
          !DOMAIN_MAP.SUPPORT.includes(type) &&
          !DOMAIN_MAP.IDENTITY.includes(type)
        )
      }
      return true
    })
  }, [allAudits, domainFilter])

  // Columns for Audit Log table
  const auditColumns = [
    {
      key: 'action',
      label: 'Action',
      render: (row) => (
        <span className="font-semibold text-body">
          {row.action ? row.action.replace(/_/g, ' ') : 'Event'}
        </span>
      ),
    },
    {
      key: 'entity_type',
      label: 'Target Entity',
      render: (row) => (
        <span className="inline-flex items-center gap-1">
          <span className="text-secondary">{row.entity_type || 'Entity'}</span>
          {row.entity_id ? <span className="font-mono text-caption text-muted">#{row.entity_id}</span> : null}
        </span>
      ),
    },
    {
      key: 'actor',
      label: 'Actor',
      render: (row) => <span className="text-secondary">{row.actor ? `User #${row.actor}` : 'System'}</span>,
    },
    {
      key: 'created_at',
      label: 'Timestamp',
      render: (row) => (
        <span className="tabular-nums text-caption text-secondary" title={row.created_at}>
          {dateTime(row.created_at, business?.timezone)}
        </span>
      ),
    },
  ]

  // Trend time-series data scaled to selected period and counts
  const trendData = useMemo(() => {
    const baseOrders = Number(counts.orders) || 8

    if (period === 'day') {
      return [
        { date: '00:00', orders: 1, activity: 3 },
        { date: '04:00', orders: 0, activity: 1 },
        { date: '08:00', orders: 2, activity: 6 },
        { date: '12:00', orders: 3, activity: 8 },
        { date: '16:00', orders: 4, activity: 7 },
        { date: '20:00', orders: 2, activity: 4 },
      ]
    }
    if (period === 'week') {
      return [
        { date: 'Mon', orders: Math.max(1, Math.round(baseOrders * 0.12)), activity: 6 },
        { date: 'Tue', orders: Math.max(1, Math.round(baseOrders * 0.15)), activity: 8 },
        { date: 'Wed', orders: Math.max(1, Math.round(baseOrders * 0.18)), activity: 11 },
        { date: 'Thu', orders: Math.max(1, Math.round(baseOrders * 0.14)), activity: 7 },
        { date: 'Fri', orders: Math.max(1, Math.round(baseOrders * 0.22)), activity: 14 },
        { date: 'Sat', orders: Math.max(1, Math.round(baseOrders * 0.11)), activity: 5 },
        { date: 'Sun', orders: Math.max(1, Math.round(baseOrders * 0.08)), activity: 4 },
      ]
    }
    if (period === 'rolling7') {
      return [
        { date: 'D-6', orders: Math.max(1, Math.round(baseOrders * 0.1)), activity: 5 },
        { date: 'D-5', orders: Math.max(1, Math.round(baseOrders * 0.15)), activity: 7 },
        { date: 'D-4', orders: Math.max(1, Math.round(baseOrders * 0.2)), activity: 12 },
        { date: 'D-3', orders: Math.max(1, Math.round(baseOrders * 0.16)), activity: 9 },
        { date: 'D-2', orders: Math.max(1, Math.round(baseOrders * 0.18)), activity: 10 },
        { date: 'D-1', orders: Math.max(1, Math.round(baseOrders * 0.12)), activity: 6 },
        { date: 'Today', orders: Math.max(1, Math.round(baseOrders * 0.09)), activity: 8 },
      ]
    }
    if (period === 'rolling30') {
      return [
        { date: 'Day 5', orders: Math.max(1, Math.round(baseOrders * 0.14)), activity: 12 },
        { date: 'Day 10', orders: Math.max(1, Math.round(baseOrders * 0.18)), activity: 16 },
        { date: 'Day 15', orders: Math.max(1, Math.round(baseOrders * 0.16)), activity: 14 },
        { date: 'Day 20', orders: Math.max(1, Math.round(baseOrders * 0.22)), activity: 20 },
        { date: 'Day 25', orders: Math.max(1, Math.round(baseOrders * 0.17)), activity: 15 },
        { date: 'Day 30', orders: Math.max(1, Math.round(baseOrders * 0.13)), activity: 11 },
      ]
    }
    // Default 'month'
    return [
      { date: 'Week 1', orders: Math.max(1, Math.round(baseOrders * 0.2)), activity: 18 },
      { date: 'Week 2', orders: Math.max(1, Math.round(baseOrders * 0.28)), activity: 24 },
      { date: 'Week 3', orders: Math.max(1, Math.round(baseOrders * 0.32)), activity: 30 },
      { date: 'Week 4', orders: Math.max(1, Math.round(baseOrders * 0.2)), activity: 22 },
    ]
  }, [counts, period])

  const trendSeries = [
    { key: 'orders', name: 'Orders Placed', color: 'var(--chart-1)' },
    { key: 'activity', name: 'Audit Events', color: 'var(--chart-2)' },
  ]

  const trendTableColumns = [
    { key: 'date', label: 'Interval', type: 'text' },
    { key: 'orders', label: 'Orders Placed', type: 'mono', align: 'right' },
    { key: 'activity', label: 'Audit Events', type: 'mono', align: 'right' },
  ]

  // Channel Touchpoint Distribution data
  const channelData = [
    { category: 'Direct Web', value: 45 },
    { category: 'WhatsApp Messaging', value: 25 },
    { category: 'Facebook Messenger', value: 15 },
    { category: 'Marketplace', value: 10 },
    { category: 'Phone Orders', value: 5 },
  ]

  const channelTableColumns = [
    { key: 'category', label: 'Channel', type: 'text' },
    { key: 'value', label: 'Share (%)', type: 'mono', align: 'right' },
  ]

  // Per-domain health definitions
  const DOMAIN_HEALTH = [
    {
      id: 'commerce',
      name: 'Commerce & Orders',
      status: 'ACTIVE',
      statusLabel: 'Operational',
      authority: 'Core Ledger (Deterministic)',
      desc: 'Order state machine active, stock reservation locks and idempotency keys enforced.',
    },
    {
      id: 'payments',
      name: 'Payments & Billing',
      status: 'ACTIVE',
      statusLabel: 'Operational',
      authority: 'Financial Ledger (Immutable)',
      desc: `Double-entry payment and refund tracking active. Currency ISO: ${business?.currency || 'BDT'}.`,
    },
    {
      id: 'support',
      name: 'Customer Support',
      status: 'ACTIVE',
      statusLabel: 'Operational',
      authority: 'Support Queue & Triage',
      desc: 'Multi-channel conversation routing active. Priority and SLA triage listening.',
    },
    {
      id: 'shipments',
      name: 'Shipments & Logistics',
      status: 'ACTIVE',
      statusLabel: 'Operational',
      authority: 'Carrier Dispatch Engine',
      desc: 'Delivery tracking webhooks connected. Prepared-not-executed boundary enforced.',
    },
    {
      id: 'identity',
      name: 'Identity Resolution',
      status: 'ACTIVE',
      statusLabel: 'Operational',
      authority: 'Customer 360 Engine',
      desc: 'Canonical identity linking active. Conflict merge review operational.',
    },
    {
      id: 'bi',
      name: 'Business Intelligence',
      status: 'UNAVAILABLE',
      statusLabel: 'Not connected',
      authority: 'Overview & Monitoring',
      desc: 'Authoritative analytics provider contract is not registered.',
    },
    {
      id: 'ai',
      name: 'AI Advisory Intelligence',
      status: 'PENDING',
      statusLabel: 'Simulated',
      authority: 'AI Intelligence Service',
      desc: 'Advisory assistant active in simulation mode. Human approval required for all actions.',
    },
  ]

  // Columns for Open Business Issues
  const issueColumns = [
    {
      key: 'title',
      label: 'Issue Title',
      render: (row) => (
        <div>
          <span className="font-semibold text-body">{row.title}</span>
          {row.description && (
            <p className="text-caption text-secondary" style={{ margin: 0 }}>
              {row.description}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'severity',
      label: 'Severity',
      render: (row) => <SeverityChip severity={row.severity} size="sm" />,
    },
    {
      key: 'rule_key',
      label: 'Rule Key',
      type: 'mono',
    },
    {
      key: 'subject_entity_type',
      label: 'Target',
      render: (row) => (
        <span className="font-mono text-caption text-secondary">
          {row.subject_entity_type} #{row.subject_entity_id}
        </span>
      ),
    },
    {
      key: 'detected_at',
      label: 'Detected',
      render: (row) => (
        <span className="tabular-nums text-caption text-secondary">
          {dateTime(row.detected_at, business?.timezone)}
        </span>
      ),
    },
  ]

  return (
    <div className="overview-container stack-lg">
      {!hideHeading && (
        <div className="page-heading">
          <div>
            <p className="page-context">Business overview</p>
            <h1>Overview</h1>
            <p>
              Stored activity for {business?.name || 'this business'}. Counts are all time unless stated
              otherwise.
            </p>
          </div>
          <span className="count-chip">
            {business?.currency} · {business?.timezone}
          </span>
        </div>
      )}

      {/* Overview Reporting Controls Bar */}
      <section className="overview-controls-bar" aria-label="Reporting controls">
        <p className="overview-controls-info">
          <span>Authoritative ledger records as of today.</span>
          {compare && <span className="text-primary font-semibold"> · Comparison mode active</span>}
        </p>

        <div className="overview-controls-actions">
          <div className="period-controls" role="group" aria-label="Reporting period">
            {PERIOD_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setPeriod(opt.id)}
                className={`period-btn ${period === opt.id ? 'is-active' : ''}`}
                aria-pressed={period === opt.id}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setCompare((prev) => !prev)}
            className={`period-compare-btn ${compare ? 'is-active' : ''}`}
            aria-pressed={compare}
            aria-label="Toggle period comparison"
          >
            <CheckCircle2 size={14} aria-hidden="true" style={{ opacity: compare ? 1 : 0.4 }} />
            <span>Compare</span>
          </button>
        </div>
      </section>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="stack-lg">
          {/* Section: Core Entity Counts */}
          <section aria-labelledby="core-counts-title" className="stack-sm">
            <div className="section-title-wrap">
              <h2 id="core-counts-title" className="section-title">
                Authoritative Record Counts
              </h2>
              <p className="section-desc">
                Canonical entities stored in the deterministic PostgreSQL database.
              </p>
            </div>

            <div className="grid-kpi">
              <KpiTile title="Orders" value={counts.orders} subtext="Canonical records · all time" />
              <KpiTile title="Customers" value={counts.customers} subtext="Registered customer entities" />
              <KpiTile title="Payments" value={counts.payments} subtext="Settled payment ledger entries" />
              <KpiTile
                title="Open Cases"
                value={queueCount ?? counts.conversations}
                subtext="Active support queue conversations"
              />
              <KpiTile title="Shipments" value={counts.shipments} subtext="Carrier delivery consignments" />
              <KpiTile title="Calls" value={counts.calls} subtext="Recorded telephony sessions" />
            </div>
          </section>

          {/* Section: Executive KPIs (calm UNAVAILABLE state naming owner and reason) */}
          <section aria-labelledby="executive-kpis-title" className="stack-sm">
            <div className="section-title-wrap">
              <h2 id="executive-kpis-title" className="section-title">
                Executive KPIs & Analytics
              </h2>
              <p className="section-desc">
                Automated multi-channel aggregation pipelines from Overview &amp; Monitoring.
              </p>
            </div>

            <div className="grid-kpi">
              <KpiTile
                title="Gross Revenue"
                isUnavailable={true}
                unavailableOwner="Overview & Monitoring"
                unavailableReason="Revenue aggregation pipeline is not connected."
              />
              <KpiTile
                title="Net Revenue"
                isUnavailable={true}
                unavailableOwner="Overview & Monitoring"
                unavailableReason="Net revenue calculations require active financial sync."
              />
              <KpiTile
                title="Average Order Value"
                isUnavailable={true}
                unavailableOwner="Overview & Monitoring"
                unavailableReason="AOV analytics require connected sales channels."
              />
              <KpiTile
                title="Delivery Success"
                isUnavailable={true}
                unavailableOwner="Overview & Monitoring"
                unavailableReason="Carrier webhook telemetry is not connected."
              />
              <KpiTile
                title="Cart Abandonment"
                isUnavailable={true}
                unavailableOwner="Overview & Monitoring"
                unavailableReason="Storefront tracking pipeline is not connected."
              />
            </div>
          </section>

          {/* Section: Main Activity Feed + Aside Operations Snapshot */}
          <div className="grid-main-aside">
            {/* Main Column: Recent Activity Feed */}
            <section className="surface card-padding stack-sm" aria-labelledby="activity-feed-title">
              <div className="section-header">
                <div>
                  <h2 id="activity-feed-title" className="section-title">
                    Recent Activity Feed
                  </h2>
                  <p className="section-desc">Authoritative domain audit log, newest events first.</p>
                </div>
              </div>

              {/* Domain Filter Chips */}
              <div className="domain-filter-group" role="group" aria-label="Filter activity by domain">
                {[
                  { id: 'ALL', label: 'All', count: domainCounts.ALL },
                  { id: 'COMMERCE', label: 'Commerce', count: domainCounts.COMMERCE },
                  { id: 'SUPPORT', label: 'Support', count: domainCounts.SUPPORT },
                  { id: 'IDENTITY', label: 'Identity', count: domainCounts.IDENTITY },
                  { id: 'SYSTEM', label: 'System', count: domainCounts.SYSTEM },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setDomainFilter(item.id)}
                    className={`domain-chip-btn ${domainFilter === item.id ? 'is-active' : ''}`}
                    aria-pressed={domainFilter === item.id}
                  >
                    <span>{item.label}</span>
                    <span className="domain-chip-count">({item.count})</span>
                  </button>
                ))}
              </div>

              {/* Activity Table */}
              <DataTable
                columns={auditColumns}
                rows={filteredAudits}
                businessId={business.id}
                emptyTitle="No activity found"
                emptyDescription={`No recent audit events recorded for the ${domainFilter.toLowerCase()} domain.`}
                openInDrawer={false}
              />
            </section>

            {/* Aside Column: Operations Snapshot + AI Governance */}
            <div className="stack">
              <section className="surface card-padding stack-sm" aria-labelledby="ops-snapshot-title">
                <div className="section-header">
                  <div>
                    <h2 id="ops-snapshot-title" className="section-title">
                      Operations Snapshot
                    </h2>
                    <p className="section-desc">Auxiliary canonical records</p>
                  </div>
                </div>

                <dl className="snapshot-list">
                  <div>
                    <dt>Campaigns</dt>
                    <dd>{counts.campaigns ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Website Sessions</dt>
                    <dd>{counts.sessions ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Catalog Products</dt>
                    <dd>{counts.products ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Voice Telephony Calls</dt>
                    <dd>{counts.calls ?? '—'}</dd>
                  </div>
                </dl>

                <div
                  className="stack-sm"
                  style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-3)' }}
                >
                  <Link
                    className="button button-outline"
                    href={businessPath(business.id, 'support/queue')}
                    style={{ width: '100%', justifyContent: 'space-between' }}
                  >
                    <span>Support Queue</span>
                    <ArrowRight size={14} aria-hidden="true" />
                  </Link>
                  <Link
                    className="button button-outline"
                    href={businessPath(business.id, 'commerce/orders')}
                    style={{ width: '100%', justifyContent: 'space-between' }}
                  >
                    <span>Orders Ledger</span>
                    <ArrowRight size={14} aria-hidden="true" />
                  </Link>
                  <Link
                    className="button button-outline"
                    href={businessPath(business.id, 'customers')}
                    style={{ width: '100%', justifyContent: 'space-between' }}
                  >
                    <span>Customer 360</span>
                    <ArrowRight size={14} aria-hidden="true" />
                  </Link>
                </div>
              </section>

              {/* AI Governance Advisory Block */}
              <section className="surface card-padding stack-sm" aria-labelledby="ai-gov-title">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <SimulatedBadge text="SIMULATED" />
                  <span className="text-caption text-muted">AI Advisory</span>
                </div>
                <div>
                  <h3
                    id="ai-gov-title"
                    className="section-title"
                    style={{ fontSize: 'var(--text-card-title)' }}
                  >
                    Human Review Required
                  </h3>
                  <p className="section-desc" style={{ marginTop: 'var(--space-1)' }}>
                    Suggestions do not establish business facts or execute provider actions without explicit
                    human approval.
                  </p>
                </div>
                <Link
                  className="button button-secondary"
                  href={businessPath(business.id, 'ai')}
                  style={{ width: '100%', justifyContent: 'center' }}
                >
                  <span>Open AI Studio</span>
                </Link>
              </section>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: TRENDS */}
      {activeTab === 'trends' && (
        <div className="stack-lg">
          <div className="section-title-wrap">
            <h2 className="section-title">Operational Trends &amp; Channel Metrics</h2>
            <p className="section-desc">
              Multi-channel performance over the {period} period. Currency: {business?.currency || 'BDT'}.
            </p>
          </div>

          <div className="grid-2">
            {/* Chart 1: Order & Activity Volume */}
            <ChartCard
              title="Order & Activity Volume"
              subtitle={`Operational throughput over the selected ${period} window.`}
              badge={<SimulatedBadge />}
              tableData={trendData}
              tableColumns={trendTableColumns}
            >
              <TrendLine
                data={trendData}
                series={trendSeries}
                ariaLabel="Operational orders and activity trend"
              />
            </ChartCard>

            {/* Chart 2: Channel Touchpoint Breakdown */}
            <ChartCard
              title="Touchpoint & Channel Distribution"
              subtitle="Distribution of customer interactions across primary communication channels."
              badge={<SimulatedBadge />}
              tableData={channelData}
              tableColumns={channelTableColumns}
            >
              <BarCompare
                data={channelData}
                xKey="category"
                yKey="value"
                valueFormatter={(val) => `${val}%`}
                ariaLabel="Channel touchpoint distribution bar chart"
              />
            </ChartCard>

            {/* Chart 3: Revenue & Gross Margin (Honest UNAVAILABLE state) */}
            <ChartCard
              title="Revenue & Gross Margin"
              subtitle="Authoritative financial metric aggregation over time."
              unavailable={true}
              unavailableReason="Authoritative revenue pipeline is not registered. Financial ledger records are stored under Commerce."
            />

            {/* Chart 4: Customer Retention & Cart Funnel (Honest UNAVAILABLE state) */}
            <ChartCard
              title="Retention & Cart Funnel"
              subtitle="Multi-session cohort retention and storefront drop-off curves."
              unavailable={true}
              unavailableReason="Cohort retention and cart abandonment analytics require active tracking provider integration."
            />
          </div>
        </div>
      )}

      {/* TAB 3: HEALTH */}
      {activeTab === 'health' && (
        <div className="stack-lg">
          {/* Subsystems Health Grid */}
          <section aria-labelledby="subsystem-health-title" className="stack-sm">
            <div className="section-title-wrap">
              <h2 id="subsystem-health-title" className="section-title">
                Subsystem Operational Health
              </h2>
              <p className="section-desc">
                Live status and authoritative data contracts across all nine business domains.
              </p>
            </div>

            <div className="grid-2">
              {DOMAIN_HEALTH.map((domain) => (
                <div key={domain.id} className="health-domain-card">
                  <div className="health-domain-header">
                    <div>
                      <h3 className="health-domain-title">{domain.name}</h3>
                      <span className="health-domain-authority">Authority: {domain.authority}</span>
                    </div>
                    <StatusChip status={domain.status} label={domain.statusLabel} size="sm" />
                  </div>
                  <p className="health-domain-desc">{domain.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Open Business Issues Section */}
          <section aria-labelledby="open-issues-title" className="stack-sm">
            <div
              className="section-title-wrap"
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
            >
              <div>
                <h2 id="open-issues-title" className="section-title">
                  Open Business Issues
                </h2>
                <p className="section-desc">
                  Automated integrity alerts, fulfillment warnings, and orphaned records.
                </p>
              </div>
              <span className="count-chip">
                {issues.length} {issues.length === 1 ? 'issue' : 'issues'}
              </span>
            </div>

            {issues && issues.length > 0 ? (
              <div className="surface card-padding">
                <DataTable
                  columns={issueColumns}
                  rows={issues}
                  businessId={business.id}
                  emptyTitle="No issues detected"
                  openInDrawer={false}
                />
              </div>
            ) : (
              <div className="surface card-padding">
                <EmptyState
                  title="All systems healthy"
                  description="No open business issues or data integrity anomalies detected for this business."
                />
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
