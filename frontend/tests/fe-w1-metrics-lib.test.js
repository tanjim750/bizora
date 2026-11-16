import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { metricsPath, snapshotsPath, normalizeList } from '../src/lib/intelligence/metrics.js'

test('metricsPath returns valid path with default limit and offset', () => {
  const p = metricsPath(1)
  assert.equal(p, 'businesses/1/intelligence/metrics/?limit=100&offset=0')
})

test('metricsPath honors custom limit and offset', () => {
  const p = metricsPath('42', { limit: 50, offset: 100 })
  assert.equal(p, 'businesses/42/intelligence/metrics/?limit=50&offset=100')
})

test('metricsPath throws on invalid limit or offset', () => {
  assert.throws(() => metricsPath(1, { limit: 0 }), /limit/i)
  assert.throws(() => metricsPath(1, { limit: 201 }), /limit/i)
  assert.throws(() => metricsPath(1, { limit: 1.5 }), /limit/i)
  assert.throws(() => metricsPath(1, { offset: -1 }), /offset/i)
  assert.throws(() => metricsPath(1, { offset: 'abc' }), /offset/i)
})

test('snapshotsPath returns valid path for dotted metric key', () => {
  const p = snapshotsPath(1, 'bi.metric.sales_total_orders.v1')
  assert.equal(
    p,
    'businesses/1/intelligence/metrics/bi.metric.sales_total_orders.v1/snapshots/?limit=50&offset=0',
  )
})

test('snapshotsPath honors period_type and custom limit/offset', () => {
  const p = snapshotsPath(1, 'sales_total', { periodType: 'MONTH', limit: 25, offset: 10 })
  assert.equal(
    p,
    'businesses/1/intelligence/metrics/sales_total/snapshots/?limit=25&offset=10&period_type=MONTH',
  )
})

test('snapshotsPath throws on invalid metric key', () => {
  assert.throws(() => snapshotsPath(1, '..'), /Invalid metric key/i)
  assert.throws(() => snapshotsPath(1, '.metric'), /Invalid metric key/i)
  assert.throws(() => snapshotsPath(1, 'metric.'), /Invalid metric key/i)
  assert.throws(() => snapshotsPath(1, 'a..b'), /Invalid metric key/i)
  assert.throws(() => snapshotsPath(1, ''), /Invalid metric key/i)
  assert.throws(() => snapshotsPath(1, null), /Invalid metric key/i)
})

test('snapshotsPath throws on invalid periodType', () => {
  assert.throws(() => snapshotsPath(1, 'sales', { periodType: 'YEAR' }), /period/i)
  assert.throws(() => snapshotsPath(1, 'sales', { periodType: 'invalid' }), /period/i)
})

test('normalizeList normalizes total_count shape', () => {
  const data = {
    total_count: 42,
    limit: 10,
    offset: 20,
    results: [{ id: 1 }, { id: 2 }],
  }
  const norm = normalizeList(data)
  assert.deepEqual(norm, {
    total: 42,
    limit: 10,
    offset: 20,
    results: [{ id: 1 }, { id: 2 }],
  })
})

test('normalizeList normalizes standard count shape', () => {
  const data = {
    count: 15,
    results: ['a', 'b'],
  }
  const norm = normalizeList(data)
  assert.deepEqual(norm, {
    total: 15,
    limit: 0,
    offset: 0,
    results: ['a', 'b'],
  })
})

test('normalizeList handles junk or empty input gracefully', () => {
  assert.deepEqual(normalizeList(null), { total: 0, limit: 0, offset: 0, results: [] })
  assert.deepEqual(normalizeList(undefined), { total: 0, limit: 0, offset: 0, results: [] })
  assert.deepEqual(normalizeList({}), { total: 0, limit: 0, offset: 0, results: [] })
  assert.deepEqual(normalizeList('string'), { total: 0, limit: 0, offset: 0, results: [] })
  assert.deepEqual(normalizeList({ results: 'not-array' }), { total: 0, limit: 0, offset: 0, results: [] })
})

test('Intelligence.js imports from @/lib/intelligence/metrics and drops Analytical metrics registry', () => {
  const filePath = path.join(process.cwd(), 'src/components/Intelligence.js')
  const content = fs.readFileSync(filePath, 'utf8')
  assert.ok(
    content.includes('@/lib/intelligence/metrics'),
    'Intelligence.js must import from @/lib/intelligence/metrics',
  )
  assert.ok(
    !content.includes('Analytical metrics registry'),
    'Intelligence.js must no longer contain "Analytical metrics registry"',
  )
})
