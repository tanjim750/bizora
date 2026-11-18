import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  OVERVIEW_ENTITY_TYPES,
  overviewEntityKey,
  overviewEntityRef,
  overviewEntityPath,
  overviewEntityTypeLabel,
  normalizeOverviewEntity,
  overviewEntityError,
} from '../src/lib/overview/entities.js'

test('OVERVIEW_ENTITY_TYPES contains exact 12 types in order (OVW-F1)', () => {
  const expected = [
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
  ]
  assert.deepEqual(OVERVIEW_ENTITY_TYPES, expected)
  assert.ok(Object.isFrozen(OVERVIEW_ENTITY_TYPES))
})

test('overviewEntityKey normalizes case, separators, and rejects invalid types (OVW-F1)', () => {
  const pairs = [
    ['Order', 'order'],
    ['ORDER', 'order'],
    ['order', 'order'],
    ['Customer', 'customer'],
    ['Product', 'product'],
    ['ProductVariant', 'product_variant'],
    ['PRODUCT_VARIANT', 'product_variant'],
    ['product variant', 'product_variant'],
    ['Payment', 'payment'],
    ['Refund', 'refund'],
    ['Campaign', 'campaign'],
    ['Conversation', 'conversation'],
    ['Shipment', 'shipment'],
    ['Call', 'call'],
    ['WebsiteSession', 'website_session'],
    ['WebsiteVisitor', 'website_visitor'],
    [' Customer ', 'customer'],
  ]
  for (const [input, expected] of pairs) {
    assert.equal(overviewEntityKey(input), expected, `Failed for input: ${input}`)
  }

  const invalidInputs = [
    'Callback',
    'CallbackRequest',
    'Message',
    'IDENTITY',
    'PRODUCTVARIANT',
    'Order/1',
    '',
    null,
    5,
    undefined,
  ]
  for (const input of invalidInputs) {
    assert.equal(overviewEntityKey(input), null, `Expected null for: ${input}`)
  }
})

test('overviewEntityRef builds valid entity references and rejects invalid IDs (OVW-F1)', () => {
  assert.deepEqual(overviewEntityRef('Order', 8), { type: 'order', id: '8' })
  assert.deepEqual(overviewEntityRef('ORDER', '8'), { type: 'order', id: '8' })
  assert.deepEqual(overviewEntityRef('ProductVariant', ' 12 '), { type: 'product_variant', id: '12' })

  // Invalid IDs
  assert.equal(overviewEntityRef('Order', 0), null)
  assert.equal(overviewEntityRef('Order', null), null)
  assert.equal(overviewEntityRef('Message', 5), null)
  assert.equal(overviewEntityRef('Order', 'abc'), null)
  assert.equal(overviewEntityRef('Order', '9223372036854775808'), null)
  assert.equal(overviewEntityRef('Order', 1.5), null)
  assert.equal(overviewEntityRef('Order', true), null)
})

test('overviewEntityPath builds valid path and validates parameters (OVW-F1)', () => {
  assert.equal(overviewEntityPath(1, 'order', '8'), 'businesses/1/overview/entities/order/8/')
  assert.equal(
    overviewEntityPath(1, 'product_variant', 3),
    'businesses/1/overview/entities/product_variant/3/',
  )

  assert.throws(() => overviewEntityPath(1, 'Order', 8), /Unsupported entity type/)
  assert.throws(() => overviewEntityPath(1, 'message', 8), /Unsupported entity type/)
  assert.throws(() => overviewEntityPath(1, 'order', 0), /Invalid entity ID/)
  assert.throws(() => overviewEntityPath(1, 'order', 'x'), /Invalid entity ID/)
  assert.throws(() => overviewEntityPath(0, 'order', 8), /Invalid business ID/)

  assert.equal(overviewEntityTypeLabel('product_variant'), 'Product variant')
})

