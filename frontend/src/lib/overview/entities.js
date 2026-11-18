import { businessApiPath } from '../catalog.js'
import { enumLabel, stripUntrusted } from '../format/text.js'

export const OVERVIEW_ENTITY_TYPES = Object.freeze([
  'order',
  'customer',
  'product',
  'product_variant',
  'payment',
  'refund',
  'campaign',
  'conversation',
  'shipment',
  'call',
  'website_session',
  'website_visitor',
])

export function overviewEntityKey(rawType) {
  if (typeof rawType !== 'string') return null
  const trimmed = rawType.trim()
  if (!trimmed || trimmed.includes('/') || /[^a-zA-Z0-9_\s-]/.test(trimmed)) return null

  let s = trimmed
  if (/[a-z]/.test(trimmed) && /[A-Z]/.test(trimmed)) {
    s = trimmed.replace(/([a-z0-9])([A-Z])/g, '$1_$2')
  }
  s = s.replace(/[\s-]+/g, '_').toLowerCase()

  return OVERVIEW_ENTITY_TYPES.includes(s) ? s : null
}

export function overviewEntityRef(rawType, rawId) {
  const type = overviewEntityKey(rawType)
  if (!type) return null

  let idStr = null
  if (typeof rawId === 'number') {
    if (!Number.isInteger(rawId) || rawId < 1 || rawId > Number.MAX_SAFE_INTEGER) return null
    idStr = String(rawId)
  } else if (typeof rawId === 'string') {
    const trimmed = rawId.trim()
    if (!/^\d+$/.test(trimmed)) return null
    try {
      const bi = BigInt(trimmed)
      if (bi < 1n || bi > 9223372036854775807n) return null
      idStr = bi.toString()
    } catch {
      return null
    }
  } else {
    return null
  }

  return { type, id: idStr }
}

export function overviewEntityPath(businessId, type, id) {
  if (!OVERVIEW_ENTITY_TYPES.includes(type)) {
    throw new Error(`Unsupported entity type: ${type}`)
  }

  let idStr = null
  if (typeof id === 'number') {
    if (Number.isInteger(id) && id >= 1 && id <= Number.MAX_SAFE_INTEGER) {
      idStr = String(id)
    }
  } else if (typeof id === 'string') {
    const trimmed = id.trim()
    if (/^\d+$/.test(trimmed)) {
      try {
        const bi = BigInt(trimmed)
        if (bi >= 1n && bi <= 9223372036854775807n) {
          idStr = bi.toString()
        }
      } catch {}
    }
  }

  if (!idStr) {
    throw new Error('Invalid entity ID')
  }

  return businessApiPath(businessId, `overview/entities/${type}/${idStr}/`)
}

export function overviewEntityTypeLabel(type) {
  return enumLabel(type)
}

export function normalizeOverviewEntity(data) {
  if (!data || typeof data !== 'object') return null
  if (data.available !== true) return null
  if (typeof data.type !== 'string' || typeof data.id !== 'number' || !Number.isInteger(data.id)) {
    return null
  }

  const domain = typeof data.domain === 'string' ? data.domain : null
  const status = typeof data.status === 'string' ? data.status : null

  let label = null
  if (typeof data.label === 'string') {
    const stripped = stripUntrusted(data.label).trim()
    if (stripped.length > 0) label = stripped
  }

  const updatedAt = typeof data.updated_at === 'string' ? data.updated_at : null
  const asOf = typeof data.as_of === 'string' ? data.as_of : null

  const nodes = []
  if (data.graph && Array.isArray(data.graph.nodes)) {
    for (const node of data.graph.nodes) {
      if (node && typeof node.id === 'number' && Number.isInteger(node.id)) {
        let nodeLabel = ''
        if (typeof node.label === 'string') {
          nodeLabel = stripUntrusted(node.label).trim()
        }
        if (!nodeLabel) {
          nodeLabel = `Node ${node.id}`
        }
        nodes.push({
          id: node.id,
          label: nodeLabel,
          entityType: typeof node.entity?.type === 'string' ? node.entity.type : null,
          entityId:
            typeof node.entity?.id === 'number' && Number.isInteger(node.entity.id) ? node.entity.id : null,
          entityAvailable: node.entity?.available === true,
        })
      }
    }
  }

  const edges = []
  if (data.graph && Array.isArray(data.graph.edges)) {
    for (const edge of data.graph.edges) {
      if (edge && typeof edge.id === 'number' && Number.isInteger(edge.id)) {
        edges.push({
          id: edge.id,
          relationshipType: typeof edge.relationship_type === 'string' ? edge.relationship_type : 'Unknown',
          sourceNodeId:
            typeof edge.source_node_id === 'number' && Number.isInteger(edge.source_node_id)
              ? edge.source_node_id
              : null,
          targetNodeId:
            typeof edge.target_node_id === 'number' && Number.isInteger(edge.target_node_id)
              ? edge.target_node_id
              : null,
        })
      }
    }
  }

  return {
    type: data.type,
    id: data.id,
    domain,
    label,
    status,
    updatedAt,
    asOf,
    graph: { nodes, edges },
  }
}

export function overviewEntityError(error) {
  if (!error) return 'The record could not be loaded.'
  if (error.status === 404) {
    return 'This record is not available in the overview. It may be of a type the overview does not cover, or it may have been removed.'
  }
  if (error.status === 403) {
    return 'You do not have access to this business.'
  }
  if (typeof error.detail === 'string' && error.detail.trim() !== '') {
    return error.detail
  }
  if (typeof error.message === 'string' && error.message.trim() !== '') {
    return error.message
  }
  return 'The record could not be loaded.'
}
