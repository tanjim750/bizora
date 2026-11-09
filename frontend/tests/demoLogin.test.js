import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { demoLoginConfig, cookieFromSetCookie } from '../src/lib/demoLogin.js'
import { GET, POST } from '../src/app/api/demo-login/route.js'

const ENV = {
  NODE_ENV: 'development',
  BIZORA_DEMO_LOGIN: '1',
  BIZORA_DEMO_USERNAME: 'demo-owner',
  BIZORA_DEMO_PASSWORD: 'test-only-secret',
  DJANGO_API_ORIGIN: undefined,
}

async function withEnv(values, run) {
  const before = {}
  for (const [key, value] of Object.entries(values)) {
    before[key] = process.env[key]
    if (value === undefined) delete process.env[key]
    else process.env[key] = value
  }
  try {
    return await run()
  } finally {
    for (const [key, value] of Object.entries(before)) {
      if (value === undefined) delete process.env[key]
      else process.env[key] = value
    }
  }
}

const post = (url = 'http://localhost:3000/api/demo-login', headers = {}) =>
  POST(new Request(url, { method: 'POST', headers }))

test('demo login is off unless explicitly enabled with credentials', () => {
  assert.equal(demoLoginConfig({}), null)
  assert.equal(demoLoginConfig({ ...ENV, BIZORA_DEMO_LOGIN: '0' }), null)
  assert.equal(demoLoginConfig({ ...ENV, BIZORA_DEMO_LOGIN: 'true' }), null)
  assert.equal(demoLoginConfig({ ...ENV, BIZORA_DEMO_PASSWORD: '' }), null)
  assert.equal(demoLoginConfig({ ...ENV, BIZORA_DEMO_USERNAME: undefined }), null)
})

test('demo login fails closed: only NODE_ENV=development turns it on', () => {
  for (const mode of ['production', 'test', 'staging', '', undefined]) {
    assert.equal(demoLoginConfig({ ...ENV, NODE_ENV: mode }), null, `NODE_ENV=${mode}`)
  }
  assert.deepEqual(demoLoginConfig(ENV), { username: 'demo-owner', password: 'test-only-secret' })
})

test('demo login needs a backend on this machine', () => {
  for (const origin of ['http://127.0.0.1:8000', 'http://localhost:8000', 'http://[::1]:8000']) {
    assert.notEqual(demoLoginConfig({ ...ENV, DJANGO_API_ORIGIN: origin }), null, origin)
  }
  for (const origin of [
    'https://api.example.com',
    'http://10.0.0.5:8000',
    'http://staging.internal',
    'not a url',
  ]) {
    assert.equal(demoLoginConfig({ ...ENV, DJANGO_API_ORIGIN: origin }), null, origin)
  }
})

test('cookieFromSetCookie reads one cookie value', () => {
  const lines = ['sessionid=abc; Path=/; HttpOnly', 'csrftoken=tok123; expires=x; Path=/']
  assert.equal(cookieFromSetCookie(lines, 'csrftoken'), 'tok123')
  assert.equal(cookieFromSetCookie(lines, 'missing'), '')
})

test('demo route does not exist when disabled, in production, or when the flag is set in production', async () => {
  await withEnv({ ...ENV, BIZORA_DEMO_LOGIN: undefined }, async () => {
    assert.equal((await post()).status, 404)
    const probe = await GET(new Request('http://localhost:3000/api/demo-login'))
    assert.deepEqual(await probe.json(), { enabled: false })
  })
  await withEnv({ ...ENV, NODE_ENV: 'production' }, async () => {
    assert.equal((await post()).status, 404)
    const probe = await GET(new Request('http://localhost:3000/api/demo-login'))
    assert.deepEqual(await probe.json(), { enabled: false })
  })
})

