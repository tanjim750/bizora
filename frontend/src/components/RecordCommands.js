'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { businessApiPath, WRITER_ROLES } from '@/lib/catalog'
import { clientApi } from '@/lib/clientApi'
import { fieldValue } from '@/lib/format'

const TRANSITIONS = {
  customers: { ACTIVE: ['INACTIVE', 'BLOCKED'], INACTIVE: ['ACTIVE', 'BLOCKED'], BLOCKED: ['ACTIVE'] },
  products: { ACTIVE: ['INACTIVE', 'ARCHIVED'], INACTIVE: ['ACTIVE', 'ARCHIVED'], ARCHIVED: ['ACTIVE'] },
  variants: { ACTIVE: ['INACTIVE', 'ARCHIVED'], INACTIVE: ['ACTIVE', 'ARCHIVED'], ARCHIVED: ['ACTIVE'] },
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
  conversations: {
    OPEN: ['PENDING', 'RESOLVED', 'CLOSED'],
    PENDING: ['OPEN', 'RESOLVED', 'CLOSED'],
    RESOLVED: ['OPEN', 'CLOSED'],
    CLOSED: ['OPEN'],
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
  calls: {
    INITIATED: ['RINGING', 'FAILED', 'CANCELLED'],
    RINGING: ['ANSWERED', 'MISSED', 'BUSY', 'FAILED', 'CANCELLED'],
    ANSWERED: ['COMPLETED', 'FAILED'],
  },
  campaigns: { ACTIVE: ['PAUSED', 'COMPLETED'], PAUSED: ['ACTIVE', 'COMPLETED'] },
  callbacks: { PENDING: ['COMPLETED', 'CANCELLED'] },
}

const text = (name, label, required = false) => ({ name, label, required })
const select = (name, label, options) => ({ name, label, options, required: true })

function descriptors(resource, record) {
  const entries = []
  const choices = TRANSITIONS[resource]?.[record.status] || []
  if (choices.length)
    entries.push({
      key: 'transition',
      title: 'Change recorded state',
      fields: [select('status', 'New state', choices), text('reason', 'Reason', true)],
      note: 'Records an internal state change; it does not execute provider transport.',
    })
  if (resource === 'conversations')
    entries.push(
      {
        key: 'priority',
        title: 'Set priority',
        fields: [
          select('priority', 'Priority', ['LOW', 'NORMAL', 'HIGH', 'URGENT']),
          text('reason', 'Reason', true),
        ],
      },
      {
        key: 'assign',
        title: 'Assign or release',
        fields: [
          select('assignee_type', 'Assignee type', ['AGENT', 'TEAM', 'AI', 'UNASSIGNED']),
          text('assignee_id', 'Agent user or team ID'),
          text('reason', 'Reason', true),
        ],
      },
      {
        key: 'handover',
        title: 'Handover',
        fields: [
          select('target', 'Target', ['HUMAN', 'AI']),
          text('assignee_id', 'Human assignee ID'),
          text('reason', 'Reason', true),
          text('summary', 'Summary'),
        ],
      },
      { key: 'note', title: 'Save private note', fields: [text('content', 'Note', true)] },
      {
        key: 'reply',
        title: 'Save pending reply',
        fields: [text('content', 'Reply text', true)],
        note: 'This creates a pending internal message. It is not delivered.',
      },
    )
  if (resource === 'messages')
    entries.push(
      { key: 'read', title: 'Mark read', fields: [] },
      {
        key: 'prepare-message',
        title: 'Prepare send request',
        fields: [],
        note: 'Preparation does not send the message.',
      },
    )
  if (resource === 'products')
    entries.push(
      {
        key: 'add-variant',
        title: 'Add variant',
        fields: [
          text('name', 'Name', true),
          text('sku', 'SKU', true),
          text('price', 'Price'),
          text('inventory_quantity', 'Inventory quantity'),
        ],
      },
      {
        key: 'map-product',
        title: 'Map reviewed source',
        fields: [
          text('connection_id', 'Connection ID', true),
          text('external_product_id', 'External product ID', true),
        ],
      },
    )
  if (resource === 'variants')
    entries.push({
      key: 'variant',
      title: 'Edit variant',
      fields: [
        text('name', 'Name'),
        text('price', 'Price'),
        text('inventory_quantity', 'Inventory quantity'),
      ],
    })
  if (resource === 'payments')
    entries.push({
      key: 'refund',
      title: 'Record refund request',
      fields: [text('amount', 'Amount', true), text('reason', 'Reason', true)],
      note: 'Records a refund request; settlement requires provider evidence.',
    })
  if (resource === 'calls' && record.customer)
    entries.push({
      key: 'callback',
      title: 'Request callback',
      fields: [text('reason', 'Reason', true), text('scheduled_at', 'Schedule at (ISO time with offset)')],
    })
  if (resource === 'calls')
    entries.push({
      key: 'prepare-call',
      title: 'Prepare call request',
      fields: [],
      note: 'Preparation does not place a call.',
    })
  if (resource === 'shipments')
    entries.push({
      key: 'prepare-shipment',
      title: 'Prepare shipment request',
      fields: [],
      note: 'Preparation does not submit a shipment.',
    })
  if (resource === 'callbacks')
    entries.push({
      key: 'schedule',
      title: 'Schedule callback',
      fields: [text('scheduled_at', 'Schedule at (ISO time with offset)', true)],
    })
  return entries
}

function normalizedValues(formData) {
  return Object.fromEntries([...formData.entries()].filter(([, value]) => String(value).trim() !== ''))
}

async function executeCommand(businessId, resource, record, key, values) {
  const base = businessApiPath(businessId, '')
  const id = record.id
  const source = record.integration_connection ? { connection_id: record.integration_connection } : {}
  const token = crypto.randomUUID()
  const ingest = (target, data, extra = source) =>
    clientApi(`${base}${target}`, {
      method: 'POST',
      body: { data, ...extra },
      headers: { 'Idempotency-Key': `frontend-${token}` },
    })
  if (key === 'transition')
    return clientApi(`${base}${resource}/${id}/transition`, {
      method: 'POST',
      body: { ...values, expected_status: record.status },
    })
  if (key === 'priority' || key === 'assign' || key === 'handover')
    return clientApi(`${base}conversations/${id}/${key}`, { method: 'POST', body: values })
  if (key === 'note') return ingest('notes', { conversation: id, ...values })
  if (key === 'reply')
    return ingest('messages', {
      conversation: id,
      external_message_id: `pending-ui-${token}`,
      direction: 'OUTGOING',
      sender_type: 'AGENT',
      ...values,
    })
  if (key === 'read') return clientApi(`${base}messages/${id}/read`, { method: 'POST', body: {} })
  if (key === 'add-variant') return ingest('variants', { product: id, ...values }, {})
  if (key === 'map-product')
    return ingest(
      'product-references',
      { product: id, external_product_id: values.external_product_id },
      { connection_id: Number(values.connection_id) },
    )
  if (key === 'variant')
    return clientApi(`${base}variants/${id}/update`, {
      method: 'POST',
      body: { data: values, expected_updated_at: record.updated_at },
    })
  if (key === 'refund')
    return ingest('refunds', { payment: id, external_refund_id: `ui-${token}`, ...values })
  if (key === 'callback')
    return ingest(
      'callbacks',
      {
        customer: record.customer,
        order: record.order || undefined,
        conversation: record.conversation || undefined,
        ...values,
      },
      {},
    )
  if (key === 'schedule')
    return clientApi(`${base}callbacks/${id}/schedule`, { method: 'POST', body: values })
  const operation = {
    'prepare-message': 'MESSAGE_SEND',
    'prepare-call': 'CALL_INITIATE',
    'prepare-shipment': 'SHIPMENT_SUBMIT',
  }[key]
  if (operation)
    return clientApi(`${base}operations/${operation}/${id}/prepare`, { method: 'POST', body: {} })
  throw new Error('Unsupported action')
}

function Command({ businessId, resource, record, descriptor }) {
  const router = useRouter()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const values = normalizedValues(new FormData(event.currentTarget))
      const response = await executeCommand(businessId, resource, record, descriptor.key, values)
      setResult(response)
      router.refresh()
    } catch (failure) {
      setError(failure.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <details className="command-card">
      <summary>{descriptor.title}</summary>
      <form onSubmit={submit}>
        {descriptor.note && <p className="helptext">{descriptor.note}</p>}
        {descriptor.fields.map((field) => (
          <div className="form-field" key={field.name}>
            <label htmlFor={`${descriptor.key}-${field.name}`}>
              {field.label}
              {field.required ? ' *' : ''}
            </label>
            {field.options ? (
              <select id={`${descriptor.key}-${field.name}`} name={field.name} required>
                {field.options.map((option) => (
                  <option key={option} value={option}>
                    {option.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            ) : field.name === 'content' || field.name === 'summary' || field.name === 'reason' ? (
              <textarea
                id={`${descriptor.key}-${field.name}`}
                name={field.name}
                rows={3}
                required={field.required}
              />
            ) : (
              <input id={`${descriptor.key}-${field.name}`} name={field.name} required={field.required} />
            )}
          </div>
        ))}
        <button className="button button-primary" disabled={busy}>
          {busy ? 'Saving…' : descriptor.title}
        </button>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        {result && (
          <div role="status" className="form-success">
            {descriptor.key.startsWith('prepare-')
              ? 'Request prepared; execution remains unavailable.'
              : descriptor.key === 'reply'
                ? 'Reply saved as pending — not delivered.'
                : 'Internal change saved.'}
          </div>
        )}
      </form>
    </details>
  )
}

export function RecordCommands({ business, resource, record }) {
  if (!WRITER_ROLES.has(business.role)) return null
  const commands = descriptors(resource, record)
  if (!commands.length) return null
  return (
    <section className="command-section">
      <div className="section-header">
        <div>
          <h2>Authorized actions</h2>
          <p>State changes are internal. Provider delivery needs separate confirmed evidence.</p>
        </div>
      </div>
      <div className="command-grid">
        {commands.map((command) => (
          <Command
            key={command.key}
            businessId={business.id}
            resource={resource}
            record={record}
            descriptor={command}
          />
        ))}
      </div>
    </section>
  )
}