test('normalizeOverviewEntity normalizes full example and discards extra fields (OVW-F1)', () => {
  const backendData = {
    type: 'order',
    id: 8,
    domain: 'sales',
    available: true,
    label: 'ORD-1001',
    status: 'PAID',
    updated_at: '2026-11-17T09:00:00+00:00',
    drilldown: '/api/businesses/1/overview/entities/order/8/',
    graph: {
      nodes: [
        {
          kind: 'nodes',
          id: 31,
          drilldown: '/x',
          label: 'ORD-1001',
          entity: { type: 'order', id: 8, domain: 'sales', available: true, label: 'ORD-1001' },
        },
        {
          kind: 'nodes',
          id: 32,
          label: '',
          entity: { type: 'customer', id: 5, available: false, label: null },
        },
      ],
      edges: [
        {
          kind: 'edges',
          id: 41,
          drilldown: '/y',
          relationship_type: 'PLACED_ORDER',
          source_node_id: 30,
          target_node_id: 31,
          business_relationship_id: 9,
        },
      ],
    },
    as_of: '2026-11-17T10:00:00+00:00',
  }

  const expected = {
    type: 'order',
    id: 8,
    domain: 'sales',
    label: 'ORD-1001',
    status: 'PAID',
    updatedAt: '2026-11-17T09:00:00+00:00',
    asOf: '2026-11-17T10:00:00+00:00',
    graph: {
      nodes: [
        { id: 31, label: 'ORD-1001', entityType: 'order', entityId: 8, entityAvailable: true },
        { id: 32, label: 'Node 32', entityType: 'customer', entityId: 5, entityAvailable: false },
      ],
      edges: [{ id: 41, relationshipType: 'PLACED_ORDER', sourceNodeId: 30, targetNodeId: 31 }],
    },
  }

  const normalized = normalizeOverviewEntity(backendData)
  assert.deepEqual(normalized, expected)

  const serialized = JSON.stringify(normalized)
  assert.ok(!serialized.includes('drilldown'))
  assert.ok(!serialized.includes('/api/'))

  // Untrusted wrapper strip
  const untrusted = normalizeOverviewEntity({
    type: 'customer',
    id: 1,
    available: true,
    label: '<untrusted_customer_data>Hello</untrusted_customer_data>',
  })
  assert.equal(untrusted.label, 'Hello')

  // Label null
  const nullLabel = normalizeOverviewEntity({
    type: 'customer',
    id: 1,
    available: true,
    label: null,
  })
  assert.equal(nullLabel.label, null)

  // Missing graph
  const noGraph = normalizeOverviewEntity({
    type: 'order',
    id: 2,
    available: true,
  })
  assert.deepEqual(noGraph.graph, { nodes: [], edges: [] })

  // Invalid cases
  assert.equal(normalizeOverviewEntity({ available: false, type: 'order', id: 1 }), null)
  assert.equal(normalizeOverviewEntity(null), null)
  assert.equal(normalizeOverviewEntity({}), null)
  assert.equal(normalizeOverviewEntity({ available: true }), null)
  assert.equal(normalizeOverviewEntity('x'), null)
})

test('overviewEntityError maps error shapes (OVW-F1)', () => {
  assert.equal(
    overviewEntityError({ status: 404 }),
    'This record is not available in the overview. It may be of a type the overview does not cover, or it may have been removed.',
  )
  assert.equal(overviewEntityError({ status: 403 }), 'You do not have access to this business.')
  assert.equal(overviewEntityError({ status: 400, detail: 'Bad' }), 'Bad')
  assert.equal(overviewEntityError(new Error('boom')), 'boom')
  assert.equal(overviewEntityError(null), 'The record could not be loaded.')
})

test('source checks: entities.js (OVW-F1)', () => {
  const code = fs.readFileSync(path.join(process.cwd(), 'src/lib/overview/entities.js'), 'utf8')
  assert.ok(!code.includes('@/'), 'entities.js must not import via @/')
  assert.ok(!code.includes('window'), 'entities.js must not reference window')
  assert.ok(!code.includes('fetch'), 'entities.js must not reference fetch')

  const importMatches = code.match(/import\s+[\s\S]*?from\s+['"][^'"]+['"]/g) || []
  assert.equal(importMatches.length, 2, 'entities.js must have exactly two import statements')
})