test('demo route ignores requests not addressed to this machine (LAN devices, DNS rebinding)', async () => {
  await withEnv(ENV, async () => {
    for (const url of [
      'http://192.168.0.104:3000/api/demo-login',
      'http://evil.example:3915/api/demo-login',
      'http://localhost.evil.example:3000/api/demo-login',
    ]) {
      const origin = new URL(url).origin
      assert.equal((await post(url, { origin })).status, 404, url)
      assert.equal((await post(url)).status, 404, `${url} without Origin`)
      assert.deepEqual(await (await GET(new Request(url))).json(), { enabled: false }, url)
    }
    const local = await GET(new Request('http://127.0.0.1:3000/api/demo-login'))
    assert.deepEqual(await local.json(), { enabled: true })
  })
})

test('demo route refuses cross-origin and cross-site requests', async () => {
  await withEnv(ENV, async () => {
    assert.equal((await post(undefined, { origin: 'https://attacker.example' })).status, 403)
    assert.equal((await post(undefined, { origin: 'null' })).status, 403)
    assert.equal((await post(undefined, { 'sec-fetch-site': 'cross-site' })).status, 403)
    assert.equal((await post(undefined, { 'sec-fetch-site': 'same-site' })).status, 403)
  })
})

test('demo route signs in server-side and never returns the password', async () => {
  const original = globalThis.fetch
  const calls = []
  try {
    globalThis.fetch = async (url, options = {}) => {
      calls.push({ path: url.pathname, options })
      const headers = new Headers({ 'content-type': 'application/json' })
      if (url.pathname === '/api/frontend/session/') {
        headers.append('set-cookie', 'csrftoken=tok123; Path=/; SameSite=Lax')
        return new Response('{"authenticated":false}', { status: 200, headers })
      }
      headers.append('set-cookie', 'sessionid=sess456; Path=/; HttpOnly; SameSite=Lax')
      headers.append('set-cookie', 'csrftoken=tok789; Path=/; SameSite=Lax')
      return new Response('{"authenticated":true}', { status: 200, headers })
    }
    await withEnv(ENV, async () => {
      const response = await post(undefined, {
        origin: 'http://localhost:3000',
        'sec-fetch-site': 'same-origin',
      })
      assert.equal(response.status, 200)
      const text = await response.text()
      assert.equal(text.includes('test-only-secret'), false)
      assert.deepEqual(JSON.parse(text), { authenticated: true })
      const cookies = response.headers.getSetCookie().join('\n')
      assert.match(cookies, /sessionid=sess456/)
      assert.match(cookies, /csrftoken=tok789/)
    })
    assert.deepEqual(
      calls.map((call) => call.path),
      ['/api/frontend/session/', '/api/frontend/login/'],
    )
    const login = calls[1].options
    assert.equal(login.headers['x-csrftoken'], 'tok123')
    assert.equal(login.headers.cookie, 'csrftoken=tok123')
    assert.deepEqual(JSON.parse(login.body), { username: 'demo-owner', password: 'test-only-secret' })
  } finally {
    globalThis.fetch = original
  }
})

test('demo route reports a failed backend sign-in without leaking the password', async () => {
  const original = globalThis.fetch
  const originalError = console.error
  const logged = []
  try {
    console.error = (...args) => logged.push(args.join(' '))
    globalThis.fetch = async (url) => {
      const headers = new Headers({ 'content-type': 'application/json' })
      if (url.pathname === '/api/frontend/session/') {
        headers.append('set-cookie', 'csrftoken=tok123; Path=/')
        return new Response('{}', { status: 200, headers })
      }
      return new Response('{"detail":"Invalid username or password."}', { status: 401, headers })
    }
    await withEnv(ENV, async () => {
      const response = await post()
      assert.equal(response.status, 502)
      assert.equal((await response.text()).includes('test-only-secret'), false)
    })
    assert.equal(logged.length, 1)
    assert.equal(logged[0].includes('test-only-secret'), false)
  } finally {
    globalThis.fetch = original
    console.error = originalError
  }
})

test('the login page (client code) never references the demo credentials or the server helper', () => {
  const page = readFileSync(new URL('../src/app/login/page.js', import.meta.url), 'utf8')
  assert.equal(/BIZORA_DEMO|demoLogin|DEMO_PASSWORD/.test(page), false)
})
