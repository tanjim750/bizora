import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { journeyPath, buildJourneyView } from '../src/lib/intelligence/graph.js'

test('journeyPath returns valid path for customer and order', () => {
  assert.equal(journeyPath(1, 'customer', 42), 'businesses/1/graph/journeys/customer/42/')
  assert.equal(journeyPath(2, 'order', '100'), 'businesses/2/graph/journeys/order/100/')
})

test('journeyPath throws on unsupported entity kinds and invalid IDs', () => {
  assert.throws(() => journeyPath(1, 'product', 1), /Journeys exist for customers and orders only\./)
  assert.throws(() => journeyPath(1, 'campaign', 1), /Journeys exist for customers and orders only\./)
  assert.throws(() => journeyPath(1, 'conversation', 1), /Journeys exist for customers and orders only\./)
  assert.throws(() => journeyPath(1, 'shipment', 1), /Journeys exist for customers and orders only\./)

  // Invalid IDs
  assert.throws(() => journeyPath(1, 'customer', 0), /id/i)
  assert.throws(() => journeyPath(1, 'customer', -5), /id/i)
  assert.throws(() => journeyPath(1, 'customer', '9223372036854775808'), /id/i)
  assert.throws(() => journeyPath(1, 'order', 'invalid-id'), /id/i)
})

test('buildJourneyView handles customer answer with headline and timeline', () => {
  const input = {
    customer_id: 12,
    canonical_identity_id: 45,
    node_count: 5,
    edge_count: 4,
    summary: 'High value repeat customer',
    timeline: [
      {
        stage: 'ACQUISITION',
        label: 'First Visit',
        entity_type: 'CUSTOMER',
        entity_id: 12,
        timestamp: '2026-01-01T00:00:00Z',
      },
      {
        // Missing stage, should fallback to entity_type
        label: 'Order Placed',
        entity_type: 'ORDER',
        entity_id: 101,
        timestamp: '2026-01-02T00:00:00Z',
      },
    ],
  }

  const result = buildJourneyView(input)
  assert.deepEqual(result.headline, [
    { label: 'Customer ID', value: 12 },
    { label: 'Canonical Identity ID', value: 45 },
    { label: 'Nodes', value: 5 },
    { label: 'Edges', value: 4 },
    { label: 'Summary', value: 'High value repeat customer' },
  ])
  assert.equal(result.timeline.length, 2)
  assert.equal(result.timeline[0].stage, 'ACQUISITION')
  assert.equal(result.timeline[0].label, 'First Visit')
  assert.equal(result.timeline[0].entityType, 'CUSTOMER')
  assert.equal(result.timeline[0].entityId, 12)
  assert.equal(result.timeline[0].timestamp, '2026-01-01T00:00:00Z')

  assert.equal(result.timeline[1].stage, 'ORDER') // fallback to entity_type
  assert.equal(result.timeline[1].label, 'Order Placed')
  assert.equal(result.timeline[1].entityType, 'ORDER')
})

test('buildJourneyView handles order answer with headline and preserves total_amount string', () => {
  const input = {
    order_id: 99,
    status: 'FULFILLED',
    total_amount: '1250.50',
    customer_node_id: 12,
    product_count: 3,
    payment_count: 1,
    shipment_count: 1,
    timeline: [
      {
        stage: 'PLACEMENT',
        label: 'Order Created',
        entity_type: 'ORDER',
        entity_id: 99,
        timestamp: '2026-02-01T12:00:00Z',
      },
    ],
  }

  const result = buildJourneyView(input)
  assert.deepEqual(result.headline, [
    { label: 'Order ID', value: 99 },
    { label: 'Status', value: 'FULFILLED' },
    { label: 'Total Amount', value: '1250.50' },
    { label: 'Customer Node ID', value: 12 },
    { label: 'Products', value: 3 },
    { label: 'Payments', value: 1 },
    { label: 'Shipments', value: 1 },
  ])
  assert.equal(typeof result.headline.find((h) => h.label === 'Total Amount').value, 'string')
  assert.equal(result.timeline.length, 1)
})

test('buildJourneyView handles missing timeline, junk input, and entries without entity_type', () => {
  assert.deepEqual(buildJourneyView(null), { headline: [], timeline: [] })
  assert.deepEqual(buildJourneyView('junk'), { headline: [], timeline: [] })
  assert.deepEqual(buildJourneyView({}), { headline: [], timeline: [] })
  assert.deepEqual(buildJourneyView({ timeline: null }), { headline: [], timeline: [] })

  const inputWithSkipped = {
    customer_id: 1,
    timeline: [
      {
        stage: 'INVALID_ENTRY',
        // entity_type missing, must be skipped
        entity_id: 1,
      },
      {
        entity_type: 'CUSTOMER',
        entity_id: 1,
        // label missing, fallback
      },
    ],
  }

  const result = buildJourneyView(inputWithSkipped)
  assert.equal(result.timeline.length, 1)
  assert.equal(result.timeline[0].stage, 'CUSTOMER')
  assert.equal(result.timeline[0].label, 'CUSTOMER #1')
})

test('Intelligence.js contains Journey timeline and imports journeyPath', () => {
  const filePath = path.join(process.cwd(), 'src/components/Intelligence.js')
  const content = fs.readFileSync(filePath, 'utf8')
  assert.ok(content.includes('journeyPath'), 'Intelligence.js must import and use journeyPath')
  assert.ok(content.includes('Journey timeline'), 'Intelligence.js must contain a "Journey timeline" section')
})
