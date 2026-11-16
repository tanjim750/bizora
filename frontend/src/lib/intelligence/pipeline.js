import { businessApiPath, MANAGER_ROLES } from '../catalog.js'

export function PIPELINE_RUN_PATH(businessId) {
  return businessApiPath(businessId, 'intelligence/pipeline/run/')
}

export function GRAPH_REBUILD_PATH(businessId) {
  return businessApiPath(businessId, 'graph/rebuild/')
}

export function rebuildBody({ clean = false } = {}) {
  if (typeof clean !== 'boolean') {
    throw new Error('clean must be a boolean')
  }
  return { clean }
}

export function isManager(role) {
  if (!role || typeof role !== 'string') return false
  return MANAGER_ROLES.has(role.toUpperCase())
}

export function summarizePipelineResult(data) {
  if (!data || typeof data !== 'object') return []
  const rows = []
  if (data.status != null) {
    rows.push({ label: 'Status', value: String(data.status) })
  }
  if (data.relationships_reconciled && typeof data.relationships_reconciled === 'object') {
    const rr = data.relationships_reconciled
    if (rr.created != null) rows.push({ label: 'Relationships created', value: rr.created })
    if (rr.updated != null) rows.push({ label: 'Relationships updated', value: rr.updated })
    if (rr.unchanged != null) rows.push({ label: 'Relationships unchanged', value: rr.unchanged })
    if (rr.invalidated != null) rows.push({ label: 'Relationships invalidated', value: rr.invalidated })
  }
  if (data.quarantined_records != null) {
    rows.push({ label: 'Quarantined records', value: data.quarantined_records })
  }
  if (data.active_facts_count != null) {
    rows.push({ label: 'Active facts', value: data.active_facts_count })
  }
  if (data.open_issues_count != null) {
    rows.push({ label: 'Open issues', value: data.open_issues_count })
  }
  if (data.metrics_computed != null) {
    rows.push({ label: 'Metrics computed', value: data.metrics_computed })
  }
  return rows
}

export function summarizeRebuildResult(data) {
  if (!data || typeof data !== 'object') return []
  const keys = [
    ['nodes_created', 'Nodes created'],
    ['nodes_updated', 'Nodes updated'],
    ['nodes_pruned', 'Nodes pruned'],
    ['edges_created', 'Edges created'],
    ['edges_updated', 'Edges updated'],
    ['edges_pruned', 'Edges pruned'],
    ['total_nodes', 'Total nodes'],
    ['total_edges', 'Total edges'],
  ]
  const rows = []
  for (const [key, label] of keys) {
    if (data[key] != null) {
      rows.push({ label, value: data[key] })
    }
  }
  return rows
}
