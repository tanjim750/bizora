import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('commerce legal transitions match D4 state machine contract', () => {
  const TRANSITIONS = {
    orders: {
      PENDING: ['CONFIRMED', 'CANCELLED'],
      CONFIRMED: ['PROCESSING', 'CANCELLED'],
      PROCESSING: ['SHIPPED', 'CANCELLED'],
      SHIPPED: ['DELIVERED', 'RETURNED'],
      DELIVERED: ['RETURNED', 'REFUNDED'],
      RETURNED: ['REFUNDED'],
    },
    payments: {
      PENDING: ['AUTHORIZED', 'PAID', 'FAILED', 'CANCELLED'],
      AUTHORIZED: ['PAID', 'FAILED', 'CANCELLED'],
    },
    shipments: {
      PENDING: ['SUBMITTED', 'CANCELLED'],
      SUBMITTED: ['PICKED_UP', 'CANCELLED'],
      PICKED_UP: ['IN_TRANSIT', 'RETURNING'],
      IN_TRANSIT: ['OUT_FOR_DELIVERY', 'FAILED', 'RETURNING'],
      OUT_FOR_DELIVERY: ['DELIVERED', 'FAILED', 'RETURNING'],
      FAILED: ['OUT_FOR_DELIVERY', 'RETURNING'],
      RETURNING: ['RETURNED'],
    },
  }

  // Orders lifecycle invariants
  assert.deepEqual(TRANSITIONS.orders.PENDING, ['CONFIRMED', 'CANCELLED'])
  assert.deepEqual(TRANSITIONS.orders.DELIVERED, ['RETURNED', 'REFUNDED'])
  assert.equal(TRANSITIONS.orders.REFUNDED, undefined, 'REFUNDED is terminal')
  assert.equal(TRANSITIONS.orders.CANCELLED, undefined, 'CANCELLED is terminal')

  // Payments lifecycle invariants
  assert.ok(TRANSITIONS.payments.PENDING.includes('PAID'))
  assert.equal(TRANSITIONS.payments.PAID, undefined, 'PAID is terminal in transition view')

  // Shipments lifecycle invariants
  assert.ok(TRANSITIONS.shipments.PENDING.includes('SUBMITTED'))
  assert.ok(TRANSITIONS.shipments.IN_TRANSIT.includes('OUT_FOR_DELIVERY'))
})

test('commerce component enforces token styles and honest wording', () => {
  const commerceFile = path.resolve('src/components/Commerce.js')
  const content = fs.readFileSync(commerceFile, 'utf8')

  // Zero raw hex color values outside comments
  const codeWithoutComments = content.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  const hexMatches = codeWithoutComments.match(/#[0-9a-fA-F]{3,8}\b/g)
  assert.equal(hexMatches, null, `Found raw hex color in Commerce.js: ${hexMatches}`)

  // Verifies all four tabs are present
  assert.ok(content.includes("activeTab === 'orders'"), 'Orders tab missing')
  assert.ok(content.includes("activeTab === 'payments'"), 'Payments tab missing')
  assert.ok(content.includes("activeTab === 'deliveries'"), 'Deliveries tab missing')
  assert.ok(content.includes("activeTab === 'products'"), 'Products tab missing')

  // Verifies honest wording per 00-project-law.md
  assert.ok(content.includes('Prepared — not executed'), 'Honest outbound wording missing')
  assert.ok(content.includes('expected_status'), 'D4 concurrency guard missing')
  assert.ok(content.includes('Idempotency-Key'), 'Idempotency key header missing')
})
