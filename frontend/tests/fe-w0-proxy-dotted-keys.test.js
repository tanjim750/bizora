import test from 'node:test'
import assert from 'node:assert/strict'
import { GET } from '../src/app/api/backend/[...path]/route.js'

const context = (path) => ({ params: Promise.resolve({ path }) })

test('proxy forwards dotted metric keys on businesses/<id>/intelligence/metrics/<key>/snapshots', async () => {
  const original = globalThis.fetch
  try {
    let requestedUrl = null
    globalThis.fetch = async (url) => {
      requestedUrl = url
      return new Response('{"count":0,"results":[]}', {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    }

    const key = 'bi.metric.sales_total_orders.v1'
    const request = new Request(
      `http://localhost:3000/api/backend/businesses/1/intelligence/metrics/${key}/snapshots`,
    )
    const res = await GET(request, context(['businesses', '1', 'intelligence', 'metrics', key, 'snapshots']))

    assert.equal(res.status, 200)
    assert.equal(
      requestedUrl.pathname,
      '/api/businesses/1/intelligence/metrics/bi.metric.sales_total_orders.v1/snapshots/',
    )
  } finally {
    globalThis.fetch = original
  }
})

test('proxy allows non-dotted metric keys on snapshots path', async () => {
  const original = globalThis.fetch
  try {
    let requestedUrl = null
    globalThis.fetch = async (url) => {
      requestedUrl = url
      return new Response('{"count":0,"results":[]}', {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    }

    const key = 'revenue'
    const request = new Request(
      `http://localhost:3000/api/backend/businesses/1/intelligence/metrics/${key}/snapshots`,
    )
    const res = await GET(request, context(['businesses', '1', 'intelligence', 'metrics', key, 'snapshots']))

    assert.equal(res.status, 200)
    assert.equal(requestedUrl.pathname, '/api/businesses/1/intelligence/metrics/revenue/snapshots/')
  } finally {
    globalThis.fetch = original
  }
})

test('proxy rejects invalid dot configurations in metric key', async () => {
  const invalidKeys = ['..', 'a..b', '.a', 'a.']
  for (const badKey of invalidKeys) {
    const res = await GET(
      new Request(`http://localhost:3000/api/backend/businesses/1/intelligence/metrics/${badKey}/snapshots`),
      context(['businesses', '1', 'intelligence', 'metrics', badKey, 'snapshots']),
    )
    assert.equal(res.status, 404, `Expected 404 for key: ${badKey}`)
    const body = await res.json()
    assert.equal(body.detail, 'Unknown API route.')
  }
})

test('proxy rejects dotted segments on non-snapshots paths', async () => {
  // Dotted segment on customers path
  const res1 = await GET(
    new Request('http://localhost:3000/api/backend/businesses/1/customers/a.b'),
    context(['businesses', '1', 'customers', 'a.b']),
  )
  assert.equal(res1.status, 404)
  const body1 = await res1.json()
  assert.equal(body1.detail, 'Unknown API route.')

  // Dotted key on metrics detail path (5 segments, without snapshots)
  const res2 = await GET(
    new Request('http://localhost:3000/api/backend/businesses/1/intelligence/metrics/a.b'),
    context(['businesses', '1', 'intelligence', 'metrics', 'a.b']),
  )
  assert.equal(res2.status, 404)
  const body2 = await res2.json()
  assert.equal(body2.detail, 'Unknown API route.')
})
