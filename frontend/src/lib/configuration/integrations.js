import { choices } from './sections.js'
import { connectionsPath, connectionPath } from './paths.js'
import { recordSource } from './normalize.js'
import { REASON_SPEC, draftFromSettings } from './fieldKit.js'
import { buildResourceSave } from './resources.js'

export function normalizeProvider(row) {
  if (!row || typeof row !== 'object') {
    return {
      id: null,
      key: '',
      name: '',
      category: '',
      entities: [],
      scopes: [],
      mock_supported: false,
    }
  }

  const caps = row.capabilities || {}

  return {
    id: row.id != null ? Number(row.id) : null,
    key: row.key != null ? String(row.key) : '',
    name: row.name != null ? String(row.name) : '',
    category: row.category != null ? String(row.category) : '',
    entities: Array.isArray(caps.entities) ? caps.entities.map(String) : [],
    scopes: Array.isArray(caps.scopes) ? caps.scopes.map(String) : [],
    mock_supported: Boolean(row.mock_supported),
  }
}

export const REQUIRED_SCOPE = {
  PRODUCT: 'READ_PRODUCTS',
  CUSTOMER: 'READ_CUSTOMERS',
  ORDER: 'READ_ORDERS',
  PAYMENT: 'READ_PAYMENTS',
  REFUND: 'READ_PAYMENTS',
  CAMPAIGN: 'READ_CAMPAIGNS',
  CAMPAIGN_METRIC: 'READ_METRICS',
  CONVERSION: 'READ_METRICS',
  WEBSITE_VISITOR: 'READ_ANALYTICS',
  WEBSITE_SESSION: 'READ_ANALYTICS',
  WEBSITE_EVENT: 'READ_ANALYTICS',
  CONVERSATION: 'READ_CONVERSATIONS',
  MESSAGE: 'READ_CONVERSATIONS',
  SHIPMENT: 'READ_SHIPMENTS',
  SHIPMENT_EVENT: 'READ_SHIPMENTS',
  CALL: 'READ_CALLS',
  CALL_EVENT: 'READ_CALLS',
  TRANSCRIPT: 'READ_CALLS',
}

export function requiredScope(entity, category) {
  const cat = String(category || '').toUpperCase()
  if (entity === 'CUSTOMER' && ['COMMUNICATION', 'SUPPORT', 'MESSAGING'].includes(cat)) {
    return 'READ_CONVERSATIONS'
  }
  return REQUIRED_SCOPE[entity]
}

export function connectionSpecs(record, provider) {
  const entityOpts = provider?.entities ? choices(...provider.entities) : []
  const scopeOpts = provider?.scopes ? choices(...provider.scopes) : []

  return [
    {
      path: 'name',
      label: 'Name',
      type: 'text',
      required: true,
      maxLength: 150,
    },
    {
      path: 'enabled',
      label: 'Enabled',
      type: 'bool',
      hint: 'Disabled connections cannot run operations such as tests and retries.',
    },
    {
      path: 'entities',
      label: 'Records this connection may process',
      type: 'multi',
      options: entityOpts,
      maxItems: 20,
      hint: 'Each record type needs its read scope.',
    },
    {
      path: 'scopes',
      label: 'Permissions',
      type: 'multi',
      options: scopeOpts,
      maxItems: 20,
    },
    {
      path: 'sync.mode',
      label: 'Sync mode',
      type: 'select',
      required: true,
      options: choices('FULL', 'INCREMENTAL', 'SCHEDULED', 'MANUAL'),
    },
    {
      path: 'sync.interval_seconds',
      label: 'Sync interval (seconds)',
      type: 'int',
      required: true,
      min: 60,
      max: 2592000,
    },
    REASON_SPEC,
  ]
}

export function validateConnection(draft, record, provider) {
  const errs = {}

  const selectedEntities = Array.isArray(draft?.entities) ? draft.entities : []
  const selectedScopes = Array.isArray(draft?.scopes) ? draft.scopes : []

  for (const ent of selectedEntities) {
    const req = requiredScope(ent, provider?.category)
    if (req && !selectedScopes.includes(req)) {
      errs.entities = `${ent} needs the ${req} scope.`
      break
    }
  }

  if (!record?.settings?.is_mock && draft?.enabled && !record?.settings?.credentials?.configured) {
    errs.enabled = 'Live connections need credential references configured on the server.'
  }

  return errs
}

export const CONNECTIONS_RESOURCE = {
  id: 'connections',
  title: 'Connections',
  singular: 'connection',
  updateMethod: 'PATCH',
  keyField: false,
  createPath: null,
  notes: [
    'This is the setup view. Health, syncs and the connection test are on the Integrations & Sync tab.',
    'Credentials are secret references kept on the server. This screen never shows or accepts secret values.',
  ],
  listPath: (id, opts) => connectionsPath(id, opts),
  itemPath: (id, record) => connectionPath(id, record.id),
  nameOf: (record) => record?.settings?.name || `#${record?.id}`,
  columns: [
    { key: 'name', label: 'Name', text: (r) => r.settings?.name || '—' },
    {
      key: 'provider',
      label: 'Provider',
      text: (r, ctx) => {
        const prov = (ctx?.providers || []).find((p) => p.id === r.settings?.provider_id)
        return prov ? prov.name : `Provider #${r.settings?.provider_id || '—'}`
      },
    },
    {
      key: 'status',
      label: 'Status',
      chip: true,
      text: (r) => (r.status === 'ACTIVE' ? 'Enabled' : 'Disabled'),
    },
    {
      key: 'mode',
      label: 'Mode',
      text: (r) => (r.settings?.is_mock ? 'Mock (simulated)' : 'Live'),
    },
    {
      key: 'credentials',
      label: 'Credentials',
      text: (r) =>
        r.settings?.credentials?.configured
          ? `Configured: ${(r.settings.credentials.fields || []).join(', ')}`
          : 'Not configured',
    },
  ],
  lockedPaths: () => [],
  specsFor: ({ record, context }) => {
    const prov = (context?.providers || []).find((p) => p.id === record?.settings?.provider_id)
    return connectionSpecs(record, prov)
  },
  draftFor: (record, context) => {
    const prov = (context?.providers || []).find((p) => p.id === record?.settings?.provider_id)
    const specs = connectionSpecs(record, prov)
    return draftFromSettings(specs, recordSource(record || { status: 'ACTIVE' }))
  },
  build: ({ record, draft, context }) => {
    const prov = (context?.providers || []).find((p) => p.id === record?.settings?.provider_id)
    const specs = connectionSpecs(record, prov)
    const extraErrors = validateConnection(draft, record, prov)
    return buildResourceSave({
      specs,
      record,
      draft,
      creating: false,
      extraErrors,
    })
  },
}
