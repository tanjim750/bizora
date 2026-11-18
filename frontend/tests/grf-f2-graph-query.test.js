import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import {
  QUERY_LIMIT_DEFAULT,
  QUERY_LIMIT_MAX,
  QUERY_ROW_CAP,
  graphQueryPath,
  describeGraphQuery,
  normalizeGraphQuery,
} from '../src/lib/intelligence/graphQuery.js'

test('constants: limits and caps (GRF-F2)', () => {
  assert.equal(QUERY_LIMIT_DEFAULT, 100)
  assert.equal(QUERY_LIMIT_MAX, 1000)
  assert.equal(QUERY_ROW_CAP, 200)
})

test('graphQueryPath constructs valid URLs and enforces query grammar (GRF-F2)', () => {
  assert.equal(graphQueryPath(1), 'businesses/1/graph/query/?limit=100')
  assert.equal(
    graphQueryPath(1, { entityType: 'CUSTOMER', entityId: 5 }),
    'businesses/1/graph/query/?entity_type=CUSTOMER&entity_id=5&limit=100',
  )
  assert.equal(
    graphQueryPath(1, {
      entityType: 'ORDER',
      entityId: '8',
      relationshipType: 'HAS_PAYMENT',
      limit: 50,
      minConfidence: 0.5,
    }),
    'businesses/1/graph/query/?entity_type=ORDER&entity_id=8&relationship_type=HAS_PAYMENT&limit=50&min_confidence=0.5',
  )
  assert.equal(
    graphQueryPath(1, { relationshipType: 'PLACED_ORDER', limit: 1000 }),
    'businesses/1/graph/query/?relationship_type=PLACED_ORDER&limit=1000',
  )

  // Blank values count as not given
  assert.equal(
    graphQueryPath(1, { entityType: '', entityId: '  ', limit: 100 }),
    'businesses/1/graph/query/?limit=100',
  )

  // Disallowed query parameters
  const url = graphQueryPath(1, { entityType: 'CUSTOMER', entityId: 5 })
  assert.ok(!url.includes('root_entity'))
  assert.ok(!url.includes('max_depth'))

  // Throws
  assert.throws(
    () => graphQueryPath(1, { entityType: 'CUSTOMER' }),
    /Choose an entity type and an entity ID together, or leave both empty\./,
  )
  assert.throws(
    () => graphQueryPath(1, { entityId: 5 }),
    /Choose an entity type and an entity ID together, or leave both empty\./,
  )
  assert.throws(
    () => graphQueryPath(1, { entityType: 'customer', entityId: 5 }),
    /Invalid entity type: customer/,
  )
  assert.throws(() => graphQueryPath(1, { entityType: 'CUSTOMER', entityId: 0 }), /Entity ID/)
  assert.throws(() => graphQueryPath(1, { entityType: 'CUSTOMER', entityId: 'x' }), /Entity ID/)
  assert.throws(() => graphQueryPath(1, { relationshipType: 'placed_order' }), /Invalid relationship type/)
  for (const lim of [0, 1001, 2.5, '100', NaN]) {
    assert.throws(
      () => graphQueryPath(1, { limit: lim }),
      /Limit must be a whole number between 1 and 1000\./,
    )
  }
  assert.throws(() => graphQueryPath(0), /Invalid business ID/)
  assert.throws(() => graphQueryPath(1, { minConfidence: 2 }), /between 0 and 1/)
})

test('describeGraphQuery explains the search honestly (GRF-F2)', () => {
  assert.equal(
    describeGraphQuery({ entityType: 'CUSTOMER', entityId: '5', limit: 100 }),
    'Everything within 2 hops of Customer 5, in both directions, up to 100 nodes.',
  )
  assert.equal(
    describeGraphQuery({
      entityType: 'CUSTOMER',
      entityId: '5',
      limit: 100,
      relationshipType: 'PLACED_ORDER',
      minConfidence: '0.5',
    }),
    'Everything within 2 hops of Customer 5, in both directions, up to 100 nodes, following only PLACED_ORDER relationships, ignoring relationships below 0.5 confidence.',
  )
  assert.equal(
    describeGraphQuery({ limit: 50 }),
    'Up to 50 relationships in this business, with the entities they connect.',
  )
  assert.equal(
    describeGraphQuery({
      relationshipType: 'HAS_PAYMENT',
      limit: 50,
      minConfidence: '0.9',
    }),
    'Up to 50 relationships of type HAS_PAYMENT in this business, with the entities they connect, ignoring relationships below 0.9 confidence.',
  )
  assert.equal(
    describeGraphQuery({}),
    'Up to 100 relationships in this business, with the entities they connect.',
  )
})

