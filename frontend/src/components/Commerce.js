'use client'

import React, { useState, useEffect, useId, useMemo } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import {
  Package,
  CreditCard,
  Truck,
  Tag,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
  DollarSign,
  Filter,
  Plus,
  ArrowUpRight,
  Check,
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
  Drawer,
  Dialog,
  Input,
  Field,
  Select,
  CopyableCode,
  Timeline,
  Banner,
} from '@/components/ui'
import { businessPath, businessApiPath, WRITER_ROLES } from '@/lib/catalog'
import { money, dateTime, relativeTime } from '@/lib/format'
import { clientApi, newIdempotencyKey } from '@/lib/clientApi'

// Legal lifecycle transitions per D4 (matching states.py and RecordCommands.js)
const TRANSITIONS = {
  orders: {
    PENDING: ['CONFIRMED', 'CANCELLED'],
    CONFIRMED: ['PROCESSING', 'CANCELLED'],
    PROCESSING: ['SHIPPED', 'CANCELLED'],
    SHIPPED: ['DELIVERED', 'RETURNED'],
    DELIVERED: ['RETURNED', 'REFUNDED'],
    RETURNED: ['REFUNDED'],
  },
  payments: {
    PENDING: ['AUTHORIZED', 'PAID', 'FAILED', 'CANCELLED'],
    AUTHORIZED: ['PAID', 'FAILED', 'CANCELLED'],
  },
  shipments: {
    PENDING: ['SUBMITTED', 'CANCELLED'],
    SUBMITTED: ['PICKED_UP', 'CANCELLED'],
    PICKED_UP: ['IN_TRANSIT', 'RETURNING'],
    IN_TRANSIT: ['OUT_FOR_DELIVERY', 'FAILED', 'RETURNING'],
    OUT_FOR_DELIVERY: ['DELIVERED', 'FAILED', 'RETURNING'],
    FAILED: ['OUT_FOR_DELIVERY', 'RETURNING'],
    RETURNING: ['RETURNED'],
  },
  products: {
    ACTIVE: ['INACTIVE', 'ARCHIVED'],
    INACTIVE: ['ACTIVE', 'ARCHIVED'],
    ARCHIVED: ['ACTIVE'],
  },
}

