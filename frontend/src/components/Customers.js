'use client'

import React, { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import {
  Users,
  User,
  Mail,
  Phone,
  Tag,
  ShoppingBag,
  MessageSquare,
  Truck,
  Globe,
  Share2,
  Shield,
  AlertCircle,
  CheckCircle2,
  Clock,
  ExternalLink,
  Edit3,
  Layers,
  Sparkles,
  ArrowRight,
  RotateCcw,
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
  CopyableCode,
  Timeline,
  Banner,
  KpiTile,
  Tabs,
} from '@/components/ui'
import { businessPath, businessApiPath, WRITER_ROLES } from '@/lib/catalog'
import { money, dateTime, relativeTime } from '@/lib/format'
import { clientApi } from '@/lib/clientApi'

// Legal transitions for Customer lifecycle per D4
const CUSTOMER_TRANSITIONS = {
  ACTIVE: ['INACTIVE', 'BLOCKED'],
  INACTIVE: ['ACTIVE', 'BLOCKED'],
  BLOCKED: ['ACTIVE'],
}

// Sub-tabs for Customer 360 view
const SUB_TABS_360 = [
  { id: 'timeline', label: 'Timeline', icon: Clock },
  { id: 'orders', label: 'Orders', icon: ShoppingBag },
  { id: 'conversations', label: 'Conversations', icon: MessageSquare },
  { id: 'deliveries', label: 'Deliveries', icon: Truck },
  { id: 'website', label: 'Website & Events', icon: Globe },
  { id: 'graph', label: 'Context Graph', icon: Share2 },
  { id: 'identity', label: 'Identities & Links', icon: Shield },
]

export default function Customers({
  business = {},
  businessId,
  activeTab = 'list',
  customersData,
  initialCustomer360 = null,
  initialGraphContext = null,
  issues = [],
}) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const currency = business?.currency || 'BDT'
  const timezone = business?.timezone || 'Asia/Dhaka'
  const canWrite = WRITER_ROLES.has(business?.role)

  // Directory filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')

  // Selected customer for 360 view
  const [selectedCustomer, setSelectedCustomer] = useState(initialCustomer360?.customer || null)
  const [customer360Data, setCustomer360Data] = useState(initialCustomer360)
  const [graphContextData, setGraphContextData] = useState(initialGraphContext)
  const [loading360, setLoading360] = useState(false)
  const [error360, setError360] = useState('')

  // Active sub-tab inside 360
  const [active360SubTab, setActive360SubTab] = useState('timeline')

  // Status transition dialog state
  const [statusModalOpen, setStatusModalOpen] = useState(false)
  const [targetStatus, setTargetStatus] = useState('')
  const [transitionReason, setTransitionReason] = useState('')
  const [transitioning, setTransitioning] = useState(false)
  const [transitionMessage, setTransitionMessage] = useState({ type: '', text: '' })

  const allCustomers = customersData?.results || (Array.isArray(customersData) ? customersData : [])

  // Listen for `?open=customers:id` or `?id=id` to open 360
  useEffect(() => {
    const openParam = searchParams.get('open')
    const idParam = searchParams.get('id')
    let custId = null

    if (openParam && openParam.startsWith('customers:')) {
      custId = openParam.split(':')[1]
    } else if (idParam) {
      custId = idParam
    }

    if (custId) {
      if (customer360Data?.customer && String(customer360Data.customer.id) === String(custId)) {
        return
      }

      setLoading360(true)
      setError360('')

      Promise.all([
        clientApi(`businesses/${businessId}/customers/${custId}/360`),
        clientApi(`businesses/${businessId}/graph-context/customer/${custId}`).catch(() => null),
      ])
        .then(([c360, gCtx]) => {
          setCustomer360Data(c360)
          setSelectedCustomer(c360.customer)
          setGraphContextData(gCtx)
        })
        .catch((err) => {
          setError360(err.message || 'Failed to load customer 360 profile.')
        })
        .finally(() => {
          setLoading360(false)
        })
    }
  }, [searchParams, businessId, customer360Data])

  // Select customer from list to view 360
  const handleSelectCustomer = (customer) => {
    setSelectedCustomer(customer)
    const params = new URLSearchParams(searchParams.toString())
    params.set('open', `customers:${customer.id}`)
    router.push(`${pathname}?${params.toString()}`, { scroll: false })
  }

  // Close 360 view back to full directory
  const handleBackToDirectory = () => {
    setSelectedCustomer(null)
    setCustomer360Data(null)
    setGraphContextData(null)
    const params = new URLSearchParams(searchParams.toString())
    params.delete('open')
    params.delete('id')
    const qs = params.toString()
    router.push(`${pathname}${qs ? `?${qs}` : ''}`, { scroll: false })
  }

  // Execute D4 status transition
  const handleExecuteStatusTransition = async (e) => {
    e.preventDefault()
    if (!selectedCustomer || !targetStatus) return

    setTransitioning(true)
    setTransitionMessage({ type: '', text: '' })

    try {
      const updated = await clientApi(
        `businesses/${businessId}/customers/${selectedCustomer.id}/transition`,
        {
          method: 'POST',
          body: {
            status: targetStatus,
            reason: transitionReason || 'Operational status adjustment',
            expected_status: selectedCustomer.status,
          },
        },
      )

      setTransitionMessage({
        type: 'success',
        text: `Customer status changed to ${targetStatus}.`,
      })
      setSelectedCustomer((prev) => ({ ...prev, ...updated }))
      if (customer360Data?.customer) {
        setCustomer360Data((prev) => ({
          ...prev,
          customer: { ...prev.customer, ...updated },
        }))
      }

      setTimeout(() => {
        setStatusModalOpen(false)
        router.refresh()
      }, 1200)
    } catch (err) {
      if (err.status === 409 || err.code === 'STALE_STATE') {
        setTransitionMessage({
          type: 'error',
          text: 'This record changed on the server. Reloaded latest state.',
        })
        // Reload
        clientApi(`businesses/${businessId}/customers/${selectedCustomer.id}/360`).then((c360) => {
          setCustomer360Data(c360)
          setSelectedCustomer(c360.customer)
        })
      } else {
        setTransitionMessage({
          type: 'error',
          text: err.detail || err.message || 'Status transition failed.',
        })
      }
    } finally {
      setTransitioning(false)
    }
  }

  // Filter customers by search and status
  const filteredCustomers = useMemo(() => {
    return allCustomers.filter((cust) => {
      const name = (
        cust.display_name ||
        cust.name ||
        `${cust.first_name || ''} ${cust.last_name || ''}`
      ).toLowerCase()
      const matchesSearch =
        !searchQuery ||
        name.includes(searchQuery.toLowerCase()) ||
        String(cust.id).includes(searchQuery) ||
        (cust.email && cust.email.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (cust.phone && cust.phone.includes(searchQuery))

      const matchesStatus = statusFilter === 'ALL' || (cust.status || '').toUpperCase() === statusFilter

      return matchesSearch && matchesStatus
    })
  }, [allCustomers, searchQuery, statusFilter])

  // Columns for Customers directory table
  const customerColumns = [
    {
      key: 'name',
      label: 'Customer Name',
      render: (row) => {
        const displayName =
          row.display_name ||
          row.name ||
          `${row.first_name || ''} ${row.last_name || ''}`.trim() ||
          `Customer #${row.id}`
        const initial = displayName.charAt(0).toUpperCase()
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 'var(--radius-full)',
                background: 'var(--color-primary-subtle)',
                color: 'var(--color-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                fontSize: 12,
                flexShrink: 0,
              }}
            >
              {initial}
            </div>
            <div>
              <span className="font-semibold text-body">{displayName}</span>
              <span className="font-mono text-caption text-muted ml-2">#{row.id}</span>
            </div>
          </div>
        )
      },
    },
    {
      key: 'primary_contact',
      label: 'Primary Contact',
      render: (row) => {
        const contact = row.phone || row.email || row.primary_contact
        return contact ? (
          <span className="text-secondary font-mono text-caption">{contact}</span>
        ) : (
          <span className="text-muted">—</span>
        )
      },
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusChip status={row.status} record={row} size="sm" />,
    },
    {
      key: 'created_at',
      label: 'Registered',
      render: (row) => (
        <span className="tabular-nums text-caption text-secondary" title={row.created_at}>
          {dateTime(row.created_at, timezone)}
        </span>
      ),
    },
  ]

  // Calculated 360 KPIs
  const customerOrders = customer360Data?.orders?.results || []
  const totalSpend = useMemo(() => {
    return customerOrders.reduce((sum, ord) => sum + Number(ord.total_amount || 0), 0)
  }, [customerOrders])

  // Customer open issues
  const customerIssues = useMemo(() => {
    if (!selectedCustomer) return []
    return issues.filter(
      (iss) =>
        iss.subject_entity_type === 'CUSTOMER' &&
        String(iss.subject_entity_id) === String(selectedCustomer.id),
    )
  }, [issues, selectedCustomer])

  // Unified timeline items
  const timelineEvents = useMemo(() => {
    if (!customer360Data) return []
    const events = []

    // Direct timeline entries if available from backend
    if (customer360Data.timeline?.results?.length > 0) {
      customer360Data.timeline.results.forEach((ev) => {
        const ts = ev.event_at || ev.created_at
        events.push({
          date: ts,
          timestamp: ts,
          title: ev.title || ev.kind || 'Activity Event',
          description: ev.description || ev.summary,
          status: ev.status || 'COMPLETED',
        })
      })
    } else {
      // Synthesize unified timeline from child sections
      customerOrders.forEach((ord) => {
        events.push({
          date: ord.created_at,
          timestamp: ord.created_at,
          title: `Order Placed (#${ord.id})`,
          description: `Total amount: ${money(ord.total_amount, currency)} · Status: ${ord.status}`,
          status: ord.status === 'DELIVERED' ? 'COMPLETED' : 'ACTIVE',
        })
      })

      if (customer360Data.conversations?.results) {
        customer360Data.conversations.results.forEach((conv) => {
          const ts = conv.started_at || conv.created_at
          events.push({
            date: ts,
            timestamp: ts,
            title: `Support Conversation (#${conv.id})`,
            description: `Channel: ${conv.channel || 'Messaging'} · Priority: ${conv.priority || 'NORMAL'}`,
            status: conv.status === 'RESOLVED' ? 'COMPLETED' : 'ACTIVE',
          })
        })
      }

      if (customer360Data.shipments?.results) {
        customer360Data.shipments.results.forEach((sh) => {
          events.push({
            date: sh.created_at,
            timestamp: sh.created_at,
            title: `Shipment Consignment (#${sh.id})`,
            description: `Carrier: ${sh.provider || 'Carrier'} · Tracking: ${sh.tracking_code || 'Pending'}`,
            status: sh.status === 'DELIVERED' ? 'COMPLETED' : 'ACTIVE',
          })
        })
      }
    }

    // Sort newest first
    return events.sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0))
  }, [customer360Data, customerOrders, currency])

  const availableStatusChoices = selectedCustomer ? CUSTOMER_TRANSITIONS[selectedCustomer.status] || [] : []

  return (
    <div className="customers-container stack-lg">
      {/* VIEW 1: DIRECTORY LIST (when no customer selected) */}
      {!selectedCustomer && (
        <section className="surface card-padding stack-sm" aria-labelledby="customers-dir-title">
          <div className="section-header">
            <div>
              <h2 id="customers-dir-title" className="section-title">
                Customer Directory
              </h2>
              <p className="section-desc">
                Authoritative customer master identities, contact methods, and status.
              </p>
            </div>
            <span className="count-chip font-mono">
              {filteredCustomers.length} {filteredCustomers.length === 1 ? 'customer' : 'customers'}
            </span>
          </div>

          {/* Search bar and status chips */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 'var(--space-3)',
              flexWrap: 'wrap',
              marginBottom: 'var(--space-3)',
            }}
          >
            <div className="quick-filter-chips" role="group" aria-label="Filter by customer status">
              {['ALL', 'ACTIVE', 'INACTIVE', 'BLOCKED'].map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => setStatusFilter(st)}
                  className={`domain-chip-btn ${statusFilter === st ? 'is-active' : ''}`}
                  aria-pressed={statusFilter === st}
                >
                  {st === 'ALL' ? 'All Customers' : st}
                </button>
              ))}
            </div>

            <div style={{ minWidth: 240 }}>
              <Input
                type="search"
                placeholder="Search customers by name, phone, email…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search customers"
              />
            </div>
          </div>

          <DataTable
            columns={customerColumns}
            rows={filteredCustomers}
            businessId={business.id}
            resource="customers"
            onRowClick={handleSelectCustomer}
            openInDrawer={false}
            emptyTitle="No customers found"
            emptyDescription={
              searchQuery || statusFilter !== 'ALL'
                ? 'No customers match the active filters.'
                : 'No customers are registered in this business.'
            }
          />
        </section>
      )}

      {/* VIEW 2: CUSTOMER 360 PROFILE (when customer is selected) */}
      {selectedCustomer && (
        <div className="stack-lg">
          {/* Back Navigation Bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <button
              type="button"
              onClick={handleBackToDirectory}
              className="button button-secondary button-sm"
            >
              <span>← Back to Customer Directory</span>
            </button>
            <span className="text-caption text-muted">Authoritative Customer 360 View</span>
          </div>

          {/* Customer Profile Header Card */}
          <section className="customer-profile-card">
            <div className="customer-info-group">
              <div className="customer-avatar-large">
                {(selectedCustomer.display_name || selectedCustomer.name || 'C').charAt(0).toUpperCase()}
              </div>

              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  <h2 className="section-title" style={{ margin: 0 }}>
                    {selectedCustomer.display_name ||
                      selectedCustomer.name ||
                      `${selectedCustomer.first_name || ''} ${selectedCustomer.last_name || ''}`.trim() ||
                      `Customer #${selectedCustomer.id}`}
                  </h2>
                  <span className="font-mono text-caption text-muted">#{selectedCustomer.id}</span>
                  <StatusChip status={selectedCustomer.status} size="sm" />
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    marginTop: 'var(--space-1)',
                    flexWrap: 'wrap',
                  }}
                >
                  {selectedCustomer.phone && (
                    <span
                      className="text-caption text-secondary"
                      style={{ display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                      <Phone size={12} aria-hidden="true" />
                      <span>{selectedCustomer.phone}</span>
                    </span>
                  )}
                  {selectedCustomer.email && (
                    <span
                      className="text-caption text-secondary"
                      style={{ display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                      <Mail size={12} aria-hidden="true" />
                      <span>{selectedCustomer.email}</span>
                    </span>
                  )}
                  <span className="text-caption text-muted">
                    Registered {dateTime(selectedCustomer.created_at, timezone)}
                  </span>
                </div>
              </div>
            </div>

            {/* Actions: Change Status */}
            {canWrite && availableStatusChoices.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setTargetStatus('')
                  setTransitionReason('')
                  setTransitionMessage({ type: '', text: '' })
                  setStatusModalOpen(true)
                }}
              >
                <Edit3 size={14} aria-hidden="true" />
                <span>Change Status</span>
              </Button>
            )}
          </section>

          {/* Quick Metrics Grid */}
          <div className="grid-kpi">
            <KpiTile title="Total Orders" value={customerOrders.length} subtext="Lifetime placed orders" />
            <KpiTile
              title="Lifetime Spend"
              value={money(totalSpend, currency)}
              subtext="Settled purchase value"
            />
            <KpiTile
              title="Conversations"
              value={customer360Data?.conversations?.results?.length ?? 0}
              subtext="Support tickets & inquiries"
            />
            <KpiTile
              title="Linked Identities"
              value={
                (customer360Data?.identities?.results?.length ?? 0) +
                (customer360Data?.external_identities?.results?.length ?? 0)
              }
              subtext="Resolved touchpoint identifiers"
            />
          </div>

          {/* 360 Sub-Navigation & Main Workspace */}
          <div className="grid-main-aside">
            {/* Main Area: Sub-Tabs Content */}
            <div className="surface card-padding stack-sm">
              {/* 360 Sub-Tabs Navigation */}
              <Tabs
                tabs={SUB_TABS_360}
                activeTab={active360SubTab}
                onChange={setActive360SubTab}
                ariaLabel="Customer 360 sub-views"
                style={{ marginBottom: 'var(--space-4)' }}
              />

              {/* SUB-TAB 1: TIMELINE */}
              {active360SubTab === 'timeline' && (
                <div className="stack-sm">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Customer Interaction Timeline</h3>
                      <p className="section-desc">
                        Chronological audit stream of touchpoints, purchases, and communications.
                      </p>
                    </div>
                  </div>

                  {timelineEvents.length > 0 ? (
                    <Timeline events={timelineEvents} />
                  ) : (
                    <EmptyState
                      title="No timeline events"
                      description="Interaction events will appear chronologically here."
                    />
                  )}
                </div>
              )}

              {/* SUB-TAB 2: ORDERS */}
              {active360SubTab === 'orders' && (
                <div className="stack-sm">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Order History</h3>
                      <p className="section-desc">All-time orders placed by this customer.</p>
                    </div>
                  </div>

                  <DataTable
                    columns={[
                      {
                        key: 'id',
                        label: 'Order ID',
                        render: (row) => <span className="font-mono font-semibold">#{row.id}</span>,
                      },
                      {
                        key: 'total_amount',
                        label: 'Total',
                        type: 'money',
                        currency,
                      },
                      {
                        key: 'status',
                        label: 'Status',
                        render: (row) => <StatusChip status={row.status} size="sm" />,
                      },
                      {
                        key: 'created_at',
                        label: 'Placed Date',
                        render: (row) => (
                          <span className="tabular-nums text-caption text-secondary">
                            {dateTime(row.created_at, timezone)}
                          </span>
                        ),
                      },
                    ]}
                    rows={customerOrders}
                    businessId={business.id}
                    emptyTitle="No orders placed"
                    emptyDescription="Customer has not placed any orders yet."
                    openInDrawer={false}
                  />
                </div>
              )}

              {/* SUB-TAB 3: CONVERSATIONS */}
              {active360SubTab === 'conversations' && (
                <div className="stack-sm">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Support Conversations</h3>
                      <p className="section-desc">Support tickets and messaging threads.</p>
                    </div>
                  </div>

                  <DataTable
                    columns={[
                      {
                        key: 'id',
                        label: 'Ticket ID',
                        render: (row) => <span className="font-mono font-semibold">#{row.id}</span>,
                      },
                      {
                        key: 'channel',
                        label: 'Channel',
                        render: (row) => <span className="text-secondary">{row.channel || 'Chat'}</span>,
                      },
                      {
                        key: 'priority',
                        label: 'Priority',
                        render: (row) => (
                          <span className="badge badge-outline text-caption font-mono">
                            {row.priority || 'NORMAL'}
                          </span>
                        ),
                      },
                      {
                        key: 'status',
                        label: 'Status',
                        render: (row) => <StatusChip status={row.status} size="sm" />,
                      },
                      {
                        key: 'created_at',
                        label: 'Started At',
                        render: (row) => (
                          <span className="tabular-nums text-caption text-secondary">
                            {dateTime(row.created_at, timezone)}
                          </span>
                        ),
                      },
                    ]}
                    rows={customer360Data?.conversations?.results || []}
                    businessId={business.id}
                    emptyTitle="No conversations found"
                    emptyDescription="No support tickets recorded for this customer."
                    openInDrawer={false}
                  />
                </div>
              )}

              {/* SUB-TAB 4: DELIVERIES */}
              {active360SubTab === 'deliveries' && (
                <div className="stack-sm">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Fulfillment Shipments</h3>
                      <p className="section-desc">Carrier packages dispatched to this customer.</p>
                    </div>
                  </div>

                  <DataTable
                    columns={[
                      {
                        key: 'id',
                        label: 'Shipment ID',
                        render: (row) => <span className="font-mono font-semibold">#{row.id}</span>,
                      },
                      {
                        key: 'provider',
                        label: 'Carrier',
                        render: (row) => <span>{row.provider || 'Carrier Service'}</span>,
                      },
                      {
                        key: 'tracking_code',
                        label: 'Tracking Number',
                        render: (row) =>
                          row.tracking_code ? (
                            <CopyableCode value={row.tracking_code} />
                          ) : (
                            <span className="text-muted">—</span>
                          ),
                      },
                      {
                        key: 'status',
                        label: 'Status',
                        render: (row) => <StatusChip status={row.status} size="sm" />,
                      },
                    ]}
                    rows={customer360Data?.shipments?.results || []}
                    businessId={business.id}
                    emptyTitle="No shipments dispatched"
                    emptyDescription="No carrier consignments recorded for this customer."
                    openInDrawer={false}
                  />
                </div>
              )}

              {/* SUB-TAB 5: WEBSITE */}
              {active360SubTab === 'website' && (
                <div className="stack-sm">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Website Activity &amp; Sessions</h3>
                      <p className="section-desc">Storefront visitor sessions and clickstream events.</p>
                    </div>
                  </div>

                  <DataTable
                    columns={[
                      {
                        key: 'id',
                        label: 'Session ID',
                        render: (row) => <span className="font-mono text-caption">#{row.id}</span>,
                      },
                      {
                        key: 'started_at',
                        label: 'Visit Time',
                        render: (row) => (
                          <span className="tabular-nums text-caption text-secondary">
                            {dateTime(row.started_at, timezone)}
                          </span>
                        ),
                      },
                      {
                        key: 'device',
                        label: 'Device',
                        render: (row) => <span>{row.device || 'Web Browser'}</span>,
                      },
                    ]}
                    rows={customer360Data?.sessions?.results || []}
                    businessId={business.id}
                    emptyTitle="No web sessions recorded"
                    emptyDescription="Visitor sessions will appear when tracking is connected."
                    openInDrawer={false}
                  />
                </div>
              )}

              {/* SUB-TAB 6: CONTEXT GRAPH */}
              {active360SubTab === 'graph' && (
                <div className="stack-sm">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Customer Context Graph</h3>
                      <p className="section-desc">
                        Persisted one-hop graph topology connecting customer, orders, and identities.
                      </p>
                    </div>
                  </div>

                  {graphContextData?.status === 'AVAILABLE' &&
                  graphContextData?.nodes?.results?.length > 0 ? (
                    <div className="graph-node-list">
                      {graphContextData.nodes.results.map((node) => (
                        <div key={node.id} className="graph-node-item">
                          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <span className="badge badge-outline font-mono text-caption">
                              {node.entity_type}
                            </span>
                            <span className="font-semibold text-body">
                              {node.label || `${node.entity_type} #${node.entity_id}`}
                            </span>
                          </div>
                          <span className="graph-edge-tag">One-Hop Connected</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <UnavailableState
                      owner="Business Graph"
                      reason="Persisted one-hop context graph is not yet initialized for this customer entity."
                    />
                  )}
                </div>
              )}

              {/* SUB-TAB 7: IDENTITIES & LINKS */}
              {active360SubTab === 'identity' && (
                <div className="stack-sm">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">Resolved Identities &amp; Provider Links</h3>
                      <p className="section-desc">
                        External channel accounts resolved to this canonical customer entity.
                      </p>
                    </div>
                  </div>

                  <div className="customer-identity-grid">
                    {/* Primary Canonical Identity */}
                    <div className="identity-card">
                      <div className="identity-card-header">
                        <span className="font-semibold text-body">Canonical Identity</span>
                        <StatusChip status="ACTIVE" label="Authoritative" size="sm" />
                      </div>
                      <CopyableCode value={`CUSTOMER:${selectedCustomer.id}`} />
                      <span className="text-caption text-muted">Primary entity record in PostgreSQL</span>
                    </div>

                    {/* External Linked Identities */}
                    {customer360Data?.external_identities?.results?.map((ext) => (
                      <div key={ext.id} className="identity-card">
                        <div className="identity-card-header">
                          <span className="font-semibold text-body">{ext.provider || 'Channel'}</span>
                          <span className="text-caption font-mono text-secondary">
                            Confidence: {ext.confidence != null ? `${ext.confidence}%` : '—'}
                          </span>
                        </div>
                        <CopyableCode value={ext.identifier || ext.external_id || String(ext.id)} />
                        <span className="text-caption text-muted">
                          Source: {ext.source || 'Deterministic Ingestion'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Aside Column: Open Issues & AI Customer Context */}
            <div className="stack">
              {/* Open Issues Block */}
              <section className="surface card-padding stack-sm" aria-labelledby="cust-issues-title">
                <div className="section-header">
                  <div>
                    <h3 id="cust-issues-title" className="section-title">
                      Customer Integrity Alerts
                    </h3>
                    <p className="section-desc">Automated rules &amp; fulfillment exceptions</p>
                  </div>
                  <span className="count-chip font-mono">{customerIssues.length}</span>
                </div>

                {customerIssues.length > 0 ? (
                  <div className="stack-sm">
                    {customerIssues.map((iss) => (
                      <div
                        key={iss.id}
                        style={{
                          padding: 'var(--space-2) var(--space-3)',
                          border: '1px solid var(--color-border)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <div
                          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                        >
                          <span className="font-semibold text-caption">{iss.title}</span>
                          <SeverityChip severity={iss.severity} size="sm" />
                        </div>
                        <span className="font-mono text-caption text-muted">{iss.rule_key}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state" style={{ padding: 'var(--space-3)' }}>
                    <CheckCircle2 size={20} className="text-success" aria-hidden="true" />
                    <span className="text-caption text-secondary" style={{ marginTop: 4 }}>
                      No open integrity issues detected for this customer.
                    </span>
                  </div>
                )}
              </section>

              {/* AI Customer Context (Honest calm UnavailableState per project law) */}
              <section className="surface card-padding stack-sm" aria-labelledby="ai-ctx-title">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <SimulatedBadge text="SIMULATED" />
                  <span className="text-caption text-muted">AI Intelligence</span>
                </div>

                <div>
                  <h3
                    id="ai-ctx-title"
                    className="section-title"
                    style={{ fontSize: 'var(--text-card-title)' }}
                  >
                    AI Customer Summary
                  </h3>
                  <p className="section-desc">Automated behavioural synthesis</p>
                </div>

                <UnavailableState
                  owner="AI Intelligence"
                  reason="AI customer context summarization is not connected."
                />
              </section>
            </div>
          </div>
        </div>
      )}

      {/* CUSTOMER STATUS CHANGE DIALOG (D4) */}
      <Dialog
        isOpen={statusModalOpen}
        onClose={() => setStatusModalOpen(false)}
        title="Change Customer State"
        subtitle={`Enforces legal transition rules for Customer #${selectedCustomer?.id}`}
      >
        <form onSubmit={handleExecuteStatusTransition} className="stack-sm">
          {transitionMessage.text && (
            <Banner variant={transitionMessage.type === 'error' ? 'danger' : 'success'}>
              {transitionMessage.text}
            </Banner>
          )}

          <div
            style={{
              padding: 'var(--space-3)',
              background: 'var(--color-surface-subtle)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <span className="text-caption text-secondary">Current Status: </span>
            <span className="font-semibold">{selectedCustomer?.status}</span>
          </div>

          <Field id="customer-status-select" label="New Lifecycle State" required>
            <Select
              id="customer-status-select"
              value={targetStatus}
              onChange={(e) => setTargetStatus(e.target.value)}
              required
            >
              <option value="">Select target state…</option>
              {availableStatusChoices.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </Select>
          </Field>

          <Field id="customer-reason-input" label="Operational Reason" required>
            <Input
              id="customer-reason-input"
              value={transitionReason}
              onChange={(e) => setTransitionReason(e.target.value)}
              placeholder="Reason for changing customer state…"
              required
            />
          </Field>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: 'var(--space-2) 0',
            }}
          >
            <span className="text-caption text-muted font-mono">
              Expected Status: {selectedCustomer?.status}
            </span>
          </div>

          <div className="button-row" style={{ marginTop: 'var(--space-3)' }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setStatusModalOpen(false)}
              disabled={transitioning}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={transitioning || !targetStatus || !transitionReason}
            >
              {transitioning ? 'Saving…' : 'Record State Change'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  )
}