test('normalizeGraphQuery maps nodes and edges and discards properties (GRF-F2)', () => {
  const raw = {
    business_id: 1,
    root_node_id: 0,
    depth_reached: 1,
    truncated: true,
    node_count: 2,
    edge_count: 1,
    nodes: [
      {
        id: 11,
        entity_type: 'CUSTOMER',
        entity_id: 5,
        label: 'Rina Das',
        properties: { status: 'X' },
      },
      { id: 12, entity_type: 'ORDER', entity_id: 8, label: '', properties: {} },
    ],
    edges: [
      {
        id: 21,
        source_node_id: 11,
        target_node_id: 12,
        relationship_type: 'PLACED_ORDER',
        confidence: '0.9500',
      },
      {
        id: 22,
        source_node_id: 11,
        target_node_id: 999,
        relationship_type: 'HAS_CALL',
        confidence: '1.0000',
      },
    ],
  }

  const norm = normalizeGraphQuery(raw)
  assert.deepEqual(norm, {
    nodes: [
      { id: 11, entityType: 'CUSTOMER', entityId: 5, label: 'Rina Das' },
      { id: 12, entityType: 'ORDER', entityId: 8, label: 'ORDER #8' },
    ],
    edges: [
      {
        id: 21,
        relationshipType: 'PLACED_ORDER',
        sourceLabel: 'Rina Das',
        targetLabel: 'ORDER #8',
        confidencePercent: 95,
      },
    ],
    truncated: true,
    hiddenEdges: 1,
    nodeCount: 2,
    edgeCount: 1,
    depthReached: 1,
    rootNodeId: null,
  })

  // root_node_id > 0
  const withRoot = normalizeGraphQuery({ ...raw, root_node_id: 11 })
  assert.equal(withRoot.rootNodeId, 11)

  // no properties in any node
  for (const n of norm.nodes) {
    assert.equal('properties' in n, false)
  }

  // Junk input
  const emptyShape = {
    nodes: [],
    edges: [],
    truncated: false,
    hiddenEdges: 0,
    nodeCount: 0,
    edgeCount: 0,
    depthReached: null,
    rootNodeId: null,
  }
  for (const j of [null, 'x', {}]) {
    assert.deepEqual(normalizeGraphQuery(j), emptyShape)
  }
})

test('source checks: graphQuery.js, GraphQueryForm.js, and GraphExplorerPanel.js (GRF-F2)', () => {
  const libFile = path.resolve('src/lib/intelligence/graphQuery.js')
  const formFile = path.resolve('src/components/GraphQueryForm.js')
  const panelFile = path.resolve('src/components/GraphExplorerPanel.js')

  const libCode = fs.readFileSync(libFile, 'utf8')
  assert.ok(!libCode.includes('@/'))
  assert.ok(!libCode.includes('window'))
  assert.ok(!libCode.includes('fetch'))

  const importStatements = libCode.match(/import\s+[\s\S]*?from\s+['"][^'"]+['"]/g) || []
  assert.equal(importStatements.length, 5, 'graphQuery.js must have exactly five import statements')
  assert.ok(libCode.includes("from '../catalog.js'"))
  assert.ok(libCode.includes("from '../format/text.js'"))
  assert.ok(libCode.includes("from './graphExplore.js'"))
  assert.ok(libCode.includes("from './graph.js'"))
  assert.ok(libCode.includes("from './facts.js'"))

  assert.ok(fs.existsSync(formFile), 'GraphQueryForm.js must exist')
  const formCode = fs.readFileSync(formFile, 'utf8')
  assert.ok(formCode.startsWith("'use client'"), "Must start with 'use client'")
  assert.ok(formCode.includes("from '@/lib/intelligence/graphQuery'"))
  assert.ok(formCode.includes("from '@/lib/intelligence/graphExplore'"))
  assert.ok(formCode.includes("from '@/lib/clientApi'"))
  assert.ok(formCode.includes("from '@/components/ui'"))

  const requiredCodeTokens = [
    'graphQueryPath(',
    'normalizeGraphQuery(',
    'describeGraphQuery(',
    'graphErrorMessage(',
  ]
  for (const tok of requiredCodeTokens) {
    assert.ok(formCode.includes(tok), `GraphQueryForm must include ${tok}`)
  }

  const requiredPhrases = [
    'Query the graph',
    'Entity type',
    'Entity ID',
    'Relationship type',
    'Limit',
    'Minimum confidence',
    'Run query',
    'The query did not run',
    'The query failed',
    'Nothing matched',
    'Choose what to look for and select Run query.',
    'Any entity (list relationships)',
    'Any relationship',
    'aria-live="polite"',
  ]
  for (const phrase of requiredPhrases) {
    assert.ok(formCode.includes(phrase), `GraphQueryForm must include "${phrase}"`)
  }

  const strippedCode = formCode.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(strippedCode), 'No raw hex color allowed')
  assert.ok(!strippedCode.includes('dangerouslySetInnerHTML'))
  assert.ok(!strippedCode.includes('window.confirm'))
  assert.ok(!/<Banner[^>]*\btone=/.test(strippedCode))

  const forbiddenClasses = ['text-caption', 'text-muted', 'text-secondary', 'stack-xs', 'stack-md']
  for (const cls of forbiddenClasses) {
    const classRegex = new RegExp(`className=["'][^"']*\\b${cls}\\b[^"']*["']`)
    assert.ok(!classRegex.test(strippedCode), `Must not contain forbidden class ${cls}`)
  }

  const panelCode = fs.readFileSync(panelFile, 'utf8')
  assert.ok(panelCode.includes('GraphQueryForm'))
  assert.ok(panelCode.includes("id: 'query'"))
  assert.ok(panelCode.includes("view === 'query'"))
  assert.ok(panelCode.includes('GraphPathFinder'))
  assert.ok(panelCode.includes('Explore the graph'))
})