export default function Commerce({
  business = {},
  businessId,
  activeTab = 'orders',
  ordersData,
  paymentsData,
  timelineData,
  shipmentsData,
  productsData,
  initialActiveRecord = null,
}) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const currency = business?.currency || 'BDT'
  const timezone = business?.timezone || 'Asia/Dhaka'
  const canWrite = WRITER_ROLES.has(business?.role)

  // Sub-view toggle for Payments (payments ledger vs D6 financial timeline)
  const [paymentsView, setPaymentsView] = useState('payments') // 'payments' | 'timeline'

  // Quick filter for orders tab
  const [orderStatusFilter, setOrderStatusFilter] = useState('ALL')

  // Drawer state: open record
  const [activeRecord, setActiveRecord] = useState(initialActiveRecord)
  const [drawerOpen, setDrawerOpen] = useState(Boolean(initialActiveRecord))
  const [loadingDrawer, setLoadingDrawer] = useState(false)
  const [drawerError, setDrawerError] = useState('')

  // Refund dialog state
  const [refundModalOpen, setRefundModalOpen] = useState(false)
  const [refundTargetPayment, setRefundTargetPayment] = useState(null)
  const [refundAmount, setRefundAmount] = useState('')
  const [refundReason, setRefundReason] = useState('CUSTOMER_REQUEST')
  const [refundIdempotencyKey, setRefundIdempotencyKey] = useState('')
  const [refundSubmitting, setRefundSubmitting] = useState(false)
  const [refundMessage, setRefundMessage] = useState({ type: '', text: '' })

  // Status transition state (D4)
  const [targetStatus, setTargetStatus] = useState('')
  const [transitionReason, setTransitionReason] = useState('')
  const [transitioning, setTransitioning] = useState(false)
  const [transitionError, setTransitionError] = useState('')
  const [transitionSuccess, setTransitionSuccess] = useState('')

  // Outbound carrier preparation state
  const [preparingCarrier, setPreparingCarrier] = useState(false)
  const [carrierPreparedNotice, setCarrierPreparedNotice] = useState(false)

  // Listen to `?open=resource:id` query param
  useEffect(() => {
    const openParam = searchParams.get('open')
    if (!openParam) {
      setDrawerOpen(false)
      setActiveRecord(null)
      return
    }

    const [resName, recordId] = openParam.split(':')
    if (resName && recordId) {
      setDrawerOpen(true)

      // If activeRecord already matches the requested resource and ID, do not flash loading
      const currentId = activeRecord?.record?.id ?? activeRecord?.id
      if (activeRecord && activeRecord.resource === resName && String(currentId) === String(recordId)) {
        return
      }

      setLoadingDrawer(true)
      setDrawerError('')

      clientApi(`businesses/${businessId}/${resName}/${recordId}`)
        .then((res) => {
          setActiveRecord({ resource: resName, ...res })
          // Reset transition state
          setTargetStatus('')
          setTransitionReason('')
          setTransitionError('')
          setTransitionSuccess('')
        })
        .catch((err) => {
          setDrawerError(err.message || 'Failed to load record details.')
        })
        .finally(() => {
          setLoadingDrawer(false)
        })
    }
  }, [searchParams, businessId, activeRecord])

  // Close drawer
  const handleCloseDrawer = () => {
    setDrawerOpen(false)
    setActiveRecord(null)
    const params = new URLSearchParams(searchParams.toString())
    params.delete('open')
    const qs = params.toString()
    router.push(`${pathname}${qs ? `?${qs}` : ''}`, { scroll: false })
  }

  // Open refund dialog for a payment or order
  const handleOpenRefund = (paymentId, maxAmount, orderId) => {
    setRefundTargetPayment({ paymentId, maxAmount, orderId })
    setRefundAmount(maxAmount ? String(maxAmount) : '')
    setRefundReason('CUSTOMER_REQUEST')
    setRefundIdempotencyKey(newIdempotencyKey())
    setRefundMessage({ type: '', text: '' })
    setRefundModalOpen(true)
  }

  // Submit refund (Idempotent)
  const handleExecuteRefund = async (e) => {
    e.preventDefault()
    if (!refundTargetPayment) return

    setRefundSubmitting(true)
    setRefundMessage({ type: '', text: '' })

    try {
      await clientApi(`businesses/${businessId}/refunds`, {
        method: 'POST',
        headers: {
          'Idempotency-Key': refundIdempotencyKey,
        },
        body: {
          data: {
            payment: refundTargetPayment.paymentId,
            external_refund_id: `ui-${refundIdempotencyKey}`,
            amount: refundAmount,
            reason: refundReason,
          },
        },
      })

      setRefundMessage({
        type: 'success',
        text: 'Refund recorded in financial ledger. Idempotency key verified.',
      })
      setTimeout(() => {
        setRefundModalOpen(false)
        router.refresh()
      }, 1500)
    } catch (err) {
      setRefundMessage({
        type: 'error',
        text: err.detail || err.message || 'Refund failed.',
      })
    } finally {
      setRefundSubmitting(false)
    }
  }

  // Execute D4 status transition
  const handleExecuteTransition = async (e) => {
    e.preventDefault()
    if (!activeRecord || !targetStatus) return

    const record = activeRecord.record || activeRecord
    const resource = activeRecord.resource || activeTab

    setTransitioning(true)
    setTransitionError('')
    setTransitionSuccess('')

    try {
      const updated = await clientApi(`businesses/${businessId}/${resource}/${record.id}/transition`, {
        method: 'POST',
        body: {
          status: targetStatus,
          reason: transitionReason || 'Operational state change via console',
          expected_status: record.status, // Enforces D4 concurrency guard
        },
      })

      setTransitionSuccess(`Record transitioned to ${targetStatus}.`)
      setActiveRecord((prev) => ({
        ...prev,
        record: { ...prev.record, ...updated },
      }))
      setTargetStatus('')
      setTransitionReason('')
      router.refresh()
    } catch (err) {
      if (err.status === 409 || err.code === 'STALE_STATE') {
        setTransitionError('This record changed on the server. Reloaded latest state.')
        // Reload record
        clientApi(`businesses/${businessId}/${resource}/${record.id}`).then((res) => {
          setActiveRecord({ resource, ...res })
        })
      } else {
        setTransitionError(err.detail || err.message || 'Status transition failed.')
      }
    } finally {
      setTransitioning(false)
    }
  }

  // Execute outbound carrier dispatch preparation
  const handlePrepareCarrier = () => {
    setPreparingCarrier(true)
    setTimeout(() => {
      setPreparingCarrier(false)
      setCarrierPreparedNotice(true)
    }, 600)
  }

  // Orders rows and filtering
  const allOrders = ordersData?.results || (Array.isArray(ordersData) ? ordersData : [])
  const filteredOrders = useMemo(() => {
    if (orderStatusFilter === 'ALL') return allOrders
    return allOrders.filter((ord) => (ord.status || '').toUpperCase() === orderStatusFilter)
  }, [allOrders, orderStatusFilter])

  // Payments rows
  const allPayments = paymentsData?.results || (Array.isArray(paymentsData) ? paymentsData : [])

  // Timeline rows (D6)
  const allTimeline = timelineData?.results || (Array.isArray(timelineData) ? timelineData : [])

  // Shipments rows
  const allShipments = shipmentsData?.results || (Array.isArray(shipmentsData) ? shipmentsData : [])

  // Products rows
  const allProducts = productsData?.results || (Array.isArray(productsData) ? productsData : [])

  // Columns for Orders table
  const orderColumns = [
    {
      key: 'id',
      label: 'Order ID',
      render: (row) => <span className="font-mono font-semibold text-primary">#{row.id}</span>,
    },
    {
      key: 'customer',
      label: 'Customer',
      render: (row) => (
        <span className="font-mono text-caption text-secondary">
          {row.customer ? `Customer #${row.customer}` : '—'}
        </span>
      ),
    },
    {
      key: 'total_amount',
      label: 'Total Amount',
      type: 'money',
      currency,
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusChip status={row.status} record={row} size="sm" />,
    },
    {
      key: 'created_at',
      label: 'Placed Date',
      render: (row) => (
        <span className="tabular-nums text-caption text-secondary" title={row.created_at}>
          {dateTime(row.created_at, timezone)}
        </span>
      ),
    },
  ]

  // Columns for Payments table
  const paymentColumns = [
    {
      key: 'id',
      label: 'Payment ID',
      render: (row) => <span className="font-mono font-semibold text-primary">#{row.id}</span>,
    },
    {
      key: 'customer',
      label: 'Customer',
      render: (row) => (
        <span className="font-mono text-caption text-secondary">
          {row.customer ? `Customer #${row.customer}` : '—'}
        </span>
      ),
    },
    {
      key: 'order',
      label: 'Order Reference',
      render: (row) => (
        <span className="font-mono text-caption text-secondary">
          {row.order ? `Order #${row.order}` : '—'}
        </span>
      ),
    },
    {
      key: 'payment_method',
      label: 'Method',
      render: (row) => <span className="text-secondary">{row.payment_method || 'Standard'}</span>,
    },
    {
      key: 'amount',
      label: 'Amount',
      type: 'money',
      currency,
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusChip status={row.status} record={row} size="sm" />,
    },
    {
      key: 'created_at',
      label: 'Settled At',
      render: (row) => (
        <span className="tabular-nums text-caption text-secondary" title={row.created_at}>
          {dateTime(row.created_at, timezone)}
        </span>
      ),
    },
  ]

  // Columns for Financial Timeline table (D6)
  const timelineColumns = [
    {
      key: 'event_at',
      label: 'Event Date',
      render: (row) => (
        <span className="tabular-nums text-caption text-secondary" title={row.event_at}>
          {dateTime(row.event_at, timezone)}
        </span>
      ),
    },
    {
      key: 'entity_kind',
      label: 'Transaction Type',
      render: (row) => (
        <span
          className={`badge ${row.entity_kind === 'REFUND' ? 'badge-danger' : 'badge-success'}`}
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          {row.entity_kind}
        </span>
      ),
    },
    {
      key: 'order_id',
      label: 'Order ID',
      render: (row) => (
        <span className="font-mono text-caption text-secondary">
          {row.order_id ? `#${row.order_id}` : '—'}
        </span>
      ),
    },
    {
      key: 'amount',
      label: 'Amount',
      type: 'money',
      currency,
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusChip status={row.status} record={row} size="sm" />,
    },
  ]

  // Columns for Deliveries / Shipments table
  const shipmentColumns = [
    {
      key: 'id',
      label: 'Shipment ID',
      render: (row) => <span className="font-mono font-semibold text-primary">#{row.id}</span>,
    },
    {
      key: 'provider',
      label: 'Carrier / Provider',
      render: (row) => <span className="font-medium text-body">{row.provider || 'Carrier Service'}</span>,
    },
    {
      key: 'tracking_number',
      label: 'Tracking Number',
      render: (row) =>
        row.tracking_number ? (
          <CopyableCode value={row.tracking_number} />
        ) : (
          <span className="text-muted">—</span>
        ),
    },
    {
      key: 'order',
      label: 'Order Ref',
      render: (row) => (
        <span className="font-mono text-caption text-secondary">
          {row.order ? `Order #${row.order}` : '—'}
        </span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusChip status={row.status} record={row} size="sm" />,
    },
    {
      key: 'created_at',
      label: 'Dispatched At',
      render: (row) => (
        <span className="tabular-nums text-caption text-secondary" title={row.created_at}>
          {dateTime(row.created_at, timezone)}
        </span>
      ),
    },
  ]

  // Columns for Products table
  const productColumns = [
    {
      key: 'name',
      label: 'Product Name',
      render: (row) => <span className="font-semibold text-body">{row.name}</span>,
    },
    {
      key: 'sku',
      label: 'SKU',
      render: (row) => (row.sku ? <CopyableCode value={row.sku} /> : <span className="text-muted">—</span>),
    },
    {
      key: 'category',
      label: 'Category',
      render: (row) => <span className="text-secondary">{row.category || 'Standard'}</span>,
    },
    {
      key: 'price',
      label: 'Base Price',
      type: 'money',
      currency,
    },
    {
      key: 'inventory_quantity',
      label: 'Inventory',
      render: (row) => (
        <span className="tabular-nums font-mono font-medium">{row.inventory_quantity ?? '—'}</span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusChip status={row.status} record={row} size="sm" />,
    },
  ]

  // Details for current opened record
  const currentRecord = activeRecord?.record || activeRecord
  const openedResource = activeRecord?.resource || activeTab
  const availableTransitions =
    currentRecord && currentRecord.status && TRANSITIONS[openedResource]
      ? TRANSITIONS[openedResource][currentRecord.status] || []
      : []

  return (
    <div className="commerce-container stack-lg">
      {/* TAB 1: ORDERS */}
      {activeTab === 'orders' && (
        <div className="stack-lg">
          <section className="surface card-padding stack-sm" aria-labelledby="orders-list-title">
            <div className="section-header">
              <div>
                <h2 id="orders-list-title" className="section-title">
                  Customer Orders
                </h2>
                <p className="section-desc">
                  Authoritative order fulfillment records and status transitions.
                </p>
              </div>
              <span className="count-chip font-mono">
                {filteredOrders.length} {filteredOrders.length === 1 ? 'order' : 'orders'}
              </span>
            </div>

            {/* Quick status filter chips */}
            <div className="quick-filter-chips" role="group" aria-label="Filter orders by status">
              {['ALL', 'PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED'].map(
                (st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setOrderStatusFilter(st)}
                    className={`domain-chip-btn ${orderStatusFilter === st ? 'is-active' : ''}`}
                    aria-pressed={orderStatusFilter === st}
                  >
                    {st === 'ALL' ? 'All Orders' : st}
                  </button>
                ),
              )}
            </div>

            <DataTable
              columns={orderColumns}
              rows={filteredOrders}
              businessId={business.id}
              resource="orders"
              emptyTitle="No orders found"
              emptyDescription={
                orderStatusFilter !== 'ALL'
                  ? `No orders matching status ${orderStatusFilter}.`
                  : 'No customer orders have been placed yet.'
              }
            />
          </section>
        </div>
      )}

      {/* TAB 2: PAYMENTS & REFUNDS */}
      {activeTab === 'payments' && (
        <div className="stack-lg">
          <section className="surface card-padding stack-sm" aria-labelledby="payments-list-title">
            <div className="timeline-switch-bar">
              <div>
                <h2 id="payments-list-title" className="section-title">
                  {paymentsView === 'payments' ? 'Settled Payments Ledger' : 'Financial Timeline (Audit)'}
                </h2>
                <p className="section-desc">
                  {paymentsView === 'payments'
                    ? 'Authoritative payment records and double-entry refund ledger.'
                    : 'Unified chronologically ordered financial ledger entries (D6).'}
                </p>
              </div>

              {/* View Switcher: Payments vs Financial Timeline */}
              <div className="timeline-segmented" role="group" aria-label="Financial view mode">
                <button
                  type="button"
                  onClick={() => setPaymentsView('payments')}
                  className={`timeline-segmented-btn ${paymentsView === 'payments' ? 'is-active' : ''}`}
                  aria-pressed={paymentsView === 'payments'}
                >
                  <CreditCard size={14} aria-hidden="true" />
                  <span>Payments Ledger</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPaymentsView('timeline')}
                  className={`timeline-segmented-btn ${paymentsView === 'timeline' ? 'is-active' : ''}`}
                  aria-pressed={paymentsView === 'timeline'}
                >
                  <Clock size={14} aria-hidden="true" />
                  <span>Financial Timeline</span>
                </button>
              </div>
            </div>

            {paymentsView === 'payments' ? (
              <DataTable
                columns={paymentColumns}
                rows={allPayments}
                businessId={business.id}
                resource="payments"
                emptyTitle="No payments recorded"
                emptyDescription="Settled customer payments will appear here."
              />
            ) : (
              <DataTable
                columns={timelineColumns}
                rows={allTimeline}
                businessId={business.id}
                emptyTitle="No financial timeline events"
                emptyDescription="Payments and refunds will appear chronologically here."
                openInDrawer={false}
              />
            )}
          </section>
        </div>
      )}

      {/* TAB 3: DELIVERIES & SHIPMENTS */}
      {activeTab === 'deliveries' && (
        <div className="stack-lg">
          <section className="surface card-padding stack-sm" aria-labelledby="deliveries-list-title">
            <div className="section-header">
              <div>
                <h2 id="deliveries-list-title" className="section-title">
                  Carrier Deliveries &amp; Shipments
                </h2>
                <p className="section-desc">
                  Outbound carrier consignments, tracking numbers, and delivery state tracking.
                </p>
              </div>
              <span className="count-chip font-mono">
                {allShipments.length} {allShipments.length === 1 ? 'consignment' : 'consignments'}
              </span>
            </div>

            <DataTable
              columns={shipmentColumns}
              rows={allShipments}
              businessId={business.id}
              resource="shipments"
              emptyTitle="No shipments dispatched"
              emptyDescription="Carrier consignments will appear here once orders are shipped."
            />
          </section>
        </div>
      )}

      {/* TAB 4: PRODUCTS & CATALOG */}
      {activeTab === 'products' && (
        <div className="stack-lg">
          <section className="surface card-padding stack-sm" aria-labelledby="products-list-title">
            <div className="section-header">
              <div>
                <h2 id="products-list-title" className="section-title">
                  Catalog Products &amp; Variants
                </h2>
                <p className="section-desc">
                  Active SKU inventory, variants, unit pricing, and product status.
                </p>
              </div>
              <span className="count-chip font-mono">{allProducts.length} items</span>
            </div>

            <DataTable
              columns={productColumns}
              rows={allProducts}
              businessId={business.id}
              resource="products"
              emptyTitle="No products in catalog"
              emptyDescription="Add or ingest products to display inventory."
            />
          </section>
        </div>
      )}

      {/* RECORD DETAIL DRAWER */}
      <Drawer
        isOpen={drawerOpen}
        onClose={handleCloseDrawer}
        title={
          currentRecord
            ? `${openedResource.slice(0, -1).toUpperCase()} #${currentRecord.id}`
            : 'Record Detail'
        }
        subtitle={
          currentRecord?.created_at ? `Created ${dateTime(currentRecord.created_at, timezone)}` : undefined
        }
        width="560px"
      >
        {loadingDrawer && (
          <div className="stack-sm">
            <div style={{ height: 24, background: 'var(--color-surface-subtle)', borderRadius: 4 }} />
            <div style={{ height: 120, background: 'var(--color-surface-subtle)', borderRadius: 8 }} />
            <div style={{ height: 80, background: 'var(--color-surface-subtle)', borderRadius: 8 }} />
          </div>
        )}

        {drawerError && <Banner variant="danger">{drawerError}</Banner>}

        {!loadingDrawer && currentRecord && (
          <div className="stack-lg">
            {/* Common Status & Meta Header */}
            <div className="drawer-section">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <StatusChip status={currentRecord.status} record={currentRecord} />
                <span className="font-mono text-caption text-muted">ID: {currentRecord.id}</span>
              </div>
            </div>

            {/* ORDERS DRAWER SPECIFIC CONTENT */}
            {openedResource === 'orders' && (
              <>
                {/* Customer Link Section */}
                <div className="drawer-section">
                  <h3 className="drawer-section-title">Customer Information</h3>
                  {currentRecord.customer ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div>
                        <span className="font-medium text-body">
                          {activeRecord?.customer?.name || `Customer #${currentRecord.customer}`}
                        </span>
                        <p className="text-caption text-muted" style={{ margin: '2px 0 0' }}>
                          Primary registered customer entity
                        </p>
                      </div>
                      <Link
                        className="button button-secondary button-sm"
                        href={`/business/${businessId}/customers?open=customers:${currentRecord.customer}`}
                      >
                        <span>Customer 360</span>
                        <ExternalLink size={12} aria-hidden="true" />
                      </Link>
                    </div>
                  ) : (
                    <span className="text-muted">No associated customer</span>
                  )}
                </div>

                {/* Order Financials & Items */}
                <div className="drawer-section">
                  <h3 className="drawer-section-title">Financial Summary</h3>
                  <dl className="drawer-prop-list">
                    <div className="drawer-prop-item">
                      <dt>Total Amount</dt>
                      <dd className="font-mono">{money(currentRecord.total_amount, currency)}</dd>
                    </div>
                    <div className="drawer-prop-item">
                      <dt>Currency</dt>
                      <dd>{currency}</dd>
                    </div>
                  </dl>

                  {/* Order Items Table */}
                  {activeRecord?.items?.results?.length > 0 && (
                    <div style={{ marginTop: 'var(--space-3)' }}>
                      <h4
                        className="text-caption font-semibold text-secondary"
                        style={{ marginBottom: 'var(--space-2)' }}
                      >
                        Line Items ({activeRecord.items.results.length})
                      </h4>
                      <table className="data-table" style={{ fontSize: 'var(--text-table)' }}>
                        <thead>
                          <tr>
                            <th>Item</th>
                            <th className="align-right">Qty</th>
                            <th className="align-right">Price</th>
                          </tr>
                        </thead>
                        <tbody>
                          {activeRecord.items.results.map((item) => (
                            <tr key={item.id}>
                              <td>{item.product_name || `Product #${item.product}`}</td>
                              <td className="align-right font-mono">{item.quantity}</td>
                              <td className="align-right font-mono">{money(item.unit_price, currency)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Legal State Machine Transition Control (D4) */}
                {canWrite && (
                  <div className="drawer-section">
                    <h3 className="drawer-section-title">Legal State Transition</h3>
                    <p className="text-caption text-secondary" style={{ marginBottom: 'var(--space-3)' }}>
                      Enforces authoritative transition rules per D4 contract. Concurrency protected.
                    </p>

                    {transitionSuccess && <Banner variant="success">{transitionSuccess}</Banner>}
                    {transitionError && <Banner variant="danger">{transitionError}</Banner>}

                    {availableTransitions.length > 0 ? (
                      <form onSubmit={handleExecuteTransition} className="transition-panel stack-sm">
                        <Field id="transition-target" label="Target Status" required>
                          <Select
                            id="transition-target"
                            value={targetStatus}
                            onChange={(e) => setTargetStatus(e.target.value)}
                            required
                          >
                            <option value="">Select next state…</option>
                            {availableTransitions.map((st) => (
                              <option key={st} value={st}>
                                {st}
                              </option>
                            ))}
                          </Select>
                        </Field>

                        <Field id="transition-reason" label="Operational Reason" required>
                          <Input
                            id="transition-reason"
                            value={transitionReason}
                            onChange={(e) => setTransitionReason(e.target.value)}
                            placeholder="Reason for state transition"
                            required
                          />
                        </Field>

                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            marginTop: 'var(--space-2)',
                          }}
                        >
                          <span className="text-caption text-muted font-mono">
                            Expected: {currentRecord.status}
                          </span>
                          <Button
                            type="submit"
                            variant="primary"
                            size="sm"
                            disabled={transitioning || !targetStatus || !transitionReason}
                          >
                            {transitioning ? 'Transitioning…' : 'Update Status'}
                          </Button>
                        </div>
                      </form>
                    ) : (
                      <div className="empty-state" style={{ padding: 'var(--space-3)' }}>
                        <span className="text-secondary text-caption">
                          Terminal state reached — no further transitions allowed.
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Refund Action if Delivered or Paid */}
                {canWrite && ['DELIVERED', 'PAID', 'CONFIRMED'].includes(currentRecord.status) && (
                  <div className="drawer-section">
                    <h3 className="drawer-section-title">Financial Actions</h3>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        handleOpenRefund(
                          activeRecord?.payments?.results?.[0]?.id || currentRecord.id,
                          currentRecord.total_amount,
                          currentRecord.id,
                        )
                      }
                    >
                      <RotateCcw size={14} aria-hidden="true" />
                      <span>Issue Order Refund</span>
                    </Button>
                  </div>
                )}
              </>
            )}

            {/* PAYMENTS DRAWER SPECIFIC CONTENT */}
            {openedResource === 'payments' && (
              <>
                <div className="drawer-section">
                  <h3 className="drawer-section-title">Payment Settlement Details</h3>
                  <dl className="drawer-prop-list">
                    <div className="drawer-prop-item">
                      <dt>Amount</dt>
                      <dd className="font-mono">{money(currentRecord.amount, currency)}</dd>
                    </div>
                    <div className="drawer-prop-item">
                      <dt>Payment Method</dt>
                      <dd>{currentRecord.payment_method || 'Standard Settlement'}</dd>
                    </div>
                    <div className="drawer-prop-item">
                      <dt>Order Reference</dt>
                      <dd className="font-mono">{currentRecord.order ? `#${currentRecord.order}` : '—'}</dd>
                    </div>
                    <div className="drawer-prop-item">
                      <dt>Customer ID</dt>
                      <dd className="font-mono">
                        {currentRecord.customer ? `#${currentRecord.customer}` : '—'}
                      </dd>
                    </div>
                  </dl>
                </div>

                {canWrite && ['PAID', 'AUTHORIZED'].includes(currentRecord.status) && (
                  <div className="drawer-section">
                    <h3 className="drawer-section-title">Refund Processing</h3>
                    <p className="text-caption text-secondary" style={{ marginBottom: 'var(--space-3)' }}>
                      Record full or partial refund against this settled transaction.
                    </p>
                    <Button
                      variant="secondary"
                      onClick={() =>
                        handleOpenRefund(currentRecord.id, currentRecord.amount, currentRecord.order)
                      }
                    >
                      <RotateCcw size={14} aria-hidden="true" />
                      <span>Issue Refund</span>
                    </Button>
                  </div>
                )}
              </>
            )}

            {/* SHIPMENTS DRAWER SPECIFIC CONTENT */}
            {openedResource === 'shipments' && (
              <>
                <div className="drawer-section">
                  <h3 className="drawer-section-title">Consignment &amp; Logistics</h3>
                  <dl className="drawer-prop-list">
                    <div className="drawer-prop-item">
                      <dt>Carrier Provider</dt>
                      <dd>{currentRecord.provider || 'Logistics Service'}</dd>
                    </div>
                    <div className="drawer-prop-item">
                      <dt>Tracking Number</dt>
                      <dd>
                        {currentRecord.tracking_number ? (
                          <CopyableCode value={currentRecord.tracking_number} />
                        ) : (
                          '—'
                        )}
                      </dd>
                    </div>
                  </dl>
                </div>

                {/* Outbound Carrier Operation Panel */}
                <div className="drawer-section">
                  <h3 className="drawer-section-title">Carrier Transport Operation</h3>
                  <div className="carrier-operation-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span className="badge badge-warning" style={{ fontSize: 11 }}>
                        Prepared — not executed
                      </span>
                      <span className="text-caption text-muted">Outbound Transport</span>
                    </div>
                    <p className="text-caption text-secondary" style={{ margin: 0 }}>
                      Carrier webhook sync operations are prepared internally for audit verification. Carrier
                      dispatch remains simulated.
                    </p>
                    {carrierPreparedNotice && (
                      <Banner variant="success">Carrier tracking sync attempt recorded.</Banner>
                    )}
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handlePrepareCarrier}
                      disabled={preparingCarrier}
                    >
                      {preparingCarrier ? 'Preparing…' : 'Prepare Carrier Dispatch Sync'}
                    </Button>
                  </div>
                </div>
              </>
            )}

            {/* PRODUCTS DRAWER SPECIFIC CONTENT */}
            {openedResource === 'products' && (
              <>
                <div className="drawer-section">
                  <h3 className="drawer-section-title">Catalog Specifications</h3>
                  <dl className="drawer-prop-list">
                    <div className="drawer-prop-item">
                      <dt>SKU</dt>
                      <dd>{currentRecord.sku ? <CopyableCode value={currentRecord.sku} /> : '—'}</dd>
                    </div>
                    <div className="drawer-prop-item">
                      <dt>Base Price</dt>
                      <dd className="font-mono">{money(currentRecord.price, currency)}</dd>
                    </div>
                    <div className="drawer-prop-item">
                      <dt>Inventory Stock</dt>
                      <dd className="font-mono">{currentRecord.inventory_quantity ?? '—'}</dd>
                    </div>
                    <div className="drawer-prop-item">
                      <dt>Category</dt>
                      <dd>{currentRecord.category || 'General'}</dd>
                    </div>
                  </dl>
                </div>

                {/* Variants List (D5) */}
                {activeRecord?.variants?.results?.length > 0 && (
                  <div className="drawer-section">
                    <h3 className="drawer-section-title">Product Variants</h3>
                    <table className="data-table" style={{ fontSize: 'var(--text-table)' }}>
                      <thead>
                        <tr>
                          <th>Variant</th>
                          <th>SKU</th>
                          <th className="align-right">Price</th>
                          <th className="align-right">Stock</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeRecord.variants.results.map((v) => (
                          <tr key={v.id}>
                            <td className="font-medium">{v.name}</td>
                            <td className="font-mono text-caption">{v.sku}</td>
                            <td className="align-right font-mono">{money(v.price, currency)}</td>
                            <td className="align-right font-mono">{v.inventory_quantity}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </Drawer>

      {/* REFUND DIALOG (Idempotent D2/D4) */}
      <Dialog
        isOpen={refundModalOpen}
        onClose={() => setRefundModalOpen(false)}
        title="Issue Financial Refund"
        subtitle="Idempotent double-entry refund ledger recording"
      >
        <form onSubmit={handleExecuteRefund} className="stack-sm">
          {refundMessage.text && (
            <Banner variant={refundMessage.type === 'error' ? 'danger' : 'success'}>
              {refundMessage.text}
            </Banner>
          )}

          <div
            style={{
              padding: 'var(--space-3)',
              background: 'var(--color-surface-subtle)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <span className="text-caption text-secondary">Target Payment ID: </span>
            <span className="font-mono font-semibold">#{refundTargetPayment?.paymentId}</span>
            {refundTargetPayment?.orderId && (
              <span className="ml-2 text-caption text-secondary">(Order #{refundTargetPayment.orderId})</span>
            )}
          </div>

          <Field id="refund-amount-input" label={`Refund Amount (${currency})`} required>
            <Input
              id="refund-amount-input"
              type="text"
              value={refundAmount}
              onChange={(e) => setRefundAmount(e.target.value)}
              placeholder="0.00"
              required
            />
          </Field>

          <Field id="refund-reason-select" label="Refund Reason" required>
            <Select
              id="refund-reason-select"
              value={refundReason}
              onChange={(e) => setRefundReason(e.target.value)}
              required
            >
              <option value="CUSTOMER_REQUEST">Customer requested cancellation</option>
              <option value="DEFECTIVE_PRODUCT">Defective or damaged merchandise</option>
              <option value="DELIVERY_FAILURE">Failed carrier fulfillment</option>
              <option value="PRICING_ERROR">Pricing adjustment / discount</option>
              <option value="FRAUD_PREVENTION">Risk mitigation / fraud protection</option>
            </Select>
          </Field>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: 'var(--space-2) 0',
            }}
          >
            <span className="text-caption text-muted">Idempotency Key:</span>
            <span className="font-mono text-caption text-muted">{refundIdempotencyKey.slice(0, 18)}…</span>
          </div>

          <div className="button-row" style={{ marginTop: 'var(--space-3)' }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setRefundModalOpen(false)}
              disabled={refundSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={refundSubmitting || !refundAmount}>
              {refundSubmitting ? 'Recording…' : 'Process Refund (Idempotent)'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  )
}