test('source checks: OverviewEntityDrawer.js (OVW-F1)', () => {
  const filePath = path.join(process.cwd(), 'src/components/OverviewEntityDrawer.js')
  assert.ok(fs.existsSync(filePath), 'OverviewEntityDrawer.js must exist')
  const code = fs.readFileSync(filePath, 'utf8')

  assert.ok(code.trim().startsWith("'use client'"), "Must start with 'use client'")
  assert.ok(code.includes('@/lib/overview/entities'), 'Must import from entities lib')
  assert.ok(code.includes('@/lib/clientApi'), 'Must import clientApi')
  assert.ok(code.includes('@/components/ui'), 'Must import from ui kit')

  assert.ok(code.includes('isOpen='), 'Must pass isOpen= to Drawer')
  assert.ok(code.includes('useCallback'), 'Must use useCallback for handleClose')
  assert.ok(code.includes('overviewEntityPath('), 'Must call overviewEntityPath')
  assert.ok(code.includes('normalizeOverviewEntity('), 'Must call normalizeOverviewEntity')
  assert.ok(code.includes('entity?.type'), 'Must check entity?.type')
  assert.ok(code.includes('entity?.id'), 'Must check entity?.id')

  const requiredTexts = [
    'details',
    'Record details',
    'Where it sits in the business graph',
    'The record could not be opened',
    'Loading record...',
    'Try again',
    'No stored relationships touch this record.',
    'This record has no node in the business graph',
    "Only this record's own nodes are listed",
    '(this record)',
    'aria-live="polite"',
  ]
  for (const text of requiredTexts) {
    assert.ok(code.includes(text), `Must contain text: ${text}`)
  }

  assert.ok(!code.includes('drilldown'), 'Must not contain drilldown')
  assert.ok(!code.includes('dangerouslySetInnerHTML'), 'Must not contain dangerouslySetInnerHTML')
  assert.ok(!code.includes('localStorage'), 'Must not contain localStorage')

  assert.ok(!/\bopen=\{/.test(code), 'Must not use open={')
  assert.ok(!/<Banner[^>]*\btone=/.test(code), 'Banner must not use tone=')
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(code), 'Must have no raw hex colors')

  const forbiddenClasses = ['text-caption', 'text-muted', 'text-secondary', 'stack-xs', 'stack-md']
  for (const cls of forbiddenClasses) {
    const rx = new RegExp('className=["\'][^"\']*\\b' + cls + '\\b[^"\']*["\']')
    assert.ok(!rx.test(code), `Must not use forbidden class: ${cls}`)
  }
})

test('source checks: Overview.js integration (OVW-F1)', () => {
  const code = fs.readFileSync(path.join(process.cwd(), 'src/components/Overview.js'), 'utf8')
  assert.ok(code.includes('OverviewEntityDrawer'), 'Overview.js must mount OverviewEntityDrawer')
  assert.ok(code.includes('overviewEntityRef'), 'Overview.js must import overviewEntityRef')
  assert.ok(code.includes('overviewEntityTypeLabel'), 'Overview.js must import overviewEntityTypeLabel')
  assert.ok(code.includes('setOpenEntity'), 'Overview.js must use setOpenEntity')
  assert.ok(code.includes('renderEntityButton'), 'Overview.js must define renderEntityButton')
  assert.ok(code.includes('entity_details'), 'auditColumns must include entity_details')
  assert.ok(code.includes('subject_details'), 'issueColumns must include subject_details')
  assert.ok(code.includes('Open details for'), 'Button must have aria-label with Open details for')

  // Keep existing invariants
  assert.ok(code.includes('unavailableOwner="Overview & Monitoring"'), 'Must retain unavailableOwner')
  assert.ok(code.includes('SIMULATED'), 'Must retain SIMULATED')
  assert.ok(code.includes("activeTab === 'health'"), 'Must retain activeTab === health')
})
