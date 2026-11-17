import test from 'node:test'
import assert from 'node:assert/strict'
import {
  money,
  dateTime,
  date,
  relativeTime,
  duration,
  percent,
  enumLabel,
  stripUntrusted,
  recordTitle,
  statusTone,
  statusText,
  missing,
} from '../src/lib/format/index.js'

test('money format properly formats ISO currency, handles null and UNAVAILABLE', () => {
  assert.equal(money(null), '—')
  assert.equal(money(undefined), '—')
  assert.equal(money(''), '—')
  assert.equal(money('UNAVAILABLE'), 'UNAVAILABLE')
  assert.equal(money(0), 'BDT 0.00')
  assert.equal(money(2500), 'BDT 2,500.00')
  assert.equal(money(1234.567), 'BDT 1,234.57')
  assert.equal(money('49.9', 'USD'), 'USD 49.90')
})

test('dateTime and date format with time zone awareness and handle UNAVAILABLE', () => {
  assert.equal(dateTime(null), '—')
  assert.equal(dateTime('UNAVAILABLE'), 'UNAVAILABLE')
  assert.equal(date(null), '—')
  assert.equal(date('UNAVAILABLE'), 'UNAVAILABLE')

  // UTC timestamp 2026-11-09T14:32:00Z is 2026-11-09T20:32:00 in Asia/Dhaka (+6)
  const iso = '2026-11-09T14:32:00Z'
  assert.equal(dateTime(iso, 'Asia/Dhaka'), '09 Nov 2026, 20:32')
  assert.equal(date(iso, 'Asia/Dhaka'), '09 Nov 2026')
})

test('duration formats seconds into compact human-readable duration', () => {
  assert.equal(duration(null), '—')
  assert.equal(duration('UNAVAILABLE'), '—')
  assert.equal(duration(0), '0s')
  assert.equal(duration(45), '45s')
  assert.equal(duration(90), '1m 30s')
  assert.equal(duration(3600), '1h')
  assert.equal(duration(7200), '2h')
  assert.equal(duration(9000), '2h 30m')
  assert.equal(duration(86400), '1d')
  assert.equal(duration(180000), '2d 2h')
})

test('percent formats fractions correctly', () => {
  assert.equal(percent(null), '—')
  assert.equal(percent('UNAVAILABLE'), 'UNAVAILABLE')
  assert.equal(percent(0), '0.0%')
  assert.equal(percent(0.17), '17.0%')
  assert.equal(percent(0.8542, 2), '85.42%')
  assert.equal(percent(1), '100.0%')
})

test('enumLabel formats enums to sentence case', () => {
  assert.equal(enumLabel(null), '—')
  assert.equal(enumLabel('MERGE_CANDIDATES'), 'Merge candidates')
  assert.equal(enumLabel('ACTIVE'), 'Active')
})

test('stripUntrusted removes untrusted data markers for plain-text presentation', () => {
  assert.equal(stripUntrusted(''), '')
  assert.equal(
    stripUntrusted('<untrusted_customer_data>Hello, I need help with my order.</untrusted_customer_data>'),
    'Hello, I need help with my order.',
  )
})

test('statusTone maps exact enum codes correctly, distinguishing INACTIVE from ACTIVE', () => {
  // CRITICAL REGRESSION TEST: Old regex /ACTIVE/ falsely matched INACTIVE as success
  assert.equal(statusTone('INACTIVE'), 'neutral')
  assert.equal(statusTone('ACTIVE'), 'success')

  // Additional status codes required by spec
  assert.equal(statusTone('RETURNED'), 'danger')
  assert.equal(statusTone('REFUNDED'), 'success')
  assert.equal(statusTone('SENT'), 'success')
  assert.equal(statusTone('MISSED'), 'danger')
  assert.equal(statusTone('BUSY'), 'warning')
  assert.equal(statusTone('CLOSED'), 'success')

  // Core system statuses
  assert.equal(statusTone('NOT MOUNTED'), 'not-mounted')
  assert.equal(statusTone('UNAVAILABLE'), 'unavailable')
  assert.equal(statusTone('SUGGESTED'), 'ai')
  assert.equal(statusTone('FAILED'), 'danger')
  assert.equal(statusTone('PENDING'), 'warning')
  assert.equal(statusTone('PAID'), 'success')
})

test('statusText produces honest wording per spec', () => {
  assert.equal(statusText({ direction: 'OUTGOING', status: 'PENDING' }), 'Pending — not delivered')
  assert.equal(statusText({ is_ai_generated: true, status: 'SUGGESTED' }), 'AI suggestion')
  assert.equal(statusText({ status: 'DELIVERED' }), 'Delivered')
  assert.equal(statusText(null), 'Recorded')
})

test('recordTitle derives human readable titles using domain identifiers', () => {
  assert.equal(recordTitle({ display_name: 'Acme Corp' }), 'Acme Corp')
  assert.equal(recordTitle({ name: 'Jane Doe' }), 'Jane Doe')
  assert.equal(recordTitle({ transaction_reference: 'TXN-98765' }), 'TXN-98765')
  assert.equal(recordTitle({ external_refund_id: 'REF-12345' }), 'REF-12345')
  assert.equal(recordTitle({ tag: 'VIP' }), 'VIP')
  assert.equal(recordTitle({ sku: 'PROD-SKU-1' }), 'PROD-SKU-1')
  assert.equal(recordTitle({ value: '+8801700000000' }), '+8801700000000')
  assert.equal(recordTitle({ id: 42 }), 'Record #42')
  assert.equal(recordTitle(null), 'Record #—')
})

test('relativeTime handles past, recent, and future dates properly', () => {
  const now = new Date('2026-11-09T14:32:00Z')
  // 10s ago
  assert.equal(relativeTime('2026-11-09T14:31:50Z', now), 'just now')
  // 5m ago
  assert.equal(relativeTime('2026-11-09T14:27:00Z', now), '5m ago')
  // 2h ago
  assert.equal(relativeTime('2026-11-09T12:32:00Z', now), '2h ago')
  // Future date (must not be 'just now')
  const future = '2026-11-10T14:32:00Z'
  assert.equal(relativeTime(future, now), date(future))
})

test('stripUntrusted is resilient against case variations and whitespace', () => {
  assert.equal(
    stripUntrusted('<UNTRUSTED_CUSTOMER_DATA>  Sensitive message  </UNTRUSTED_CUSTOMER_DATA>'),
    'Sensitive message',
  )
})
