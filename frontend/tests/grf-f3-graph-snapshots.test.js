import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import {
  SNAPSHOT_LIST_CAP,
  SNAPSHOT_ROW_CAP,
  SNAPSHOT_TIMELINE_CAP,
  SNAPSHOT_SUMMARY_CAP,
  SNAPSHOT_TYPE_LABELS,
  snapshotTypeLabel,
  snapshotListPath,
  snapshotDetailPath,
  normalizeSnapshotList,
  snapshotFilterRows,
  snapshotSummaryRows,
  normalizeSnapshotDetail,
} from '../src/lib/intelligence/graphSnapshots.js'

test('paths and constants (GRF-F3)', () => {
  assert.equal(SNAPSHOT_LIST_CAP, 50)
  assert.equal(SNAPSHOT_ROW_CAP, 100)
  assert.equal(SNAPSHOT_TIMELINE_CAP, 20)
  assert.equal(SNAPSHOT_SUMMARY_CAP, 20)
  assert.deepEqual(SNAPSHOT_TYPE_LABELS, {
    BUSINESS: 'Whole business',
    CUSTOMER: 'Customer journey',
    ORDER: 'Order journey',
    PRODUCT: 'Product journey',
    CAMPAIGN: 'Campaign journey',
  })

  assert.equal(snapshotListPath(1), 'businesses/1/graph/snapshots/')
  assert.equal(snapshotDetailPath(1, 3), 'businesses/1/graph/snapshots/3/')
  assert.equal(snapshotDetailPath(1, '12'), 'businesses/1/graph/snapshots/12/')

  assert.throws(() => snapshotDetailPath(1, 0), /Snapshot ID must be a whole number/)
  assert.throws(() => snapshotDetailPath(1, 'x'), /Snapshot ID must be a whole number/)
  assert.throws(() => snapshotDetailPath(1, '9223372036854775808'), /Snapshot ID must be a whole number/)
  assert.throws(() => snapshotListPath(0), /Invalid business ID/)
})

test('snapshotTypeLabel maps types and fallbacks (GRF-F3)', () => {
  assert.equal(snapshotTypeLabel('BUSINESS'), 'Whole business')
  assert.equal(snapshotTypeLabel('CUSTOMER'), 'Customer journey')
  assert.equal(snapshotTypeLabel('ORDER'), 'Order journey')
  assert.equal(snapshotTypeLabel('PRODUCT'), 'Product journey')
  assert.equal(snapshotTypeLabel('CAMPAIGN'), 'Campaign journey')
  assert.equal(snapshotTypeLabel('OTHER_TYPE'), 'Other type')
  assert.equal(snapshotTypeLabel(null), '—')
})

test('normalizeSnapshotList normalizes arrays and objects (GRF-F3)', () => {
  const rawList = [
    {
      id: 10,
      name: '  Snapshot A  ',
      snapshot_type: 'BUSINESS',
      node_count: 5,
      edge_count: 8,
      generated_at: '2026-11-17T09:00:00Z',
    },
    { id: 'not-int' },
    {
      id: 11,
      name: '   ',
      node_count: 'not-int',
      edge_count: null,
    },
  ]

  const norm = normalizeSnapshotList(rawList)
  assert.equal(norm.length, 2)
  assert.deepEqual(norm[0], {
    id: 10,
    name: 'Snapshot A',
    snapshotType: 'BUSINESS',
    nodeCount: 5,
    edgeCount: 8,
    generatedAt: '2026-11-17T09:00:00Z',
  })
  assert.deepEqual(norm[1], {
    id: 11,
    name: 'Untitled snapshot',
    snapshotType: null,
    nodeCount: null,
    edgeCount: null,
    generatedAt: null,
  })

  // Object with results
  const normObj = normalizeSnapshotList({ results: rawList })
  assert.equal(normObj.length, 2)

  // Junk input
  for (const j of [null, 'x', {}]) {
    assert.deepEqual(normalizeSnapshotList(j), [])
  }
})

