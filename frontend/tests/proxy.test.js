import test from 'node:test'
import assert from 'node:assert/strict'
import { GET, POST } from '../src/app/api/backend/[...path]/route.js'

const context = (path) => ({ params: Promise.resolve({ path }) })

test('proxy denies unknown paths and cross-origin writes', async () => {
  const unknown = await GET(
    new Request('http://localhost:3000/api/backend/admin/secrets'),
    context(['admin', 'secrets']),
  )
  assert.equal(unknown.status, 404)
  const crossOrigin = await POST(
    new Request('http://localhost:3000/api/backend/frontend/login', {
      method: 'POST',
      headers: { origin: 'https://attacker.example' },
    }),
    context(['frontend', 'login']),
  )
  assert.equal(crossOrigin.status, 403)
})

test('proxy forwards cookies and CSRF header to the fixed Django origin', async () => {
  const original = globalThis.fetch
  try {
    globalThis.fetch = async (url, options) => {
      assert.equal(url.pathname, '/api/frontend/login/')
      assert.equal(options.headers.cookie, 'csrftoken=abc')
      assert.equal(options.headers['x-csrftoken'], 'abc')
      const headers = new Headers({ 'content-type': 'application/json' })
      headers.append('set-cookie', 'sessionid=xyz; Path=/; HttpOnly; SameSite=Lax')
      return new Response('{"authenticated":true}', { status: 200, headers })
    }
    const request = new Request('http://localhost:3000/api/backend/frontend/login', {
      method: 'POST',
      headers: {
        origin: 'http://localhost:3000',
        cookie: 'csrftoken=abc',
        'x-csrftoken': 'abc',
        'content-type': 'application/json',
      },
      body: '{}',
    })
    const result = await POST(request, context(['frontend', 'login']))
    assert.equal(result.status, 200)
    assert.match(result.headers.get('set-cookie'), /sessionid=xyz/)
  } finally {
    globalThis.fetch = original
  }
})
