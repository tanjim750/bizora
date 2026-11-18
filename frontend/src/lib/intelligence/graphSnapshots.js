import { businessApiPath } from '../catalog.js'
import { enumLabel } from '../format/text.js'
import { parseGraphEntityId, graphNodeLabel } from './graphExplore.js'
import { confidencePercent } from './facts.js'

export const SNAPSHOT_LIST_CAP = 50
export const SNAPSHOT_ROW_CAP = 100
export const SNAPSHOT_TIMELINE_CAP = 20
export const SNAPSHOT_SUMMARY_CAP = 20

export const SNAPSHOT_TYPE_LABELS = Object.freeze({
  BUSINESS: 'Whole business',
  CUSTOMER: 'Customer journey',
  ORDER: 'Order journey',
  PRODUCT: 'Product journey',
  CAMPAIGN: 'Campaign journey',
})

export function snapshotTypeLabel(type) {
  if (type === null || type === undefined) return '—'
  if (SNAPSHOT_TYPE_LABELS[type]) return SNAPSHOT_TYPE_LABELS[type]
  return enumLabel(type)
}

export function snapshotListPath(businessId) {
  return businessApiPath(businessId, 'graph/snapshots/')
}

export function snapshotDetailPath(businessId, snapshotId) {
  const parsedId = parseGraphEntityId(snapshotId, 'Snapshot ID')
  return businessApiPath(businessId, `graph/snapshots/${parsedId}/`)
}

export function normalizeSnapshotList(data) {
  const list = Array.isArray(data)
    ? data
    : data && typeof data === 'object' && Array.isArray(data.results)
      ? data.results
      : []

  return list
    .filter((item) => item && typeof item === 'object' && Number.isInteger(item.id) && item.id > 0)
    .map((item) => ({
      id: item.id,
      name: typeof item.name === 'string' && item.name.trim() ? item.name.trim() : 'Untitled snapshot',
      snapshotType: item.snapshot_type || null,
      nodeCount: Number.isInteger(item.node_count) ? item.node_count : null,
      edgeCount: Number.isInteger(item.edge_count) ? item.edge_count : null,
      generatedAt: item.generated_at || null,
    }))
}

const FILTER_KEYS = [
  { key: 'entity_types', label: 'Entity types' },
  { key: 'relationship_types', label: 'Relationship types' },
  { key: 'min_confidence', label: 'Minimum confidence' },
  { key: 'status', label: 'Status' },
  { key: 'channel', label: 'Channel' },
  { key: 'provider', label: 'Provider' },
  { key: 'dimensions', label: 'Dimensions' },
  { key: 'time_from', label: 'From' },
  { key: 'time_to', label: 'To' },
  { key: 'valid_at', label: 'Valid at' },
]

export function snapshotFilterRows(filters) {
  if (!filters || typeof filters !== 'object' || Array.isArray(filters)) {
    return []
  }

  const rows = []
  for (const { key, label } of FILTER_KEYS) {
    const val = filters[key]
    if (val === null || val === undefined) continue
    if (typeof val === 'string' && val.trim() === '') continue
    if (Array.isArray(val) && val.length === 0) continue

    let valueStr = ''
    if (Array.isArray(val)) {
      valueStr = val.join(', ')
    } else if (typeof val === 'object') {
      valueStr = JSON.stringify(val)
    } else {
      valueStr = String(val)
    }

    rows.push({ key, label, value: valueStr })
  }

  return rows
}

export function snapshotSummaryRows(summary) {
  if (!summary || typeof summary !== 'object' || Array.isArray(summary)) {
    return []
  }

  const rows = []
  for (const [key, val] of Object.entries(summary)) {
    if (
      typeof val === 'string' ||
      (typeof val === 'number' && Number.isFinite(val)) ||
      typeof val === 'boolean'
    ) {
      rows.push({ label: enumLabel(key), value: String(val) })
      if (rows.length >= SNAPSHOT_SUMMARY_CAP) break
    }
  }

  return rows
}

export function normalizeSnapshotDetail(data, { rowCap = SNAPSHOT_ROW_CAP } = {}) {
  if (!data || typeof data !== 'object' || !Number.isInteger(data.id) || data.id <= 0) {
    return null
  }

  const name = typeof data.name === 'string' && data.name.trim() ? data.name.trim() : 'Untitled snapshot'
  const snapshotType = data.snapshot_type || null
  const generatedAt = data.generated_at || null
  const storedNodeCount = Number.isInteger(data.node_count) ? data.node_count : null
  const storedEdgeCount = Number.isInteger(data.edge_count) ? data.edge_count : null

  const body =
    data.snapshot_data && typeof data.snapshot_data === 'object' && !Array.isArray(data.snapshot_data)
      ? data.snapshot_data
      : {}

  const rawNodes = Array.isArray(body.nodes) ? body.nodes.filter((n) => n && typeof n === 'object') : []
  const rawEdges = Array.isArray(body.edges) ? body.edges.filter((e) => e && typeof e === 'object') : []
  const rawTimeline = Array.isArray(body.timeline)
    ? body.timeline.filter((t) => t && typeof t === 'object')
    : []

  const loadedNodeCount = rawNodes.length
  const loadedEdgeCount = rawEdges.length
  const timelineCount = rawTimeline.length

  const countsMatch =
    (storedNodeCount === null || storedNodeCount === loadedNodeCount) &&
    (storedEdgeCount === null || storedEdgeCount === loadedEdgeCount)

  const labelById = new Map()
  for (const n of rawNodes) {
    if (n.id !== undefined && n.id !== null) {
      labelById.set(n.id, graphNodeLabel(n))
    }
  }

  const nodes = rawNodes.slice(0, rowCap).map((n) => ({
    id: n.id,
    entityType: n.entity_type,
    entityId: n.entity_id,
    label: graphNodeLabel(n),
  }))

  const edges = rawEdges.slice(0, rowCap).map((e) => ({
    id: e.id,
    relationshipType: e.relationship_type || 'Unknown',
    sourceLabel: labelById.get(e.source_node_id) || `Node ${e.source_node_id}`,
    targetLabel: labelById.get(e.target_node_id) || `Node ${e.target_node_id}`,
    confidencePercent: confidencePercent(e.confidence),
  }))

  const timeline = rawTimeline.slice(0, SNAPSHOT_TIMELINE_CAP).map((t) => ({
    stage: t.stage || null,
    label: graphNodeLabel({
      label: t.label,
      entity_type: t.entity_type,
      entity_id: t.entity_id,
    }),
    entityType: t.entity_type,
    entityId: t.entity_id,
    timestamp: t.timestamp || null,
  }))

  const nodesCapped = rawNodes.length > rowCap
  const edgesCapped = rawEdges.length > rowCap
  const timelineCapped = rawTimeline.length > SNAPSHOT_TIMELINE_CAP
  const filters = snapshotFilterRows(data.filters)
  const summary = snapshotSummaryRows(body.summary)

  return {
    id: data.id,
    name,
    snapshotType,
    generatedAt,
    storedNodeCount,
    storedEdgeCount,
    loadedNodeCount,
    loadedEdgeCount,
    timelineCount,
    countsMatch,
    nodes,
    edges,
    timeline,
    nodesCapped,
    edgesCapped,
    timelineCapped,
    filters,
    summary,
  }
}