test('snapshotFilterRows extracts whitelisted filters in strict order (GRF-F3)', () => {
  const filters = {
    entity_types: ['CUSTOMER', 'ORDER'],
    min_confidence: '0.95',
    status: 'PAID',
    dimensions: { tier: 'gold' },
    time_from: '2026-01-01T00:00:00+00:00',
    evil_key: 'x',
    channel: '',
  }

  const expected = [
    { key: 'entity_types', label: 'Entity types', value: 'CUSTOMER, ORDER' },
    { key: 'min_confidence', label: 'Minimum confidence', value: '0.95' },
    { key: 'status', label: 'Status', value: 'PAID' },
    { key: 'dimensions', label: 'Dimensions', value: '{"tier":"gold"}' },
    { key: 'time_from', label: 'From', value: '2026-01-01T00:00:00+00:00' },
  ]

  assert.deepEqual(snapshotFilterRows(filters), expected)
  for (const j of [null, 'x', []]) {
    assert.deepEqual(snapshotFilterRows(j), [])
  }
})

test('snapshotSummaryRows extracts scalar fields up to cap (GRF-F3)', () => {
  const summary = {
    type: 'FULL_BUSINESS_GRAPH',
    node_count: 3,
    edge_count: 2,
    nested: { a: 1 },
    flag: true,
    none: null,
  }

  const expected = [
    { label: 'Type', value: 'FULL_BUSINESS_GRAPH' },
    { label: 'Node count', value: '3' },
    { label: 'Edge count', value: '2' },
    { label: 'Flag', value: 'true' },
  ]

  assert.deepEqual(snapshotSummaryRows(summary), expected)

  // More than 20 entries capped at 20
  const largeSummary = {}
  for (let i = 0; i < 30; i++) {
    largeSummary[`key_${i}`] = `val_${i}`
  }
  assert.equal(snapshotSummaryRows(largeSummary).length, 20)
  assert.deepEqual(snapshotSummaryRows(null), [])
})

test('normalizeSnapshotDetail handles full contract and caps (GRF-F3)', () => {
  const sample = {
    id: 3,
    name: 'Order journey',
    snapshot_type: 'ORDER',
    node_count: 3,
    edge_count: 2,
    filters: null,
    generated_at: '2026-11-17T09:00:00+00:00',
    snapshot_data: {
      nodes: [
        { id: 1, entity_type: 'CUSTOMER', entity_id: 1, label: 'Alice' },
        {
          id: 2,
          entity_type: 'ORDER',
          entity_id: 8,
          label: '',
          properties: { secret: 'SENTINEL_PROPS' },
        },
        { id: 3, entity_type: 'PRODUCT', entity_id: 20, label: 'Shoes' },
      ],
      edges: [
        {
          id: 101,
          relationship_type: 'PLACED_ORDER',
          source_node_id: 1,
          target_node_id: 2,
          confidence: '0.9500',
          properties: { metadata: 'SENTINEL_PROPS' },
        },
        {
          id: 102,
          relationship_type: 'REFERENCES',
          source_node_id: 2,
          target_node_id: 999, // missing node
        },
      ],
      timeline: [
        {
          stage: 'PLACED',
          entity_type: 'ORDER',
          entity_id: 8,
          label: 'Order 8',
          timestamp: '2026-11-17T09:05:00Z',
          connecting_relationships: 'SENTINEL_PROPS',
        },
      ],
      summary: { status: 'PAID', node_count: 3 },
    },
  }

  const norm = normalizeSnapshotDetail(sample)
  assert.ok(norm)
  assert.equal(norm.id, 3)
  assert.equal(norm.name, 'Order journey')
  assert.equal(norm.snapshotType, 'ORDER')
  assert.equal(norm.loadedNodeCount, 3)
  assert.equal(norm.loadedEdgeCount, 2)
  assert.equal(norm.timelineCount, 1)
  assert.equal(norm.countsMatch, true)

  assert.equal(norm.nodes[1].label, 'ORDER #8')
  assert.equal(norm.edges[0].confidencePercent, 95)
  assert.equal(norm.edges[0].sourceLabel, 'Alice')
  assert.equal(norm.edges[0].targetLabel, 'ORDER #8')
  assert.equal(norm.edges[1].targetLabel, 'Node 999')

  assert.deepEqual(norm.filters, [])
  assert.deepEqual(norm.summary, [
    { label: 'Status', value: 'PAID' },
    { label: 'Node count', value: '3' },
  ])

  const jsonStr = JSON.stringify(norm)
  assert.ok(!jsonStr.includes('SENTINEL_PROPS'))

  // Test rowCap: 2
  const capped = normalizeSnapshotDetail(sample, { rowCap: 2 })
  assert.equal(capped.nodes.length, 2)
  assert.equal(capped.nodesCapped, true)
  assert.equal(capped.loadedNodeCount, 3)

  // Mismatched counts
  const mismatched = normalizeSnapshotDetail({ ...sample, node_count: 5 })
  assert.equal(mismatched.countsMatch, false)
  assert.equal(mismatched.storedNodeCount, 5)

  // Junk input
  for (const j of [null, {}, { id: 'x' }]) {
    assert.equal(normalizeSnapshotDetail(j), null)
  }

  // Id only
  const minimal = normalizeSnapshotDetail({ id: 1 })
  assert.equal(minimal.countsMatch, true)
  assert.equal(minimal.nodes.length, 0)
  assert.equal(minimal.edges.length, 0)
})

