import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('source text: Customers.js uses tracking_code instead of tracking_number (CUS-F2)', () => {
  const file = path.resolve('src/components/Customers.js')
  const content = fs.readFileSync(file, 'utf8')

  assert.ok(!content.includes('tracking_number'), 'Customers.js must not contain tracking_number')
  assert.ok(content.includes('sh.tracking_code'), 'Customers.js must include sh.tracking_code')
  assert.ok(content.includes('row.tracking_code'), 'Customers.js must include row.tracking_code')
  assert.ok(content.includes("key: 'tracking_code'"), "Customers.js must include key: 'tracking_code'")
  assert.ok(
    content.includes('Tracking Number'),
    'Customers.js must still contain column label Tracking Number',
  )
})
