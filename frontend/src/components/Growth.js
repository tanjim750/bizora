'use client'

import React, { useState, useMemo, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  TrendingUp,
  Globe,
  Layers,
  ArrowRight,
  ExternalLink,
  Sparkles,
  BarChart2,
  Calendar,
  MousePointer,
  DollarSign,
  Users,
  Eye,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Plus,
  Compass,
  Activity,
  Smartphone,
  Laptop,
} from 'lucide-react'
import {
  DataTable,
  StatusChip,
  EmptyState,
  UnavailableState,
  SimulatedBadge,
  Button,
  Dialog,
  Drawer,
  Input,
  Field,
  Select,
  KpiTile,
  PageHeader,
  Tabs,
  CopyableCode,
  Banner,
  Tooltip,
} from './ui'
import { ChartCard, TrendLine } from './ui/charts'
import { Timeline } from './ui/Timeline'
import { money, dateTime, relativeTime, duration } from '../lib/format/index.js'
import { clientApi } from '../lib/clientApi'

// Verified role sets
const WRITER_ROLES = new Set(['OPERATOR', 'MANAGER', 'OWNER'])

// Sample data for simulated preview mode
const SAMPLE_CAMPAIGNS = [
  {
    id: 101,
    name: 'Q4 Winter Omnichannel Launch',
    platform: 'Google Ads',
    status: 'ACTIVE',
    budget: 50000.0,
    spend: 42150.0,
    clicks: 12480,
    conversions: 482,
    started_at: '2026-10-15T08:00:00Z',
    ended_at: null,
  },
  {
    id: 102,
    name: 'Social Retargeting & Lookalikes',
    platform: 'Meta Ads',
    status: 'ACTIVE',
    budget: 25000.0,
    spend: 19800.0,
    clicks: 8920,
    conversions: 215,
    started_at: '2026-10-20T10:00:00Z',
    ended_at: null,
  },
  {
    id: 103,
    name: 'Top Funnel Video Discovery',
    platform: 'TikTok Ads',
    status: 'PAUSED',
    budget: 15000.0,
    spend: 14200.0,
    clicks: 18340,
    conversions: 94,
    started_at: '2026-10-01T09:00:00Z',
    ended_at: '2026-10-31T23:59:59Z',
  },
  {
    id: 104,
    name: 'B2B Wholesale Catalog Search',
    platform: 'Google Ads',
    status: 'COMPLETED',
    budget: 30000.0,
    spend: 29850.0,
    clicks: 6450,
    conversions: 184,
    started_at: '2026-09-01T00:00:00Z',
    ended_at: '2026-09-30T23:59:59Z',
  },
]

const SAMPLE_TELEMETRY = [
  { date: '04 Nov', spend: 4200, clicks: 1120 },
  { date: '05 Nov', spend: 5100, clicks: 1340 },
  { date: '06 Nov', spend: 6300, clicks: 1720 },
  { date: '07 Nov', spend: 5800, clicks: 1510 },
  { date: '08 Nov', spend: 7200, clicks: 2100 },
  { date: '09 Nov', spend: 6900, clicks: 2240 },
  { date: '10 Nov', spend: 6650, clicks: 2450 },
]

const SAMPLE_CONVERSIONS = [
  {
    id: 201,
    conversion_type: 'PURCHASE',
    conversion_value: 14200.0,
    attribution_type: 'LAST_TOUCH',
    converted_at: '2026-11-09T18:40:00Z',
  },
  {
    id: 202,
    conversion_type: 'LEAD_SIGNUP',
    conversion_value: 0.0,
    attribution_type: 'FIRST_CLICK',
    converted_at: '2026-11-08T14:15:00Z',
  },
  {
    id: 203,
    conversion_type: 'ADD_TO_CART',
    conversion_value: 3500.0,
    attribution_type: 'LINEAR',
    converted_at: '2026-11-08T11:20:00Z',
  },
]

const SAMPLE_AD_SETS = [
  { id: 301, name: 'Dhaka Metro High Intent', status: 'ACTIVE', budget: 20000.0 },
  { id: 302, name: 'Chittagong Tier-1 Lookalikes', status: 'ACTIVE', budget: 15000.0 },
  { id: 303, name: 'Nationwide Broad 18-35', status: 'PAUSED', budget: 15000.0 },
]

const SAMPLE_CREATIVES = [
  { id: 401, external_id: 'CR-8921', type: 'IMAGE', title: 'Product Showcase Grid — Dhaka' },
  { id: 402, external_id: 'CR-8922', type: 'VIDEO', title: 'Customer Unboxing 15s Nationwide' },
]

