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
  Palette,
  CheckSquare,
  Bell,
  Sliders,
  Table as TableIcon,
  GitCommit,
  BarChart3,
  Check,
  Copy,
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
  ChartCard,
  TrendLine,
  BarCompare,
  Sparkline,
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

function TokensShowcase() {
  const [copiedToken, setCopiedToken] = useState(null)

  const copyToClipboard = (tokenName, text) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(text)
      setCopiedToken(tokenName)
      setTimeout(() => setCopiedToken(null), 1800)
    }
  }

  const surfaceTokens = [
    { name: 'Canvas', cssVar: '--color-canvas', bg: 'var(--color-canvas)' },
    { name: 'Surface (Card)', cssVar: '--color-surface', bg: 'var(--color-surface)' },
    { name: 'Elevated Surface', cssVar: '--color-surface-elevated', bg: 'var(--color-surface-elevated)' },
    { name: 'Recessed Surface', cssVar: '--color-surface-recessed', bg: 'var(--color-surface-recessed)' },
    { name: 'Subtle Surface', cssVar: '--color-surface-subtle', bg: 'var(--color-surface-subtle)' },
    { name: 'Border Hairline', cssVar: '--color-border', bg: 'var(--color-border)' },
  ]

  const semanticTokens = [
    { name: 'Primary Cobalt', cssVar: '--color-primary', bg: 'var(--color-primary)' },
    { name: 'Primary Subtle', cssVar: '--color-primary-subtle', bg: 'var(--color-primary-subtle)' },
    { name: 'Success Emerald', cssVar: '--color-success', bg: 'var(--color-success)' },
    { name: 'Success Subtle', cssVar: '--color-success-subtle', bg: 'var(--color-success-subtle)' },
    { name: 'Warning Amber', cssVar: '--color-warning', bg: 'var(--color-warning)' },
    { name: 'Warning Subtle', cssVar: '--color-warning-subtle', bg: 'var(--color-warning-subtle)' },
    { name: 'Danger Crimson', cssVar: '--color-danger', bg: 'var(--color-danger)' },
    { name: 'Danger Subtle', cssVar: '--color-danger-subtle', bg: 'var(--color-danger-subtle)' },
    { name: 'Info Steel', cssVar: '--color-info', bg: 'var(--color-info)' },
    { name: 'Info Subtle', cssVar: '--color-info-subtle', bg: 'var(--color-info-subtle)' },
  ]

  const chartTokens = [
    { name: 'Series 1 (Blue)', cssVar: '--chart-1', bg: 'var(--chart-1)' },
    { name: 'Series 2 (Orange)', cssVar: '--chart-2', bg: 'var(--chart-2)' },
    { name: 'Series 3 (Teal)', cssVar: '--chart-3', bg: 'var(--chart-3)' },
    { name: 'Series 4 (Gold)', cssVar: '--chart-4', bg: 'var(--chart-4)' },
    { name: 'Series 5 (Rose)', cssVar: '--chart-5', bg: 'var(--chart-5)' },
    { name: 'Series 6 (Green)', cssVar: '--chart-6', bg: 'var(--chart-6)' },
    { name: 'Series 7 (Violet)', cssVar: '--chart-7', bg: 'var(--chart-7)' },
    { name: 'Series 8 (Coral)', cssVar: '--chart-8', bg: 'var(--chart-8)' },
  ]

  const typeSpecimens = [
    { level: 'Page Title', size: '26px / 34px', weight: '600', sample: 'Executive Business Overview' },
    {
      level: 'Section Title',
      size: '18px / 26px',
      weight: '600',
      sample: 'Customer Accounts & Ledger Summary',
    },
    { level: 'Card Title', size: '16px / 24px', weight: '600', sample: 'Payment Gateway Configuration' },
    { level: 'Subsection', size: '15px / 22px', weight: '500', sample: 'Reconciled transaction volume' },
    {
      level: 'Body Regular',
      size: '14px / 21px',
      weight: '400',
      sample: 'Standard copy for table content, labels, and notices.',
    },
    {
      level: 'Table / Compact',
      size: '13px / 20px',
      weight: '400',
      sample: 'Dense tabular records and timeline descriptions.',
    },
    {
      level: 'Caption',
      size: '12px / 16px',
      weight: '400',
      sample: 'Monospace metadata, timestamps, and secondary status context.',
    },
    { level: 'Overline', size: '11px / 16px', weight: '600', sample: 'STATUS · SPEC T3-1 · ENTERPRISE' },
  ]

  return (
    <section id="section-tokens" className="surface" style={{ marginTop: 'var(--space-6)' }}>
      <div className="section-header">
        <div>
          <h2>Design Tokens & High-Craft Foundations</h2>
          <p>
            WCAG 2.2 AA calibrated formal color palette, layered surface elevations, and typographic scale.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
        {/* Surface & Depth Architecture */}
        <div>
          <div className="ui-kit-demo-label">
            <span className="ui-kit-demo-title">Surface Elevation & Recessed Wells</span>
            <span className="text-caption text-muted">Hairline borders with subtle specular highlights</span>
          </div>
          <div className="token-swatch-grid">
            {surfaceTokens.map((item) => (
              <button
                key={item.cssVar}
                type="button"
                className="token-swatch-card"
                onClick={() => copyToClipboard(item.cssVar, `var(${item.cssVar})`)}
                title={`Click to copy var(${item.cssVar})`}
                style={{ textAlign: 'left', cursor: 'pointer', border: '1px solid var(--color-border)' }}
              >
                <div className="token-swatch-color" style={{ background: item.bg }} />
                <div className="token-swatch-info">
                  <span className="token-swatch-name">{item.name}</span>
                  <span className="token-swatch-var">
                    {copiedToken === item.cssVar ? 'Copied!' : item.cssVar}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Semantic Tones */}
        <div>
          <div className="ui-kit-demo-label">
            <span className="ui-kit-demo-title">Semantic Tones & Translucent Tint Fills</span>
            <span className="text-caption text-muted">WCAG 4.5:1 text contrast on subtles</span>
          </div>
          <div className="token-swatch-grid">
            {semanticTokens.map((item) => (
              <button
                key={item.cssVar}
                type="button"
                className="token-swatch-card"
                onClick={() => copyToClipboard(item.cssVar, `var(${item.cssVar})`)}
                title={`Click to copy var(${item.cssVar})`}
                style={{ textAlign: 'left', cursor: 'pointer', border: '1px solid var(--color-border)' }}
              >
                <div className="token-swatch-color" style={{ background: item.bg }} />
                <div className="token-swatch-info">
                  <span className="token-swatch-name">{item.name}</span>
                  <span className="token-swatch-var">
                    {copiedToken === item.cssVar ? 'Copied!' : item.cssVar}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Chart Series Tokens */}
        <div>
          <div className="ui-kit-demo-label">
            <span className="ui-kit-demo-title">Data Visualization Spectrum (T3-7)</span>
            <span className="text-caption text-muted">8 distinct accessible dataviz categorical hues</span>
          </div>
          <div className="token-swatch-grid">
            {chartTokens.map((item) => (
              <button
                key={item.cssVar}
                type="button"
                className="token-swatch-card"
                onClick={() => copyToClipboard(item.cssVar, `var(${item.cssVar})`)}
                title={`Click to copy var(${item.cssVar})`}
                style={{ textAlign: 'left', cursor: 'pointer', border: '1px solid var(--color-border)' }}
              >
                <div className="token-swatch-color" style={{ background: item.bg }} />
                <div className="token-swatch-info">
                  <span className="token-swatch-name">{item.name}</span>
                  <span className="token-swatch-var">
                    {copiedToken === item.cssVar ? 'Copied!' : item.cssVar}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Typography Hierarchy */}
        <div>
          <div className="ui-kit-demo-label">
            <span className="ui-kit-demo-title">Typography Hierarchy (IBM Plex Sans & Mono)</span>
            <span className="text-caption text-muted">Strict vertical rhythm with tabular numerals</span>
          </div>
          <div className="ui-kit-demo-box" style={{ overflowX: 'auto' }}>
            <table className="type-specimen-table">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                  <th
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: '12px',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    LEVEL
                  </th>
                  <th
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: '12px',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    SPEC
                  </th>
                  <th
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: '12px',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    WEIGHT
                  </th>
                  <th
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      fontSize: '12px',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    SAMPLE RENDERING
                  </th>
                </tr>
              </thead>
              <tbody>
                {typeSpecimens.map((spec) => (
                  <tr key={spec.level}>
                    <td style={{ fontWeight: 600, fontSize: '12px', whiteSpace: 'nowrap' }}>{spec.level}</td>
                    <td
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '12px',
                        color: 'var(--color-text-muted)',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {spec.size}
                    </td>
                    <td
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '12px',
                        color: 'var(--color-text-muted)',
                      }}
                    >
                      {spec.weight}
                    </td>
                    <td style={{ color: 'var(--color-text)' }}>
                      {spec.level === 'Overline' ? (
                        <span
                          style={{
                            fontSize: '12px',
                            fontWeight: 600,
                            letterSpacing: '0.06em',
                            textTransform: 'uppercase',
                          }}
                        >
                          {spec.sample}
                        </span>
                      ) : spec.level === 'Page Title' ? (
                        <span style={{ fontSize: '20px', fontWeight: 600 }}>{spec.sample}</span>
                      ) : spec.level === 'Section Title' ? (
                        <span style={{ fontSize: '16px', fontWeight: 600 }}>{spec.sample}</span>
                      ) : (
                        <span style={{ fontSize: '14px', fontWeight: spec.weight === '600' ? 600 : 400 }}>
                          {spec.sample}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
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

        {/* Sticky Section Quick-Jump Nav Bar */}
        <nav aria-label="UI Kit sections" className="ui-kit-nav-bar">
          <a href="#section-tokens" className="ui-kit-nav-pill">
            <Palette size={13} aria-hidden="true" />
            <span>00 Tokens</span>
          </a>
          <a href="#section-forms" className="ui-kit-nav-pill">
            <CheckSquare size={13} aria-hidden="true" />
            <span>01 Forms</span>
          </a>
          <a href="#section-feedback" className="ui-kit-nav-pill">
            <Bell size={13} aria-hidden="true" />
            <span>02 Feedback</span>
          </a>
          <a href="#section-overlays" className="ui-kit-nav-pill">
            <Sliders size={13} aria-hidden="true" />
            <span>03 Overlays</span>
          </a>
          <a href="#section-tables" className="ui-kit-nav-pill">
            <TableIcon size={13} aria-hidden="true" />
            <span>04 Tables</span>
          </a>
          <a href="#section-evidence" className="ui-kit-nav-pill">
            <GitCommit size={13} aria-hidden="true" />
            <span>05 Evidence</span>
          </a>
          <a href="#section-charts" className="ui-kit-nav-pill">
            <BarChart3 size={13} aria-hidden="true" />
            <span>06 Charts</span>
          </a>
        </nav>

        {/* Section 0: Design Tokens & Foundations */}
        <TokensShowcase />

        {/* Section 1: Form Basics */}
        <section id="section-forms" className="surface" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-header">
            <div>
              <h2>Form Controls & Actions (T3-1)</h2>
              <p>WCAG AA accessible form fields, states, sizes, and native control stylings.</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
            <div className="ui-kit-demo-box">
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Button Hierarchy & Micro-States</span>
                <span className="text-caption text-muted">
                  Primary top highlight, secondary e1 shadow, active translate
                </span>
              </div>
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

            <div className="ui-kit-demo-box">
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Checkboxes & Radios</span>
                <span className="text-caption text-muted">
                  Native accessible controls with custom theme accent
                </span>
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
          </div>
        </section>

        {/* Section 2: Feedback & Status */}
        <section id="section-feedback" className="surface" style={{ marginTop: 'var(--space-6)' }}>
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

            <div className="ui-kit-demo-box">
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Status Chips (Icon + Exact Label, Translucent Tint)</span>
                <span className="text-caption text-muted">Never color alone · WCAG 2.2 AA compliant</span>
              </div>
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

            <div className="ui-kit-demo-box">
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Severity Chips & Confidence Meters</span>
                <span className="text-caption text-muted">Recessed track with smooth rounded indicator</span>
              </div>
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
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Executive KPI Tiles</span>
                <span className="text-caption text-muted">Sleek trend badges with tabular figures</span>
              </div>
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

            <div className="ui-kit-demo-box">
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Ephemeral Toast Notifications</span>
                <span className="text-caption text-muted">
                  Top-right floating portal stack with auto-dismiss
                </span>
              </div>
              <ToastDemos />
            </div>

            <div>
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Calm Unavailable State</span>
                <span className="text-caption text-muted">
                  Normal authoritative data, never error red or zero
                </span>
              </div>
              <UnavailableState
                title="Context Graph Engine"
                owner="Business Graph (BG-1)"
                reason="Context graph service is unmounted in this environment. Authoritative node relationships will activate automatically upon mount."
                action={
                  <Button variant="secondary" size="sm">
                    Inspect Logs
                  </Button>
                }
              ></UnavailableState>
            </div>
          </div>
        </section>

        {/* Section 3: Overlays & Navigation */}
        <section id="section-overlays" className="surface" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-header">
            <div>
              <h2>Overlays & Navigation (T3-3)</h2>
              <p>Path-segment tabs, focus-trapped drawers, accessible modals, and filter toolbars.</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
            <div>
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Tab Navigation with Count Chips</span>
                <span className="text-caption text-muted">
                  Segmented tab switching with active indicator line
                </span>
              </div>
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

            <div className="ui-kit-demo-box">
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Overlay Triggers (Focus Trap & Escape Handlers)</span>
                <span className="text-caption text-muted">Dialogs & drawers render into Portal root</span>
              </div>
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
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Filter Bar & Active Filter Pills</span>
                <span className="text-caption text-muted">Removable filter tags with clear all action</span>
              </div>
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

            <div className="ui-kit-demo-box">
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">Pagination Footer</span>
                <span className="text-caption text-muted">Exact record range display (1–25 of 1,284)</span>
              </div>
              <Pagination page={page} pageSize={25} total={1284} onPageChange={(p) => setPage(p)} />
            </div>
          </div>
        </section>

        {/* Section 4: Data Table */}
        <section id="section-tables" className="surface" style={{ marginTop: 'var(--space-6)' }}>
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
        <section id="section-evidence" className="surface" style={{ marginTop: 'var(--space-6)' }}>
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
              <div className="ui-kit-demo-label">
                <span className="ui-kit-demo-title">The Evidence Thread</span>
                <span className="text-caption text-muted">Continuous vertical spine joining events</span>
              </div>
              <Timeline events={timelineEvents} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              <div>
                <div className="ui-kit-demo-label">
                  <span className="ui-kit-demo-title">Grounding Evidence Panel</span>
                  <span className="text-caption text-muted">Transparent provenance citations</span>
                </div>
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

              <div className="ui-kit-demo-box">
                <div className="ui-kit-demo-label">
                  <span className="ui-kit-demo-title">Copyable Identifiers & Codes</span>
                  <span className="text-caption text-muted">Monospace with quick copy tooltip</span>
                </div>
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

        {/* Section 6: Charts & Visualizations (T3-7) */}
        <section id="section-charts" className="surface" style={{ marginTop: 'var(--space-6)' }}>
          <div className="section-header">
            <div>
              <h2>Charts & Visualizations (T3-7)</h2>
              <p>
                Recharts wrappers driven by formal theme tokens (--chart-*), with accessible data table
                toggle, calm empty/unavailable states, and responsive aspect ratio.
              </p>
            </div>
          </div>

          <div className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
            <ChartCard
              title="Gross Revenue & Volume"
              subtitle="7-day rolling revenue trend (BDT)"
              badge={<SimulatedBadge />}
              tableData={[
                { id: '1', date: '04 Nov', revenue: 24500, orders: 18 },
                { id: '2', date: '05 Nov', revenue: 31200, orders: 24 },
                { id: '3', date: '06 Nov', revenue: 19800, orders: 15 },
                { id: '4', date: '07 Nov', revenue: 42100, orders: 32 },
                { id: '5', date: '08 Nov', revenue: 38400, orders: 29 },
                { id: '6', date: '09 Nov', revenue: 51200, orders: 41 },
                { id: '7', date: '10 Nov', revenue: 46800, orders: 36 },
              ]}
              tableColumns={[
                { key: 'date', label: 'Date' },
                { key: 'revenue', label: 'Revenue (BDT)', type: 'money' },
                { key: 'orders', label: 'Orders', align: 'right' },
              ]}
              ariaLabel="Gross revenue 7-day trend showing growth from BDT 24,500 to BDT 46,800"
            >
              <TrendLine
                data={[
                  { date: '04 Nov', revenue: 24500 },
                  { date: '05 Nov', revenue: 31200 },
                  { date: '06 Nov', revenue: 19800 },
                  { date: '07 Nov', revenue: 42100 },
                  { date: '08 Nov', revenue: 38400 },
                  { date: '09 Nov', revenue: 51200 },
                  { date: '10 Nov', revenue: 46800 },
                ]}
                xKey="date"
                yKey="revenue"
                series={[{ key: 'revenue', name: 'Revenue', color: 'var(--chart-1)' }]}
                valueFormatter={(v) => `BDT ${(v / 1000).toFixed(0)}k`}
              />
            </ChartCard>

            <ChartCard
              title="Channel Distribution"
              subtitle="Direct vs referral sales by channel"
              badge={<SimulatedBadge />}
              tableData={[
                { id: '1', category: 'Online Store', direct: 34000, referral: 12000 },
                { id: '2', category: 'Marketplace', direct: 22000, referral: 8500 },
                { id: '3', category: 'Social Shop', direct: 18000, referral: 14000 },
                { id: '4', category: 'B2B Wholesale', direct: 45000, referral: 5000 },
              ]}
              tableColumns={[
                { key: 'category', label: 'Sales Channel' },
                { key: 'direct', label: 'Direct (BDT)', type: 'money' },
                { key: 'referral', label: 'Referral (BDT)', type: 'money' },
              ]}
              ariaLabel="Sales by channel comparison chart"
            >
              <BarCompare
                data={[
                  { category: 'Online', direct: 34000, referral: 12000 },
                  { category: 'Market', direct: 22000, referral: 8500 },
                  { category: 'Social', direct: 18000, referral: 14000 },
                  { category: 'B2B', direct: 45000, referral: 5000 },
                ]}
                xKey="category"
                series={[
                  { key: 'direct', name: 'Direct', color: 'var(--chart-1)' },
                  { key: 'referral', name: 'Referral', color: 'var(--chart-2)' },
                ]}
                valueFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              />
            </ChartCard>
          </div>

          <div className="grid-2">
            <ChartCard
              title="Telemetry Status"
              subtitle="Empty state demonstration"
              empty
              emptyTitle="No time series points recorded"
              emptyDescription="No orders were placed during the selected comparison window."
            />

            <ChartCard
              title="Warehouse Sensor Feed"
              subtitle="Simulated telemetry from external integration"
              unavailable
              unavailableReason="Cold chain IoT sensor telemetry service is currently offline"
            />
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
