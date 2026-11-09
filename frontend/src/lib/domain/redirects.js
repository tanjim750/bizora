/**
 * Authoritative redirect mappings from legacy routes to the 9-workspace architecture.
 * Per docs/frontend-overhaul/PLAN.md (T4-3) and DESIGN_SPEC.md section 3.
 */

import { RESOURCE_CONFIGS } from './resources.js'

export const LEGACY_SECTION_REDIRECTS = {
  overview: { workspace: 'overview', tab: 'overview' },
  customers: { workspace: 'customers', tab: 'list' },
  orders: { workspace: 'commerce', tab: 'orders' },
  products: { workspace: 'commerce', tab: 'products' },
  payments: { workspace: 'commerce', tab: 'payments' },
  finance: { workspace: 'commerce', tab: 'payments', view: 'timeline' },
  delivery: { workspace: 'commerce', tab: 'deliveries' },
  inbox: { workspace: 'support', tab: 'inbox' },
  queue: { workspace: 'support', tab: 'queue' },
  calls: { workspace: 'support', tab: 'calls' },
  marketing: { workspace: 'growth', tab: 'campaigns' },
  website: { workspace: 'growth', tab: 'website' },
  'website-performance': { workspace: 'growth', tab: 'website', view: 'performance' },
  insights: { workspace: 'intelligence', tab: 'facts' },
  assistant: { workspace: 'ai', tab: 'assistant' },
  actions: { workspace: 'ai', tab: 'actions' },
  identity: { workspace: 'admin', tab: 'identity' },
  contracts: { workspace: 'admin', tab: 'configuration' },
  configuration: { workspace: 'admin', tab: 'configuration' },
  observability: { workspace: 'admin', tab: 'integrations' },
}

/**
 * Resolves the destination URL for a legacy section name.
 */
export function resolveLegacySectionUrl(businessId, sectionKey, query = {}) {
  const mapping = LEGACY_SECTION_REDIRECTS[sectionKey]
  if (!mapping) return null

  const params = new URLSearchParams()
  if (mapping.tab) {
    params.set('tab', mapping.tab)
  }
  if (mapping.view) {
    params.set('view', mapping.view)
  }

  for (const [key, val] of Object.entries(query)) {
    if (key !== 'tab' && key !== 'view' && typeof val === 'string' && val) {
      params.set(key, val)
    }
  }

  const qs = params.toString()
  return `/business/${encodeURIComponent(businessId)}/${mapping.workspace}${qs ? `?${qs}` : ''}`
}

/**
 * Resolves the destination URL for a canonical resource list (legacy /resources/[resource]).
 */
export function resolveResourceListUrl(businessId, resourceName, query = {}) {
  const config = RESOURCE_CONFIGS[resourceName]
  if (!config) return null

  const workspace = config.workspace || 'commerce'
  const tab = config.tab || resourceName

  const params = new URLSearchParams()
  params.set('tab', tab)

  for (const [key, val] of Object.entries(query)) {
    if (key !== 'tab' && typeof val === 'string' && val) {
      params.set(key, val)
    }
  }

  const qs = params.toString()
  return `/business/${encodeURIComponent(businessId)}/${workspace}${qs ? `?${qs}` : ''}`
}

/**
 * Resolves the destination URL for a record detail link (legacy /records/[resource]/[id]).
 */
export function resolveRecordDetailUrl(businessId, resourceName, recordId, query = {}) {
  const config = RESOURCE_CONFIGS[resourceName]
  if (!config) return null

  const workspace = config.workspace || 'commerce'
  const tab = config.tab || resourceName

  const params = new URLSearchParams()
  params.set('tab', tab)
  params.set('open', `${resourceName}:${recordId}`)

  for (const [key, val] of Object.entries(query)) {
    if (key !== 'tab' && key !== 'open' && typeof val === 'string' && val) {
      params.set(key, val)
    }
  }

  const qs = params.toString()
  return `/business/${encodeURIComponent(businessId)}/${workspace}${qs ? `?${qs}` : ''}`
}
