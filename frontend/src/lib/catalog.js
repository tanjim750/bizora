export const SECTIONS = [
  { key: 'overview', label: 'Overview', group: 'Workspace', endpoint: 'overview/' },
  { key: 'customers', label: 'Customers', group: 'Business data', resource: 'customers' },
  { key: 'products', label: 'Products', group: 'Business data', resource: 'products' },
  { key: 'orders', label: 'Orders', group: 'Business data', resource: 'orders' },
  { key: 'payments', label: 'Payments', group: 'Business data', resource: 'payments' },
  { key: 'finance', label: 'Financial timeline', group: 'Business data', endpoint: 'financial-timeline/' },
  { key: 'insights', label: 'Business insights', group: 'Workspace' },
  { key: 'inbox', label: 'Inbox', group: 'Operations', resource: 'conversations' },
  { key: 'queue', label: 'Support queue', group: 'Operations', endpoint: 'support-queue/' },
  { key: 'marketing', label: 'Campaigns', group: 'Operations', resource: 'campaigns' },
  { key: 'website', label: 'Website', group: 'Operations', resource: 'visitors' },
  {
    key: 'website-performance',
    label: 'Website evidence',
    group: 'Operations',
    endpoint: 'website-performance/',
  },
  { key: 'delivery', label: 'Shipments', group: 'Operations', resource: 'shipments' },
  { key: 'calls', label: 'Calls', group: 'Operations', resource: 'calls' },
  { key: 'assistant', label: 'AI assistant', group: 'Assistance', endpoint: 'ai/recommendations/' },
  { key: 'actions', label: 'AI proposals', group: 'Assistance', endpoint: 'ai/actions/', manager: true },
  {
    key: 'identity',
    label: 'Identity review',
    group: 'Administration',
    endpoint: 'identity/conflicts/',
    manager: true,
  },
  { key: 'contracts', label: 'Service contracts', group: 'Administration', manager: true },
  { key: 'configuration', label: 'Configuration', group: 'Administration', manager: true },
  { key: 'observability', label: 'Integration health', group: 'Administration', manager: true },
]

export const MODULE_VIEWS = {
  insights: {
    prefix: 'overview',
    views: [
      'summary',
      'kpis',
      'trends',
      'issues',
      'health',
      'activity',
      'recommendations',
      'cross-domain',
      'catalog',
      'configuration',
    ],
    details: ['issues', 'recommendations'],
  },
  configuration: {
    prefix: 'configuration',
    views: [
      'effective',
      'changes',
      'profile',
      'general',
      'ai',
      'knowledge',
      'rules',
      'policies',
      'freshness',
      'providers',
      'connections',
      'sources',
      'reprocessing',
      'monitoring',
    ],
    details: ['connections', 'sources'],
  },
  observability: {
    prefix: 'observability',
    views: [
      'summary',
      'connections',
      'syncs',
      'failed-records',
      'webhooks',
      'freshness',
      'providers',
      'errors',
      'policies',
      'failed-records/groups',
      'syncs/statistics',
    ],
    details: ['connections', 'syncs', 'failed-records', 'webhooks', 'providers', 'errors'],
  },
}

export const RESOURCES = [
  'product-images',
  'products',
  'product-references',
  'customer-references',
  'variants',
  'customers',
  'contacts',
  'tags',
  'orders',
  'payments',
  'refunds',
  'conversations',
  'participants',
  'messages',
  'attachments',
  'notes',
  'campaigns',
  'campaign-metrics',
  'conversions',
  'ad-accounts',
  'ad-sets',
  'creatives',
  'ads',
  'visitors',
  'sessions',
  'website-events',
  'shipments',
  'shipment-events',
  'calls',
  'call-events',
  'transcripts',
  'callbacks',
]

export const MANAGER_ROLES = new Set(['OWNER', 'MANAGER'])
export const WRITER_ROLES = new Set(['OWNER', 'MANAGER', 'OPERATOR'])

export function businessPath(id, section = 'overview') {
  return `/business/${encodeURIComponent(id)}/${section}`
}

export function resourcePath(id, resource) {
  return `/business/${encodeURIComponent(id)}/resources/${resource}`
}

export function detailPath(id, resource, recordId) {
  return `/business/${encodeURIComponent(id)}/records/${resource}/${encodeURIComponent(recordId)}`
}

export function businessApiPath(id, suffix) {
  if (!Number.isSafeInteger(Number(id)) || Number(id) <= 0) throw new Error('Invalid business ID')
  return `businesses/${id}/${suffix}`
}
