'use client'

import React, { useState } from 'react'
import {
  Plus,
  Trash2,
  Settings,
  Search,
  ExternalLink,
  Shield,
  Layers,
  Sparkles,
  ShoppingBag,
  CreditCard,
  Truck,
} from 'lucide-react'
import {
  Button,
  IconButton,
  Field,
  Input,
  Select,
  Textarea,
  Checkbox,
  MoneyField,
  DateTimeField,
  Banner,
  StatusChip,
  SeverityChip,
  ConfidenceMeter,
  Skeleton,
  EmptyState,
  UnavailableState,
  SimulatedBadge,
  KpiTile,
  ToastProvider,
  useToast,
  Tabs,
  Drawer,
  Dialog,
  ConfirmDialog,
  Pagination,
  FilterBar,
  PageHeader,
  DataTable,
  Timeline,
  EvidencePanel,
  CopyableCode,
} from '@/components/ui'

function ToastDemos() {
  const { showToast } = useToast()

  return (
    <div className="button-row" style={{ flexWrap: 'wrap' }}>
      <Button
        variant="secondary"
        size="sm"
        onClick={() =>
          showToast({
            variant: 'info',
            title: 'System Notice',
            message: 'Data sync completed at scheduled interval.',
          })
        }
      >
        Info Toast
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={() =>
          showToast({
            variant: 'success',
            title: 'Saved successfully',
            message: 'Record changes committed to database.',
          })
        }
      >
        Success Toast
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={() =>
          showToast({
            variant: 'warning',
            title: 'Configuration Warning',
            message: 'API rate limit threshold at 82% capacity.',
          })
        }
      >
        Warning Toast
      </Button>
      <Button
        variant="danger"
        size="sm"
        onClick={() =>
          showToast({
            variant: 'danger',
            title: 'Operation Failed',
            message: 'Payment gateway rejected transaction reference.',
          })
        }
      >
        Danger Toast
      </Button>
    </div>
  )
}

