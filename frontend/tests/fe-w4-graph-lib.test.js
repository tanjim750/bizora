import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  ENTITY_KINDS,
  REBUILD_BODY,
  traversalPath,
  buildGraphView,
  graphErrorKind,
} from '../src/lib/intelligence/graph.js'

test('ENTITY_KINDS and REBUILD_BODY constants are defined correctly', () => {
  assert.deepEqual(ENTITY_KINDS, {
    customer: 'CUSTOMER',
    order: 'ORDER',
    product: 'PRODUCT',
    conversation: 'CONVERSATION',
    shipment: 'SHIPMENT',
  })
  assert.deepEqual(REBUILD_BODY, { clean: false })
})

test('traversalPath builds valid URL for every entity kind', () => {
  for (const [kind, backendType] of Object.entries(ENTITY_KINDS)) {
    const url = traversalPath(1, kind, 42)
    assert.equal(
      url,
      `businesses/1/graph/traversal/?root_entity_type=${backendType}&root_entity_id=42&direction=BIDIRECTIONAL&max_depth=2&max_nodes=100`,
    )
  }
})

test('traversalPath throws on invalid inputs', () => {
  // id 0, negative, text id, out of range
  assert.throws(() => traversalPath(1, 'customer', 0), /id/i)
  assert.throws(() => traversalPath(1, 'customer', '9223372036854775808'), /id/i)
  assert.throws(() => traversalPath(1, 'customer', 'abc'), /id/i)

  // unknown kind
  assert.throws(() => traversalPath(1, 'unknown', 1), /kind/i)

  // bad direction
  assert.throws(() => traversalPath(1, 'customer', 1, { direction: 'SIDEWAYS' }), /direction/i)

  // depth out of range
  assert.throws(() => traversalPath(1, 'customer', 1, { maxDepth: 6 }), /depth/i)
  assert.throws(() => traversalPath(1, 'customer', 1, { maxDepth: -1 }), /depth/i)

  // nodes out of range
  assert.throws(() => traversalPath(1, 'customer', 1, { maxNodes: 0 }), /nodes/i)
  assert.throws(() => traversalPath(1, 'customer', 1, { maxNodes: 1001 }), /nodes/i)
})

test('buildGraphView handles normal answer, dangling edge pruning, empty labels, and missing arrays', () => {
  // Missing arrays
  assert.deepEqual(buildGraphView(null), { nodes: [], edges: [], truncated: false, hiddenEdges: 0 })
  assert.deepEqual(buildGraphView({}), { nodes: [], edges: [], truncated: false, hiddenEdges: 0 })

  // Normal + dangling edge
  const input = {
    nodes: [
      { id: 1, entity_type: 'CUSTOMER', entity_id: 10, label: 'Alice', properties: {} },
      { id: 2, entity_type: 'ORDER', entity_id: 20, label: '', properties: {} },
    ],
    edges: [
      { id: 101, source_node_id: 1, target_node_id: 2, relationship_type: 'PLACED_ORDER', confidence: 1 },
      { id: 102, source_node_id: 1, target_node_id: 999, relationship_type: 'VIEWED', confidence: 0.8 },
    ],
    truncated: true,
  }

  const view = buildGraphView(input)
  assert.equal(view.truncated, true)
  assert.equal(view.hiddenEdges, 1) // edge 102 target 999 is missing
  assert.equal(view.edges.length, 1)

  const keptEdge = view.edges[0]
  assert.equal(keptEdge.id, 101)
  assert.equal(keptEdge.sourceLabel, 'Alice')
  assert.equal(keptEdge.targetLabel, 'ORDER #20') // fallback when label is empty
})

test('graphErrorKind classifies error kinds', () => {
  assert.equal(graphErrorKind({ code: 'GRAPH_NOT_BUILT' }), 'not_built')
  assert.equal(graphErrorKind({ status: 409, code: 'GRAPH_NOT_BUILT' }), 'not_built')
  assert.equal(graphErrorKind({ status: 404 }), 'not_found')
  assert.equal(graphErrorKind({ status: 400 }), 'invalid')
  assert.equal(graphErrorKind({ status: 500 }), 'other')
  assert.equal(graphErrorKind(null), 'other')
})

test('Intelligence.js imports from @/lib/intelligence/graph and removes graph-context', () => {
  const filePath = path.join(process.cwd(), 'src/components/Intelligence.js')
  const content = fs.readFileSync(filePath, 'utf8')
  assert.ok(
    content.includes('@/lib/intelligence/graph'),
    'Intelligence.js must import from @/lib/intelligence/graph',
  )
  assert.ok(!content.includes('graph-context/'), 'Intelligence.js must no longer contain graph-context/')
})