export default function Growth({
  businessId,
  business,
  currentTab = 'campaigns',
  initialCampaigns = [],
  initialWebsite = null,
}) {
  const router = useRouter()
  const isWriter = WRITER_ROLES.has(business?.role)

  // Demo / Sample mode toggle
  const [sampleMode, setSampleMode] = useState(false)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [platformFilter, setPlatformFilter] = useState('ALL')

  // Campaign Detail Drawer
  const [selectedCampaign, setSelectedCampaign] = useState(null)
  const [isExplainLoading, setIsExplainLoading] = useState(false)
  const [explainResult, setExplainResult] = useState(null)
  const [explainError, setExplainError] = useState(null)

  // Website sub-navigation
  const [websiteSubTab, setWebsiteSubTab] = useState('visitors')

  // Visitor Journey Drawer (D19)
  const [selectedVisitor, setSelectedVisitor] = useState(null)
  const [visitorJourney, setVisitorJourney] = useState([])
  const [isJourneyLoading, setIsJourneyLoading] = useState(false)

  // Create Campaign Dialog
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState({
    name: '',
    platform: 'Google Ads',
    budget: '',
    started_at: '',
  })
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState(null)

  // Tabs
  const growthTabs = [
    { key: 'campaigns', label: 'Campaigns & Ads', href: `/business/${businessId}/growth/campaigns` },
    { key: 'website', label: 'Website & Visitors', href: `/business/${businessId}/growth/website` },
  ]

  // Data selection (real or simulated)
  const campaignsList = useMemo(() => {
    if (sampleMode) return SAMPLE_CAMPAIGNS
    return initialCampaigns || []
  }, [sampleMode, initialCampaigns])

  // Filtered campaigns
  const filteredCampaigns = useMemo(() => {
    return campaignsList.filter((camp) => {
      if (statusFilter !== 'ALL' && camp.status !== statusFilter) return false
      if (platformFilter !== 'ALL' && camp.platform !== platformFilter) return false
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        const nameMatch = (camp.name || '').toLowerCase().includes(q)
        const platformMatch = (camp.platform || '').toLowerCase().includes(q)
        if (!nameMatch && !platformMatch) return false
      }
      return true
    })
  }, [campaignsList, statusFilter, platformFilter, searchQuery])

  // Summary Metrics
  const summaryMetrics = useMemo(() => {
    let totalBudget = 0
    let totalSpend = 0
    let totalClicks = 0
    let totalConversions = 0

    campaignsList.forEach((c) => {
      totalBudget += Number(c.budget) || 0
      totalSpend += Number(c.spend) || 0
      totalClicks += Number(c.clicks) || 0
      totalConversions += Number(c.conversions) || 0
    })

    return { totalBudget, totalSpend, totalClicks, totalConversions }
  }, [campaignsList])

  // Fetch visitor journey when a visitor is clicked (D19)
  const handleOpenVisitorJourney = async (visitor) => {
    setSelectedVisitor(visitor)
    setIsJourneyLoading(true)
    setVisitorJourney([])

    if (sampleMode) {
      // Mocked chronological journey (oldest first)
      setTimeout(() => {
        setVisitorJourney([
          {
            id: 'j-1',
            title: 'Initial Landing: /shop/winter-collection',
            timestamp: '2026-10-24T09:00:00Z',
            icon: Globe,
            tone: 'neutral',
            metadata: { medium: 'cpc', source: 'google', campaign: 'winter_launch' },
          },
          {
            id: 'j-2',
            title: 'Product View: Handcrafted Leather Bag',
            timestamp: '2026-10-24T09:04:12Z',
            icon: Eye,
            tone: 'neutral',
            metadata: { product_id: '12', price: 'BDT 4,500.00' },
          },
          {
            id: 'j-3',
            title: 'Cart Addition',
            timestamp: '2026-10-24T09:08:45Z',
            icon: MousePointer,
            tone: 'neutral',
            metadata: { quantity: '1', item: 'Handcrafted Leather Bag' },
          },
          {
            id: 'j-4',
            title: 'Customer Authentication (LOGIN)',
            timestamp: '2026-10-24T09:12:00Z',
            icon: Users,
            tone: 'success',
            metadata: { customer_id: String(visitor.customer || 1) },
          },
        ])
        setIsJourneyLoading(false)
      }, 250)
      return
    }

    try {
      const res = await clientApi(`/api/backend/businesses/${businessId}/visitors/${visitor.id}/journey`)
      const rows = res?.results || (Array.isArray(res) ? res : [])
      // Sort oldest first per D19 specification
      const sorted = [...rows].sort(
        (a, b) => new Date(a.occurred_at || a.created_at) - new Date(b.occurred_at || b.created_at),
      )
      setVisitorJourney(
        sorted.map((ev) => ({
          id: ev.id,
          title: `Website Event: ${ev.event_type || 'PAGE_VIEW'}`,
          timestamp: ev.occurred_at || ev.created_at,
          icon: Globe,
          tone: ev.event_type === 'PURCHASE' ? 'success' : 'neutral',
          metadata: {
            page: ev.page_url || '—',
            event_type: ev.event_type,
            ...(ev.properties || {}),
          },
        })),
      )
    } catch (err) {
      console.error('Failed to load visitor journey', err)
      setVisitorJourney([])
    } finally {
      setIsJourneyLoading(false)
    }
  }

  // E6 AI Explain Campaign Performance
  const handleExplainCampaign = async (campaign) => {
    setIsExplainLoading(true)
    setExplainError(null)

    if (sampleMode || !campaign?.id) {
      setTimeout(() => {
        setExplainResult({
          calculated_roas: '3.18',
          target_roas: '2.50',
          attributed_orders_count: 482,
          attributed_revenue: '134037.00',
          net_revenue: '128400.00',
          customer_repeat_rate_pct: '24.6',
          top_products: ['Handcrafted Leather Bag (184 units)', 'Canvas Weekender Duffel (112 units)'],
          suggestions: [
            'Current ROAS exceeds target 2.50x by +27%: scale daily budget by 15% on high-converting Dhaka ad sets.',
            'Mobile cart dropoff is 18% higher on Meta traffic compared to Google search; audit checkout latency.',
            'Top-of-funnel discovery campaigns yield high CTR with low direct conversions; activate automated SMS re-engagement.',
          ],
          goals: ['Maintain blended ROAS >= 2.50x', 'Acquire 500+ verified customer profiles in Q4'],
        })
        setIsExplainLoading(false)
      }, 400)
      return
    }

    try {
      const res = await clientApi(`/api/backend/businesses/${businessId}/ai/marketing/explain-campaign`, {
        method: 'POST',
        body: { campaign_id: campaign.id },
      })
      setExplainResult(res)
    } catch (err) {
      setExplainError(err.detail || err.message || 'Unable to explain campaign performance.')
    } finally {
      setIsExplainLoading(false)
    }
  }

  // Create Campaign
  const handleCreateSubmit = async (e) => {
    e.preventDefault()
    setIsCreating(true)
    setCreateError(null)

    try {
      await clientApi(`/api/backend/businesses/${businessId}/campaigns`, {
        method: 'POST',
        body: {
          name: createForm.name,
          platform: createForm.platform,
          budget: String(createForm.budget),
          status: 'DRAFT',
          started_at: createForm.started_at ? new Date(createForm.started_at).toISOString() : null,
        },
      })
      setIsCreateOpen(false)
      router.refresh()
    } catch (err) {
      setCreateError(err.detail || err.message || 'Failed to create campaign.')
    } finally {
      setIsCreating(false)
    }
  }

  // Real website data from initialWebsite
  const websiteVisitors = initialWebsite?.visitors?.results || []
  const websiteSessions = initialWebsite?.sessions?.results || []
  const websiteEvents = initialWebsite?.events?.results || []

  return (
    <div className="workspace-page">
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspace' },
          { label: business?.name || 'Workspace', href: `/business/${businessId}/overview` },
          { label: 'Growth' },
        ]}
        title="Growth & Marketing"
        description="Omnichannel marketing campaign telemetry, ad spend attribution, and website visitor sessions."
        badge="Platform-reported"
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Button
              variant={sampleMode ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setSampleMode(!sampleMode)}
              aria-label="Toggle sample data"
            >
              {sampleMode ? 'Exit Sample Data' : 'Sample Data (SIMULATED)'}
            </Button>

            <Tooltip content={!isWriter ? 'Requires Operator role' : 'Create new campaign'}>
              <Button
                variant="primary"
                size="sm"
                icon={Plus}
                disabled={!isWriter}
                onClick={() => {
                  setCreateError(null)
                  setCreateForm({ name: '', platform: 'Google Ads', budget: '', started_at: '' })
                  setIsCreateOpen(true)
                }}
              >
                Create Campaign
              </Button>
            </Tooltip>
          </div>
        }
      />

      {sampleMode && (
        <Banner tone="info" className="mb-4">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <SimulatedBadge />
            <span>
              Previewing simulated campaign performance, conversions, and visitor session telemetry. Live
              database records are preserved.
            </span>
          </div>
        </Banner>
      )}

      <Tabs tabs={growthTabs} activeKey={currentTab} className="workspace-tabs" />

      {/* =========================================================================
          TAB 1: CAMPAIGNS & ADS
          ========================================================================= */}
      {currentTab === 'campaigns' && (
        <div className="stack section-gap">
          {/* Executive KPI Summary */}
          <div className="grid-kpi">
            <KpiTile
              label="Platform Spend (Platform-reported)"
              value={money(summaryMetrics.totalSpend)}
              subtext="Aggregated ad provider spend"
              icon={DollarSign}
            />
            <KpiTile
              label="Platform Clicks (Platform-reported)"
              value={summaryMetrics.totalClicks.toLocaleString()}
              subtext="Total inbound ad clicks"
              icon={MousePointer}
            />
            <KpiTile
              label="Conversions (Platform-reported)"
              value={summaryMetrics.totalConversions.toLocaleString()}
              subtext="First-party & provider tags"
              icon={CheckCircle2}
            />
            <UnavailableState
              owner="Business Intelligence"
              reason="Attribution models require an active provider contract."
              variant="compact"
            />
          </div>

          {/* Filters & Search Toolbar */}
          <div className="growth-toolbar">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                flex: '1 1 280px',
                flexWrap: 'wrap',
              }}
            >
              <Input
                type="search"
                placeholder="Search campaigns by name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search campaigns"
                style={{ flex: '1 1 180px', minWidth: '0' }}
              />
              <Select
                value={platformFilter}
                onChange={(e) => setPlatformFilter(e.target.value)}
                aria-label="Filter by advertising platform"
                style={{ width: '140px', flexShrink: 0 }}
              >
                <option value="ALL">All Platforms</option>
                <option value="Google Ads">Google Ads</option>
                <option value="Meta Ads">Meta Ads</option>
                <option value="TikTok Ads">TikTok Ads</option>
              </Select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', flexWrap: 'wrap' }}>
              {['ALL', 'ACTIVE', 'PAUSED', 'COMPLETED', 'DRAFT'].map((st) => (
                <Button
                  key={st}
                  variant={statusFilter === st ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => setStatusFilter(st)}
                >
                  {st === 'ALL' ? 'All Statuses' : st}
                </Button>
              ))}
            </div>
          </div>

          {/* Campaigns Table */}
          {filteredCampaigns.length === 0 ? (
            <EmptyState
              title="No campaigns found"
              description={
                searchQuery || statusFilter !== 'ALL'
                  ? 'No campaigns match the selected filters.'
                  : 'No marketing campaigns have been registered for this business yet.'
              }
              action={
                !sampleMode ? (
                  <Button variant="outline" size="sm" onClick={() => setSampleMode(true)}>
                    Preview with Sample Data (SIMULATED)
                  </Button>
                ) : null
              }
            />
          ) : (
            <DataTable
              rows={filteredCampaigns}
              columns={[
                {
                  key: 'name',
                  label: 'Campaign Name',
                  render: (row) => (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span className="font-semibold text-body">{row.name}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <span className="text-caption text-secondary">{row.platform}</span>
                        {sampleMode && <SimulatedBadge size="sm" />}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'platform',
                  label: 'Platform',
                  className: 'table-col-priority-low',
                  render: (row) => <span className="text-caption font-mono">{row.platform}</span>,
                },
                {
                  key: 'status',
                  label: 'Status',
                  render: (row) => <StatusChip status={row.status} size="sm" />,
                },
                {
                  key: 'budget',
                  label: 'Budget',
                  align: 'right',
                  render: (row) => <span className="font-mono text-body">{money(row.budget)}</span>,
                },
                {
                  key: 'spend',
                  label: 'Platform Spend',
                  align: 'right',
                  render: (row) => (
                    <span className="font-mono text-body font-semibold">{money(row.spend)}</span>
                  ),
                },
                {
                  key: 'clicks',
                  label: 'Clicks',
                  align: 'right',
                  className: 'table-col-priority-low',
                  render: (row) => (
                    <span className="font-mono text-body">{(row.clicks || 0).toLocaleString()}</span>
                  ),
                },
                {
                  key: 'started_at',
                  label: 'Period / Started',
                  className: 'table-col-priority-low',
                  render: (row) => (
                    <span className="text-caption text-secondary">
                      {row.started_at ? dateTime(row.started_at) : '—'}
                    </span>
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
                      icon={ArrowRight}
                      onClick={() => {
                        setSelectedCampaign(row)
                        setExplainResult(null)
                        setExplainError(null)
                      }}
                    >
                      View Details
                    </Button>
                  ),
                },
              ]}
            />
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 2: WEBSITE & VISITORS
          ========================================================================= */}
      {currentTab === 'website' && (
        <div className="stack section-gap">
          {/* Sub-view Navigation Bar */}
          <div className="timeline-switch-bar">
            <div className="timeline-segmented">
              <button
                type="button"
                className={`timeline-segmented-btn ${websiteSubTab === 'visitors' ? 'is-active' : ''}`}
                onClick={() => setWebsiteSubTab('visitors')}
              >
                <Users size={14} />
                Visitors ({websiteVisitors.length})
              </button>
              <button
                type="button"
                className={`timeline-segmented-btn ${websiteSubTab === 'sessions' ? 'is-active' : ''}`}
                onClick={() => setWebsiteSubTab('sessions')}
              >
                <Compass size={14} />
                Sessions ({websiteSessions.length})
              </button>
              <button
                type="button"
                className={`timeline-segmented-btn ${websiteSubTab === 'events' ? 'is-active' : ''}`}
                onClick={() => setWebsiteSubTab('events')}
              >
                <Activity size={14} />
                Events ({websiteEvents.length})
              </button>
              <button
                type="button"
                className={`timeline-segmented-btn ${websiteSubTab === 'analytics' ? 'is-active' : ''}`}
                onClick={() => setWebsiteSubTab('analytics')}
              >
                <BarChart2 size={14} />
                Performance Analytics (D7)
              </button>
            </div>
          </div>

          {/* Sub-view 1: Visitors */}
          {websiteSubTab === 'visitors' && (
            <div>
              {websiteVisitors.length === 0 ? (
                <EmptyState
                  title="No visitor records"
                  description="Website tracking script has not recorded any visitor identifiers yet."
                />
              ) : (
                <DataTable
                  rows={websiteVisitors}
                  columns={[
                    {
                      key: 'visitor_key',
                      label: 'Visitor Identifier',
                      render: (row) => (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <CopyableCode value={row.visitor_key} label="Visitor Key" />
                          {row.is_anonymous && (
                            <span className="text-caption text-secondary">(Anonymous)</span>
                          )}
                        </div>
                      ),
                    },
                    {
                      key: 'customer',
                      label: 'Linked Customer',
                      priority: 'low',
                      className: 'table-col-priority-low',
                      render: (row) =>
                        row.customer ? (
                          <Link
                            href={`/business/${businessId}/customers`}
                            className="font-medium text-primary hover:underline"
                          >
                            Customer #{row.customer}
                          </Link>
                        ) : (
                          <span className="text-muted">—</span>
                        ),
                    },
                    {
                      key: 'first_seen_at',
                      label: 'First Seen',
                      priority: 'low',
                      className: 'table-col-priority-low',
                      render: (row) => (
                        <span className="text-caption text-secondary">
                          {row.first_seen_at ? dateTime(row.first_seen_at) : '—'}
                        </span>
                      ),
                    },
                    {
                      key: 'last_seen_at',
                      label: 'Last Seen',
                      render: (row) => (
                        <span className="text-caption font-semibold">
                          {row.last_seen_at ? dateTime(row.last_seen_at) : '—'}
                        </span>
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
                          icon={Compass}
                          onClick={() => handleOpenVisitorJourney(row)}
                        >
                          View Journey
                        </Button>
                      ),
                    },
                  ]}
                />
              )}
            </div>
          )}

          {/* Sub-view 2: Sessions */}
          {websiteSubTab === 'sessions' && (
            <div>
              {websiteSessions.length === 0 ? (
                <EmptyState
                  title="No session records"
                  description="No web sessions have been logged by the tracking pipeline."
                />
              ) : (
                <DataTable
                  rows={websiteSessions}
                  columns={[
                    {
                      key: 'external_session_id',
                      label: 'Session ID',
                      render: (row) => (
                        <CopyableCode
                          value={row.external_session_id || `session-${row.id}`}
                          label="Session ID"
                        />
                      ),
                    },
                    {
                      key: 'traffic_source',
                      label: 'Traffic Source / Medium',
                      render: (row) => (
                        <span className="text-body font-mono">
                          {row.traffic_source || 'Direct'} / {row.traffic_medium || 'none'}
                        </span>
                      ),
                    },
                    {
                      key: 'device_type',
                      label: 'Device',
                      className: 'table-col-priority-low',
                      render: (row) => (
                        <span className="text-caption text-secondary">{row.device_type || 'Desktop'}</span>
                      ),
                    },
                    {
                      key: 'started_at',
                      label: 'Started At',
                      render: (row) => (
                        <span className="text-caption">
                          {row.started_at ? dateTime(row.started_at) : '—'}
                        </span>
                      ),
                    },
                    {
                      key: 'duration_seconds',
                      label: 'Duration',
                      align: 'right',
                      className: 'table-col-priority-low',
                      render: (row) => (
                        <span className="text-caption font-mono">
                          {row.duration_seconds != null ? duration(row.duration_seconds) : '—'}
                        </span>
                      ),
                    },
                    {
                      key: 'is_converted',
                      label: 'Converted',
                      align: 'right',
                      render: (row) => (
                        <StatusChip status={row.is_converted ? 'ACTIVE' : 'INACTIVE'} size="sm" />
                      ),
                    },
                  ]}
                />
              )}
            </div>
          )}

          {/* Sub-view 3: Events */}
          {websiteSubTab === 'events' && (
            <div>
              {websiteEvents.length === 0 ? (
                <EmptyState
                  title="No telemetry events"
                  description="Website interaction events have not been received."
                />
              ) : (
                <DataTable
                  rows={websiteEvents}
                  columns={[
                    {
                      key: 'event_type',
                      label: 'Event Type',
                      render: (row) => <StatusChip status={row.event_type} size="sm" />,
                    },
                    {
                      key: 'page_url',
                      label: 'Page URL',
                      render: (row) =>
                        row.page_url ? (
                          <CopyableCode value={row.page_url} label="URL" />
                        ) : (
                          <span className="text-muted">—</span>
                        ),
                    },
                    {
                      key: 'occurred_at',
                      label: 'Occurred At',
                      render: (row) => (
                        <span className="text-caption font-semibold">
                          {row.occurred_at ? dateTime(row.occurred_at) : '—'}
                        </span>
                      ),
                    },
                    {
                      key: 'currency',
                      label: 'Event Value',
                      align: 'right',
                      render: (row) => (
                        <span className="font-mono text-caption">
                          {row.event_value != null ? money(row.event_value, row.currency) : '—'}
                        </span>
                      ),
                    },
                  ]}
                />
              )}
            </div>
          )}

          {/* Sub-view 4: Performance Analytics (D7) */}
          {websiteSubTab === 'analytics' && (
            <div className="stack section-gap">
              <Banner tone="neutral">
                <span>
                  Authoritative web performance models and funnel drop-off metrics are computed by Business
                  Intelligence provider contracts.
                </span>
              </Banner>

              <div className="grid-2">
                <UnavailableState
                  owner="Business Intelligence"
                  reason="Traffic source attribution requires an active provider contract."
                />
                <UnavailableState
                  owner="Business Intelligence"
                  reason="Conversion funnel modeling requires an active provider contract."
                />
                <UnavailableState
                  owner="Business Intelligence"
                  reason="Cart abandonment analytics requires an active provider contract."
                />
                <UnavailableState
                  owner="Business Intelligence"
                  reason="Checkout drop-off telemetry requires an active provider contract."
                />
                <UnavailableState
                  owner="Business Intelligence"
                  reason="Landing page performance indexing requires an active provider contract."
                />
                <UnavailableState
                  owner="Business Intelligence"
                  reason="Device experience breakdown requires an active provider contract."
                />
                <UnavailableState
                  owner="Business Intelligence"
                  reason="Experience friction analysis requires an active provider contract."
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          CAMPAIGN DETAIL DRAWER
          ========================================================================= */}
      {selectedCampaign && (
        <Drawer
          isOpen={true}
          onClose={() => setSelectedCampaign(null)}
          title={`Campaign: ${selectedCampaign.name}`}
          size="lg"
        >
          <div className="stack section-gap">
            {/* Header badges */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              <StatusChip status={selectedCampaign.status} />
              <span className="font-mono text-caption text-secondary">{selectedCampaign.platform}</span>
              <CopyableCode value={String(selectedCampaign.id)} label="Campaign ID" />
              {sampleMode && <SimulatedBadge />}
            </div>

            {/* Quick KPI row */}
            <div className="grid-kpi">
              <KpiTile
                label="Budget"
                value={money(selectedCampaign.budget)}
                subtext="Campaign allocated total"
              />
              <KpiTile
                label="Spend (Platform-reported)"
                value={money(selectedCampaign.spend)}
                subtext="Ad provider aggregated"
              />
              <KpiTile
                label="Clicks (Platform-reported)"
                value={(selectedCampaign.clicks || 0).toLocaleString()}
                subtext="Total inbound clicks"
              />
            </div>

            {/* Attributed revenue tile */}
            <UnavailableState
              owner="Business Intelligence"
              reason="Attribution models require an active provider contract."
              variant="compact"
            />

            {/* Daily Telemetry Metrics: Two Small Charts (NEVER one chart with two axes) */}
            <div className="growth-detail-section">
              <h4>Daily Telemetry Trends (Platform-reported)</h4>
              <div className="growth-charts-grid">
                <ChartCard
                  title="Daily Platform Spend"
                  subtitle="Spend per day in BDT"
                  data={SAMPLE_TELEMETRY}
                  columns={[
                    { key: 'date', label: 'Date' },
                    { key: 'spend', label: 'Spend', format: (val) => money(val) },
                  ]}
                >
                  <TrendLine
                    data={SAMPLE_TELEMETRY}
                    dataKey="spend"
                    xKey="date"
                    color="var(--chart-1)"
                    height={180}
                  />
                </ChartCard>

                <ChartCard
                  title="Daily Platform Clicks"
                  subtitle="Inbound clicks per day"
                  data={SAMPLE_TELEMETRY}
                  columns={[
                    { key: 'date', label: 'Date' },
                    { key: 'clicks', label: 'Clicks', format: (val) => val.toLocaleString() },
                  ]}
                >
                  <TrendLine
                    data={SAMPLE_TELEMETRY}
                    dataKey="clicks"
                    xKey="date"
                    color="var(--chart-2)"
                    height={180}
                  />
                </ChartCard>
              </div>
            </div>

            {/* AI Campaign Performance Explanation (E6) */}
            <div className="growth-detail-section">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 'var(--space-3)',
                  flexWrap: 'wrap',
                }}
              >
                <h4>AI Campaign Performance Diagnosis (E6)</h4>
                <Button
                  variant="outline"
                  size="sm"
                  icon={Sparkles}
                  loading={isExplainLoading}
                  onClick={() => handleExplainCampaign(selectedCampaign)}
                >
                  {explainResult ? 'Refresh Diagnosis' : 'Explain Campaign Performance'}
                </Button>
              </div>

              {explainError && (
                <Banner tone="danger" className="mt-3">
                  <span>{explainError}</span>
                </Banner>
              )}

              {explainResult && (
                <div className="explain-campaign-box stack-sm">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <SimulatedBadge />
                    <span className="font-semibold text-caption text-secondary">
                      Execution is simulated — Advisory insight derived from platform telemetry
                    </span>
                  </div>

                  <div className="grid-kpi mt-2">
                    <KpiTile
                      label="Calculated ROAS"
                      value={`${explainResult.calculated_roas}x`}
                      subtext={`Target ROAS: ${explainResult.target_roas}x`}
                    />
                    <KpiTile
                      label="Attributed Orders"
                      value={explainResult.attributed_orders_count?.toString() || '0'}
                      subtext={`Net Rev: ${money(explainResult.net_revenue)}`}
                    />
                    <KpiTile
                      label="Repeat Customer Rate"
                      value={`${explainResult.customer_repeat_rate_pct}%`}
                      subtext="Attributed buyer repeat rate"
                    />
                  </div>

                  {explainResult.top_products && explainResult.top_products.length > 0 && (
                    <div className="mt-3">
                      <span className="font-semibold text-caption text-secondary">
                        Top Converting Products:
                      </span>
                      <ul
                        style={{ margin: 'var(--space-1) 0 0 var(--space-4)', fontSize: 'var(--text-body)' }}
                      >
                        {explainResult.top_products.map((tp, idx) => (
                          <li key={idx}>{tp}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {explainResult.suggestions && explainResult.suggestions.length > 0 && (
                    <div className="mt-3">
                      <span className="font-semibold text-caption text-secondary">Strategic Next Steps:</span>
                      <ul
                        style={{ margin: 'var(--space-1) 0 0 var(--space-4)', fontSize: 'var(--text-body)' }}
                      >
                        {explainResult.suggestions.map((sug, idx) => (
                          <li key={idx} style={{ marginBottom: 'var(--space-1)' }}>
                            {sug}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Platform-reported Conversions */}
            <div className="growth-detail-section">
              <h4>Platform-reported Conversions</h4>
              <DataTable
                rows={SAMPLE_CONVERSIONS}
                columns={[
                  {
                    key: 'conversion_type',
                    label: 'Conversion Type',
                    render: (row) => <StatusChip status={row.conversion_type} size="sm" />,
                  },
                  {
                    key: 'conversion_value',
                    label: 'Attributed Value',
                    align: 'right',
                    render: (row) => <span className="font-mono">{money(row.conversion_value)}</span>,
                  },
                  {
                    key: 'attribution_type',
                    label: 'Attribution Model',
                    render: (row) => <span className="text-caption font-mono">{row.attribution_type}</span>,
                  },
                  {
                    key: 'converted_at',
                    label: 'Recorded At',
                    render: (row) => <span className="text-caption">{dateTime(row.converted_at)}</span>,
                  },
                ]}
              />
            </div>

            {/* Ad Sets & Creatives */}
            <div className="growth-detail-section">
              <h4>Ad Sets & Creatives</h4>
              <div className="grid-2">
                <div>
                  <span className="font-semibold text-caption text-secondary">Ad Sets</span>
                  <ul className="stack-sm mt-2" style={{ listStyle: 'none', padding: 0 }}>
                    {SAMPLE_AD_SETS.map((as) => (
                      <li
                        key={as.id}
                        className="journey-card"
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                      >
                        <span className="font-medium text-body">{as.name}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <StatusChip status={as.status} size="sm" />
                          <span className="font-mono text-caption">{money(as.budget)}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <span className="font-semibold text-caption text-secondary">Active Creatives</span>
                  <ul className="stack-sm mt-2" style={{ listStyle: 'none', padding: 0 }}>
                    {SAMPLE_CREATIVES.map((cr) => (
                      <li key={cr.id} className="journey-card">
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <CopyableCode value={cr.external_id} label="Creative" />
                          <span className="text-caption font-mono">({cr.type})</span>
                        </div>
                        <p className="text-caption text-secondary mt-1">{cr.title}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </Drawer>
      )}

      {/* =========================================================================
          VISITOR JOURNEY DRAWER (D19)
          ========================================================================= */}
      {selectedVisitor && (
        <Drawer
          isOpen={true}
          onClose={() => setSelectedVisitor(null)}
          title={`Visitor Journey: ${selectedVisitor.visitor_key}`}
          size="md"
        >
          <div className="stack section-gap">
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              <CopyableCode value={selectedVisitor.visitor_key} label="Visitor Key" />
              {selectedVisitor.is_anonymous ? (
                <span className="text-caption text-secondary">(Anonymous session)</span>
              ) : (
                <span className="text-caption text-primary">Identified Visitor</span>
              )}
            </div>

            <div className="grid-kpi">
              <KpiTile
                label="First Seen"
                value={selectedVisitor.first_seen_at ? dateTime(selectedVisitor.first_seen_at) : '—'}
                subtext="Initial session entry"
              />
              <KpiTile
                label="Last Seen"
                value={selectedVisitor.last_seen_at ? dateTime(selectedVisitor.last_seen_at) : '—'}
                subtext="Most recent touchpoint"
              />
            </div>

            <div className="growth-detail-section">
              <h4>Chronological Visitor Journey (D19, oldest first)</h4>
              {isJourneyLoading ? (
                <div className="text-caption text-secondary">Loading visitor journey timeline...</div>
              ) : visitorJourney.length === 0 ? (
                <EmptyState
                  title="No journey events recorded"
                  description="No web telemetry events are associated with this visitor identifier."
                />
              ) : (
                <Timeline events={visitorJourney} />
              )}
            </div>
          </div>
        </Drawer>
      )}

      {/* =========================================================================
          CREATE CAMPAIGN DIALOG
          ========================================================================= */}
      <Dialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Advertising Campaign"
        confirmLabel="Create Campaign"
        onConfirm={handleCreateSubmit}
        isLoading={isCreating}
      >
        <form onSubmit={handleCreateSubmit} className="stack-sm">
          {createError && (
            <Banner tone="danger">
              <span>{createError}</span>
            </Banner>
          )}

          <Field label="Campaign Name" required htmlFor="create-camp-name">
            <Input
              id="create-camp-name"
              aria-label="Campaign Name"
              placeholder="e.g. Q4 Winter Omnichannel Launch"
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              required
            />
          </Field>

          <Field label="Advertising Platform" required htmlFor="create-camp-platform">
            <Select
              id="create-camp-platform"
              aria-label="Advertising Platform"
              value={createForm.platform}
              onChange={(e) => setCreateForm({ ...createForm, platform: e.target.value })}
            >
              <option value="Google Ads">Google Ads</option>
              <option value="Meta Ads">Meta Ads</option>
              <option value="TikTok Ads">TikTok Ads</option>
              <option value="LinkedIn Ads">LinkedIn Ads</option>
              <option value="Other">Other</option>
            </Select>
          </Field>

          <Field label="Allocated Budget (BDT)" required htmlFor="create-camp-budget">
            <Input
              id="create-camp-budget"
              aria-label="Allocated Budget"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="e.g. 50000.00"
              value={createForm.budget}
              onChange={(e) => setCreateForm({ ...createForm, budget: e.target.value })}
              required
            />
          </Field>

          <Field label="Start Date (Optional)" htmlFor="create-camp-start">
            <Input
              id="create-camp-start"
              aria-label="Start Date"
              type="datetime-local"
              value={createForm.started_at}
              onChange={(e) => setCreateForm({ ...createForm, started_at: e.target.value })}
            />
          </Field>
        </form>
      </Dialog>
    </div>
  )
}