export function UiKitGalleryClient({ business }) {
  // Overlay state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [isConfirmOpen, setIsConfirmOpen] = useState(false)
  const [confirmLoading, setConfirmLoading] = useState(false)

  // Form state
  const [sampleMoney, setSampleMoney] = useState('2450.00')
  const [sampleSearch, setSampleSearch] = useState('')
  const [activeTab, setActiveTab] = useState('orders')
  const [page, setPage] = useState(1)

  // Sample table data
  const sampleRows = [
    {
      id: 101,
      order_number: 'ORD-84920',
      customer_name: 'Sadia Rahman',
      total: 3500.0,
      currency: 'BDT',
      status: 'PAID',
      created_at: '2026-11-09T14:30:00Z',
      notes: '<untrusted_customer_data>Please call upon arrival before delivery.</untrusted_customer_data>',
    },
    {
      id: 102,
      order_number: 'ORD-84921',
      customer_name: 'Tanvir Hossain',
      total: 1250.5,
      currency: 'BDT',
      status: 'PENDING',
      created_at: '2026-11-09T15:15:00Z',
      notes: '<untrusted_customer_data>Urgent: ship before Friday morning.</untrusted_customer_data>',
    },
    {
      id: 103,
      order_number: 'ORD-84922',
      customer_name: 'Farhana Ahmed',
      total: 7800.0,
      currency: 'BDT',
      status: 'INACTIVE',
      created_at: '2026-11-08T11:00:00Z',
      notes: '<untrusted_customer_data>Cancelled by customer request.</untrusted_customer_data>',
    },
  ]

  const tableColumns = [
    { key: 'order_number', label: 'Order #', type: 'entity' },
    { key: 'customer_name', label: 'Customer', type: 'text' },
    { key: 'total', label: 'Amount', type: 'money', currency: 'BDT' },
    { key: 'status', label: 'State', type: 'status' },
    { key: 'created_at', label: 'Date', type: 'datetime' },
    { key: 'notes', label: 'Delivery note', type: 'untrusted' },
  ]

  // Sample timeline events
  const timelineEvents = [
    {
      id: 'e1',
      title: 'Order Placed by Customer',
      status: 'PAID',
      timestamp: '2026-11-09T14:30:00Z',
      description: 'Customer selected standard delivery and verified primary mobile identity.',
      metadata: { 'Order ID': '#84920', Channel: 'Website checkout' },
      icon: ShoppingBag,
      tone: 'success',
    },
    {
      id: 'e2',
      title: 'Payment Gateway Confirmed',
      status: 'PAID',
      timestamp: '2026-11-09T14:32:15Z',
      description: 'Transaction reference TXN-99882 settled successfully via bKash gateway.',
      metadata: { Reference: 'TXN-99882', Gateway: 'bKash' },
      icon: CreditCard,
      tone: 'success',
    },
    {
      id: 'e3',
      title: 'AI Delivery Risk Advisory',
      status: 'SUGGESTED',
      is_ai: true,
      timestamp: '2026-11-09T14:33:00Z',
      description: 'Advisory analysis detected heavy rain alert in destination postal district.',
      icon: Sparkles,
      tone: 'ai',
    },
  ]

  const handleConfirmAction = () => {
    setConfirmLoading(true)
    setTimeout(() => {
      setConfirmLoading(false)
      setIsConfirmOpen(false)
    }, 1000)
  }

  return (
    <ToastProvider>
      <div
        className="ui-kit-gallery"
        suppressHydrationWarning
        style={{ maxWidth: '1280px', margin: '0 auto', paddingBottom: 'var(--space-12)' }}
      >
        <PageHeader
          title="UI Kit Component Gallery"
          description="Enterprise design system token catalog, native inputs, status primitives, overlays, and tables."
          breadcrumbs={[
            { label: 'Overview', href: `/business/${business.id}/overview` },
            { label: 'UI Kit Gallery' },
          ]}
          badge={<SimulatedBadge />}
          actions={
            <div className="button-row">
              <Button variant="primary" icon={Plus}>
                New Action
              </Button>
            </div>
          }
        />

        {/* Section 1: Form Basics */}
        <section className="surface" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-header">
            <div>
              <h2>Form Controls & Actions (T3-1)</h2>
              <p>WCAG AA accessible form fields, states, sizes, and native control stylings.</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
            <div>
              <p className="form-label">Button Variants & Sizes</p>
              <div className="button-row" style={{ flexWrap: 'wrap' }}>
                <Button variant="primary">Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="danger">Danger</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="primary" size="sm">
                  Small Primary
                </Button>
                <Button variant="secondary" size="sm">
                  Small Secondary
                </Button>
                <Button variant="primary" isLoading>
                  Saving...
                </Button>
                <Button variant="secondary" disabled>
                  Disabled
                </Button>
                <IconButton icon={Settings} label="Settings control" variant="secondary" />
                <IconButton icon={Trash2} label="Delete record" variant="ghost" size="sm" />
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: 'var(--space-4)',
              }}
            >
              <Field
                label="Customer full name"
                id="demo-name"
                hint="Legal name matching identity card"
                required
              >
                <Input placeholder="Enter name..." />
              </Field>

              <Field label="Email address" id="demo-email" error="Please enter a valid business email">
                <Input type="email" placeholder="user@company.com" defaultValue="invalid-email" />
              </Field>

              <Field
                label="Order transaction total"
                id="demo-money"
                hint="Strict 2 decimal numeric validation"
                required
              >
                <MoneyField value={sampleMoney} onChange={(e) => setSampleMoney(e.target.value)} />
              </Field>

              <Field label="Recorded date and time" id="demo-date" hint="Stored in business timezone">
                <DateTimeField defaultValue="2026-11-09T14:30" />
              </Field>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: 'var(--space-4)',
              }}
            >
              <Field label="Account status" id="demo-select">
                <Select
                  options={[
                    { value: 'ACTIVE', label: 'Active business account' },
                    { value: 'SUSPENDED', label: 'Suspended by admin' },
                    { value: 'PENDING', label: 'Pending manual review' },
                  ]}
                />
              </Field>

              <Field label="Delivery instructions" id="demo-textarea">
                <Textarea placeholder="Special handling notes..." rows={2} />
              </Field>
            </div>

            <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
              <Checkbox
                id="cb-1"
                label="Receive delivery SMS updates"
                hint="Sent to primary mobile number"
                defaultChecked
              />
              <Checkbox id="cb-2" label="Require signature on delivery" />
              <Checkbox id="cb-3" label="Account locked by administrator" disabled />
            </div>
          </div>
        </section>

        {/* Section 2: Feedback & Status */}
        <section className="surface" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-header">
            <div>
              <h2>Feedback & Status Indicators (T3-2)</h2>
              <p>Honest status wording, WCAG contrast chips, alert banners, and calm not-connected states.</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <Banner variant="info" title="Scheduled Platform Maintenance">
                Database indexing scheduled tonight at 02:00 Asia/Dhaka. Read operations remain uninterrupted.
              </Banner>
              <Banner variant="success" title="Payment Succeeded" onClose={() => {}}>
                Receipt generated and recorded. Accounting ledger entries updated.
              </Banner>
              <Banner variant="warning" title="Stale Record State Detected">
                Someone else updated this configuration record. Reloading with authoritative server state.
              </Banner>
              <Banner
                variant="danger"
                title="Payment Gateway Unavailable"
                action={
                  <Button variant="secondary" size="sm">
                    Retry Connection
                  </Button>
                }
              >
                The payment processor did not respond within the 15-second timeout window.
              </Banner>
            </div>

            <div>
              <p className="form-label">Status Chips (Strict Value Mapping with Icon + Label)</p>
              <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
                <StatusChip status="ACTIVE" />
                <StatusChip status="INACTIVE" />
                <StatusChip status="PENDING" />
                <StatusChip status="DELIVERED" />
                <StatusChip status="REFUNDED" />
                <StatusChip status="RETURNED" />
                <StatusChip status="CLOSED" />
                <StatusChip status="MISSED" />
                <StatusChip status="SUGGESTED" />
                <StatusChip status="UNAVAILABLE" />
                <StatusChip status="NOT MOUNTED" />
              </div>
            </div>

            <div>
              <p className="form-label">Severity Chips & Confidence Meters</p>
              <div style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'center', flexWrap: 'wrap' }}>
                <SeverityChip severity="CRITICAL" />
                <SeverityChip severity="HIGH" />
                <SeverityChip severity="MEDIUM" />
                <SeverityChip severity="LOW" />
                <SeverityChip severity="INFO" />
                <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
                  <ConfidenceMeter value={0.92} label="High match" />
                  <ConfidenceMeter value={0.65} label="Medium match" />
                  <ConfidenceMeter value={0.34} label="Low match" />
                </div>
              </div>
            </div>

            <div>
              <p className="form-label">KPI Tiles</p>
              <div className="metric-grid">
                <KpiTile
                  title="Gross Sales"
                  value="BDT 124,500.00"
                  trend="+14.2%"
                  trendDirection="up"
                  trendLabel="vs last week"
                />
                <KpiTile
                  title="Returned Orders"
                  value="18"
                  trend="-3.1%"
                  trendDirection="down"
                  trendLabel="improvement"
                />
                <KpiTile title="Pending Sync" isLoading={true} />
                <KpiTile
                  title="Predictive LTV"
                  isUnavailable={true}
                  unavailableOwner="Business Intelligence"
                  unavailableReason="Predictive module not mounted in local development"
                />
              </div>
            </div>

            <div>
              <p className="form-label">Ephemeral Toast Notifications</p>
              <ToastDemos />
            </div>

            <div>
              <p className="form-label">Calm Unavailable State (Normal Data, Never Red or Zero)</p>
              <UnavailableState
                title="Context Graph Engine"
                owner="Business Graph (BG-1)"
                reason="Context graph service is unmounted in this environment. Authoritative node relationships will activate automatically upon mount."
                action={
                  <Button variant="secondary" size="sm">
                    Inspect Logs
                  </Button>
                }
              />
            </div>
          </div>
        </section>

        {/* Section 3: Overlays & Navigation */}
        <section className="surface" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-header">
            <div>
              <h2>Overlays & Navigation (T3-3)</h2>
              <p>Path-segment tabs, focus-trapped drawers, accessible modals, and filter toolbars.</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
            <div>
              <p className="form-label">Tab Navigation with Count Chips</p>
              <Tabs
                items={[
                  { id: 'orders', label: 'Orders', count: 128 },
                  { id: 'payments', label: 'Payments & Refunds', count: 94 },
                  { id: 'deliveries', label: 'Shipments', count: 12 },
                  { id: 'archived', label: 'Archived', count: 0 },
                ]}
                activeTab={activeTab}
                onChange={setActiveTab}
              />
            </div>

            <div>
              <p className="form-label">Overlay Triggers (Focus Trap & Escape Handlers)</p>
              <div className="button-row">
                <Button variant="secondary" onClick={() => setIsDrawerOpen(true)}>
                  Open Detail Drawer
                </Button>
                <Button variant="secondary" onClick={() => setIsDialogOpen(true)}>
                  Open Standard Dialog
                </Button>
                <Button variant="danger" onClick={() => setIsConfirmOpen(true)}>
                  Open Destructive Confirm Dialog
                </Button>
              </div>
            </div>

            <div>
              <p className="form-label">Filter Bar & Active Filter Pills</p>
              <FilterBar
                searchValue={sampleSearch}
                onSearchChange={setSampleSearch}
                activeFilters={[
                  { key: 'status', label: 'Status', value: 'Paid, Processing', onRemove: () => {} },
                  { key: 'method', label: 'Payment', value: 'bKash', onRemove: () => {} },
                ]}
                onClearAll={() => setSampleSearch('')}
              >
                <Select
                  size="sm"
                  options={[
                    { value: '', label: 'All Channels' },
                    { value: 'web', label: 'Online Store' },
                    { value: 'pos', label: 'Retail POS' },
                  ]}
                />
              </FilterBar>
            </div>

            <div>
              <p className="form-label">Pagination Component</p>
              <Pagination page={page} pageSize={25} total={1284} onPageChange={(p) => setPage(p)} />
            </div>
          </div>
        </section>

        {/* Section 4: Data Table */}
        <section className="surface" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-header">
            <div>
              <h2>Data Presentation (T3-4)</h2>
              <p>
                Typed columns, sticky header, right-aligned mono numerics, density toggle, untrusted text safe
                stripping.
              </p>
            </div>
          </div>

          <DataTable
            title="Recent Customer Orders"
            columns={tableColumns}
            rows={sampleRows}
            pagination={{
              page: 1,
              pageSize: 25,
              total: 3,
              onPageChange: () => {},
            }}
          />
        </section>

        {/* Section 5: Evidence & Time */}
        <section className="surface" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-header">
            <div>
              <h2>Evidence & Chronological Threads (T3-5)</h2>
              <p>Continuous vertical timeline thread, grounding citations panel, and copyable identifiers.</p>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: 'var(--space-6)',
            }}
          >
            <div>
              <p className="form-label">Timeline (The Evidence Thread)</p>
              <Timeline events={timelineEvents} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              <div>
                <p className="form-label">Grounding Evidence Panel</p>
                <EvidencePanel
                  title="Decision Grounding"
                  confidence={0.94}
                  source="CRM Database & Payment Ledger"
                  description="Facts observed directly from authenticated customer interactions."
                  items={[
                    {
                      fact: 'Customer verified primary phone number via SMS OTP on 2026-11-09.',
                      source: 'AuthLog #991',
                    },
                    {
                      fact: '3 successful previous purchases with zero returned parcels.',
                      source: 'OrderLedger',
                    },
                    {
                      fact: '<untrusted_customer_data>Customer stated preference for weekend delivery window.</untrusted_customer_data>',
                      source: 'Ticket #442',
                    },
                  ]}
                />
              </div>

              <div>
                <p className="form-label">Copyable Identifiers & Codes</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  <div>
                    <span className="text-caption text-muted" style={{ marginRight: 'var(--space-2)' }}>
                      API Token:
                    </span>
                    <CopyableCode value="biz_live_8f93b2a74e0192837482" label="API Key" />
                  </div>
                  <div>
                    <span className="text-caption text-muted" style={{ marginRight: 'var(--space-2)' }}>
                      Idempotency Key:
                    </span>
                    <CopyableCode value="7c9e6679-7425-40de-944b-e07fc1f90ae7" label="Idempotency Key" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Interactive Overlays */}
        <Drawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          title="Order Details #ORD-84920"
          subtitle="Placed on 09 Nov 2026, 14:30 in Asia/Dhaka"
          footer={
            <div className="button-row">
              <Button variant="ghost" onClick={() => setIsDrawerOpen(false)}>
                Close
              </Button>
              <Button variant="primary" onClick={() => setIsDrawerOpen(false)}>
                Save Changes
              </Button>
            </div>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <Banner variant="info" title="Payment Confirmed">
              BDT 3,500.00 settled through bKash payment gateway.
            </Banner>
            <Field label="Customer Name" id="drawer-cust">
              <Input defaultValue="Sadia Rahman" readOnly />
            </Field>
            <Field label="Delivery Address" id="drawer-addr">
              <Textarea defaultValue="House 42, Road 11, Banani, Dhaka" rows={2} readOnly />
            </Field>
            <div>
              <p className="form-label">Fulfillment Status</p>
              <StatusChip status="DELIVERED" />
            </div>
          </div>
        </Drawer>

        <Dialog
          isOpen={isDialogOpen}
          onClose={() => setIsDialogOpen(false)}
          title="Export Analytics Report"
          subtitle="Generate a verified CSV or PDF export of current period transactions."
          footer={
            <div className="button-row">
              <Button variant="ghost" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => setIsDialogOpen(false)}>
                Export CSV
              </Button>
            </div>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <Field label="Export Format" id="export-fmt">
              <Select
                options={[
                  { value: 'csv', label: 'Comma Separated Values (.csv)' },
                  { value: 'json', label: 'JSON Data Stream (.json)' },
                ]}
              />
            </Field>
            <Checkbox id="include-untrusted" label="Include customer delivery instructions" defaultChecked />
          </div>
        </Dialog>

        <ConfirmDialog
          isOpen={isConfirmOpen}
          onClose={() => setIsConfirmOpen(false)}
          onConfirm={handleConfirmAction}
          variant="danger"
          title="Cancel Order #ORD-84920?"
          message="This action will cancel fulfillment and record a refund authorization request. This operation cannot be undone."
          confirmLabel="Cancel Order"
          cancelLabel="Keep Order"
          isLoading={confirmLoading}
        />
      </div>
    </ToastProvider>
  )
}

export default UiKitGalleryClient