test('source checks: graphSnapshots.js, GraphSnapshots.js, and GraphExplorerPanel.js (GRF-F3)', () => {
  const libFile = path.resolve('src/lib/intelligence/graphSnapshots.js')
  const compFile = path.resolve('src/components/GraphSnapshots.js')
  const panelFile = path.resolve('src/components/GraphExplorerPanel.js')

  const libCode = fs.readFileSync(libFile, 'utf8')
  assert.ok(!libCode.includes('@/'))
  assert.ok(!libCode.includes('window'))
  assert.ok(!libCode.includes('fetch'))

  const importStatements = libCode.match(/import\s+[\s\S]*?from\s+['"][^'"]+['"]/g) || []
  assert.equal(importStatements.length, 4, 'Must have exactly four import statements')
  assert.ok(libCode.includes("from '../catalog.js'"))
  assert.ok(libCode.includes("from '../format/text.js'"))
  assert.ok(libCode.includes("from './graphExplore.js'"))
  assert.ok(libCode.includes("from './facts.js'"))

  assert.ok(fs.existsSync(compFile), 'GraphSnapshots.js must exist')
  const compCode = fs.readFileSync(compFile, 'utf8')
  assert.ok(compCode.startsWith("'use client'"))
  assert.ok(compCode.includes("from '@/lib/intelligence/graphSnapshots'"))
  assert.ok(compCode.includes("from '@/lib/clientApi'"))
  assert.ok(compCode.includes("from '@/components/ui'"))

  assert.ok(compCode.includes('isOpen='))
  assert.ok(!/\bopen=\{/.test(compCode))

  const requiredCodeTokens = [
    'snapshotListPath(',
    'snapshotDetailPath(',
    'normalizeSnapshotList(',
    'normalizeSnapshotDetail(',
    'useCallback',
  ]
  for (const tok of requiredCodeTokens) {
    assert.ok(compCode.includes(tok), `Must contain ${tok}`)
  }

  const requiredPhrases = [
    'Saved snapshots',
    'No snapshots yet',
    'Snapshots could not be loaded',
    'The snapshot could not be opened',
    'This is a stored copy',
    'Filters used when it was saved',
    'No filters were applied.',
    'Showing the newest 50',
    'Try again',
    'Refresh',
    'aria-live="polite"',
  ]
  for (const phrase of requiredPhrases) {
    assert.ok(compCode.includes(phrase), `Must contain phrase "${phrase}"`)
  }

  const strippedCode = compCode.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  assert.ok(!strippedCode.includes('JSON.stringify'))
  assert.ok(!strippedCode.includes('snapshot_data'))
  assert.ok(!strippedCode.includes('dangerouslySetInnerHTML'))
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(strippedCode))
  assert.ok(!/<Banner[^>]*\btone=/.test(strippedCode))

  const forbiddenClasses = ['text-caption', 'text-muted', 'text-secondary', 'stack-xs', 'stack-md']
  for (const cls of forbiddenClasses) {
    const classRegex = new RegExp(`className=["'][^"']*\\b${cls}\\b[^"']*["']`)
    assert.ok(!classRegex.test(strippedCode), `Must not contain forbidden class ${cls}`)
  }

  const panelCode = fs.readFileSync(panelFile, 'utf8')
  assert.ok(panelCode.includes('GraphSnapshots'))
  assert.ok(panelCode.includes("id: 'snapshots'"))
  assert.ok(panelCode.includes("view === 'snapshots'"))
  assert.ok(panelCode.includes('GraphPathFinder'))
})
