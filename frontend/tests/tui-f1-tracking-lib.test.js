import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  trackingBase,
  summaryPath,
  attemptsPath,
  settingsPath,
  ALLOWED_EVENTS,
  PROVIDER_LABELS,
  providerLabel,
  modeLabel,
  statusTone,
  attemptTone,
  normalizeSummary,
  normalizeAttempts,
  settingsPatchBody,
} from '../src/lib/tracking/api.js'

test('trackingBase and summaryPath build valid URLs and throw on invalid businessId (TUI-F1)', () => {
  assert.equal(trackingBase(1), 'businesses/1/integrations/tracking/')
  assert.equal(trackingBase(42), 'businesses/42/integrations/tracking/')
  assert.throws(() => trackingBase(0), /Invalid business ID/)
  assert.throws(() => trackingBase(-1), /Invalid business ID/)
  assert.throws(() => trackingBase('abc'), /Invalid business ID/)

  assert.equal(summaryPath(1), 'businesses/1/integrations/tracking/summary/')
})

test('attemptsPath handles valid options, defaults, and throws on invalid params (TUI-F1)', () => {
  // Default path
  const defaultPath = attemptsPath(1)
  assert.match(defaultPath, /^businesses\/1\/integrations\/tracking\/attempts\/\?/)
  assert.match(defaultPath, /limit=25/)
  assert.match(defaultPath, /offset=0/)

  // Filter params
  const fullPath = attemptsPath(1, {
    connection: 5,
    status: 'SUCCEEDED',
    mode: 'LIVE',
    limit: 50,
    offset: 10,
  })
  assert.match(fullPath, /connection=5/)
  assert.match(fullPath, /status=SUCCEEDED/)
  assert.match(fullPath, /mode=LIVE/)
  assert.match(fullPath, /limit=50/)
  assert.match(fullPath, /offset=10/)

  // Error cases
  assert.throws(() => attemptsPath(1, { connection: 0 }), /connection/i)
  assert.throws(() => attemptsPath(1, { connection: -5 }), /connection/i)
  assert.throws(() => attemptsPath(1, { connection: 'foo' }), /connection/i)
  assert.throws(() => attemptsPath(1, { status: 'INVALID' }), /status/i)
  assert.throws(() => attemptsPath(1, { mode: 'OTHER' }), /mode/i)
  assert.throws(() => attemptsPath(1, { limit: 0 }), /limit/i)
  assert.throws(() => attemptsPath(1, { limit: 201 }), /limit/i)
  assert.throws(() => attemptsPath(1, { offset: -1 }), /offset/i)
})

test('settingsPath builds valid endpoint and throws on invalid connectionId (TUI-F1)', () => {
  assert.equal(settingsPath(1, 5), 'businesses/1/integrations/tracking/connections/5/settings/')
  assert.throws(() => settingsPath(1, 0), /connection/i)
  assert.throws(() => settingsPath(1, -2), /connection/i)
  assert.throws(() => settingsPath(1, 'bad'), /connection/i)
})

test('ALLOWED_EVENTS contains exactly the 13 specified events in order (TUI-F1)', () => {
  const expected = [
    'VIEW',
    'PAGE_VIEW',
    'PRODUCT_VIEW',
    'VIEW_ITEM',
    'CART',
    'ADD_TO_CART',
    'CHECKOUT',
    'CHECKOUT_START',
    'BEGIN_CHECKOUT',
    'PURCHASE',
    'ORDER',
    'CHECKOUT_COMPLETE',
    'ORDER_COMPLETE',
  ]
  assert.deepEqual(ALLOWED_EVENTS, expected)
  assert.equal(ALLOWED_EVENTS.length, 13)
})

test('PROVIDER_LABELS and providerLabel handle known and fallback values (TUI-F1)', () => {
  assert.equal(PROVIDER_LABELS.meta, 'Meta Conversions API')
  assert.equal(PROVIDER_LABELS.tiktok, 'TikTok Events API')
  assert.equal(PROVIDER_LABELS.ga4, 'Google Analytics 4')

  assert.equal(providerLabel('meta'), 'Meta Conversions API')
  assert.equal(providerLabel('tiktok'), 'TikTok Events API')
  assert.equal(providerLabel('ga4'), 'Google Analytics 4')
  assert.equal(providerLabel('custom'), 'custom')
  assert.equal(providerLabel(''), 'Unknown provider')
  assert.equal(providerLabel(null), 'Unknown provider')
})

test('modeLabel returns honest status text without falsely claiming send/success (TUI-F1)', () => {
  // PREPARED
  assert.equal(modeLabel('PREPARED', false), 'Prepared, not sent')
  assert.equal(modeLabel('PREPARED', true), 'Prepared, not sent') // prepared row must NEVER be labelled as sent

  // LIVE
  assert.equal(modeLabel('LIVE', true), 'Sent and accepted')
  assert.equal(modeLabel('LIVE', false), 'Sent, not accepted')

  // Other / null
  assert.equal(modeLabel(null, false), 'No send attempted')
  assert.equal(modeLabel('UNKNOWN', false), 'No send attempted')
})

test('statusTone and attemptTone map tones honestly (TUI-F1)', () => {
  assert.equal(statusTone('SUCCEEDED'), 'success')
  assert.equal(statusTone('FAILED'), 'danger')
  assert.equal(statusTone('UNSUPPORTED'), 'neutral')
  assert.equal(statusTone('RUNNING'), 'info')
  assert.equal(statusTone('UNKNOWN'), 'neutral')

  // attemptTone
  assert.equal(attemptTone({ sent: true, status: 'SUCCEEDED' }), 'success')
  assert.equal(attemptTone({ sent: false, status: 'SUCCEEDED' }), 'info') // prepared SUCCEEDED is info, not success
  assert.equal(attemptTone({ sent: false, status: 'FAILED' }), 'danger')
  assert.equal(attemptTone({ sent: false, status: 'RUNNING' }), 'info')
  assert.equal(attemptTone({ sent: false, status: 'UNSUPPORTED' }), 'neutral')
  assert.equal(attemptTone(null), 'neutral')
})

test('normalizeSummary handles full contract data, missing fields, and junk (TUI-F1)', () => {
  const fullData = {
    business_id: 1,
    connections: [
      {
        id: 5,
        name: 'Meta Pixel',
        provider: 'meta',
        status: 'CONNECTED',
        is_mock: true,
        mode: 'PREPARED',
        credentials_available: false,
        settings: {
          enabled: false,
          test_mode: false,
          events: [],
          test_event_code: null,
          measurement_id: null,
          api_version: null,
          send_pii: false,
        },
        counts: { total: 10, prepared: 10, live_succeeded: 0, failed: 0, unsupported: 0 },
        last_attempt_at: '2026-11-17T09:00:00Z',
      },
      {
        // Missing id -> must be dropped
        name: 'Invalid Connection',
      },
    ],
    totals: { connections: 1, attempts: 10 },
  }

  const normalized = normalizeSummary(fullData)
  assert.equal(normalized.businessId, 1)
  assert.equal(normalized.connections.length, 1)
  assert.equal(normalized.connections[0].id, 5)
  assert.equal(normalized.connections[0].name, 'Meta Pixel')
  assert.equal(normalized.connections[0].provider, 'meta')
  assert.equal(normalized.connections[0].settings.send_pii, false)
  assert.equal(normalized.totals.connections, 1)
  assert.equal(normalized.totals.attempts, 10)

  // Junk input
  const empty = normalizeSummary(null)
  assert.deepEqual(empty, {
    businessId: null,
    connections: [],
    totals: { connections: 0, attempts: 0 },
  })

  const junk = normalizeSummary({ connections: 'not-an-array' })
  assert.deepEqual(junk, {
    businessId: null,
    connections: [],
    totals: { connections: 0, attempts: 0 },
  })
})

test('normalizeAttempts handles total_count, count, contract fields, and junk (TUI-F1)', () => {
  const dataTotalCount = {
    total_count: 1,
    limit: 25,
    offset: 0,
    results: [
      {
        id: 901,
        connection_id: 5,
        connection_name: 'Meta Pixel',
        provider: 'meta',
        status: 'SUCCEEDED',
        mode: 'PREPARED',
        sent: 0, // must coerce to boolean false
        created_at: '2026-11-17T09:00:00Z',
      },
    ],
  }
  const norm1 = normalizeAttempts(dataTotalCount)
  assert.equal(norm1.total, 1)
  assert.equal(norm1.results[0].sent, false)
  assert.equal(norm1.results[0].id, 901)

  const dataCount = {
    count: 2,
    results: [{ id: 902, sent: 1 }],
  }
  const norm2 = normalizeAttempts(dataCount)
  assert.equal(norm2.total, 2)
  assert.equal(norm2.results[0].sent, true)

  const junk = normalizeAttempts('invalid')
  assert.deepEqual(junk, { total: 0, limit: 0, offset: 0, results: [] })
})

test('settingsPatchBody computes diffs, validates per provider, and omits extra keys (TUI-F1)', () => {
  const metaConn = {
    id: 5,
    provider: 'meta',
    settings: {
      enabled: false,
      test_mode: false,
      events: ['VIEW', 'PURCHASE'],
      test_event_code: null,
      measurement_id: null,
      api_version: 'v18.0',
      send_pii: false,
    },
  }

  // Nothing changed -> {}
  const noChange = settingsPatchBody(metaConn, {
    enabled: false,
    test_mode: false,
    events: ['PURCHASE', 'view'], // case-insensitive & order-insensitive
    test_event_code: '',
    api_version: 'v18.0',
  })
  assert.deepEqual(noChange, {})

  // Single key changes
  assert.deepEqual(settingsPatchBody(metaConn, { enabled: true }), { enabled: true })
  assert.deepEqual(settingsPatchBody(metaConn, { test_mode: true }), { test_mode: true })
  assert.deepEqual(settingsPatchBody(metaConn, { events: ['PURCHASE'] }), { events: ['PURCHASE'] })
  assert.deepEqual(settingsPatchBody(metaConn, { test_event_code: 'TEST1234' }), {
    test_event_code: 'TEST1234',
  })
  assert.deepEqual(settingsPatchBody(metaConn, { api_version: 'v19.0' }), {
    api_version: 'v19.0',
  })

  // Provider restrictions
  // test_event_code on ga4 throws
  const ga4Conn = { id: 6, provider: 'ga4', settings: { measurement_id: 'G-ABC1234' } }
  assert.throws(() => settingsPatchBody(ga4Conn, { test_event_code: 'CODE' }), /test_event_code/i)

  // measurement_id on meta throws
  assert.throws(() => settingsPatchBody(metaConn, { measurement_id: 'G-123456' }), /measurement_id/i)

  // api_version on tiktok throws
  const tiktokConn = { id: 7, provider: 'tiktok', settings: {} }
  assert.throws(() => settingsPatchBody(tiktokConn, { api_version: 'v18.0' }), /api_version/i)

  // Invalid formats
  assert.throws(() => settingsPatchBody(ga4Conn, { measurement_id: 'invalid-format' }), /measurement_id/i)
  assert.throws(() => settingsPatchBody(metaConn, { api_version: 'version18' }), /api_version/i)
  assert.throws(() => settingsPatchBody(metaConn, { events: ['NOT_AN_EVENT'] }), /event/i)
  assert.throws(() => settingsPatchBody(metaConn, { enabled: 'yes' }), /boolean/i)
  assert.throws(() => settingsPatchBody(metaConn, { test_event_code: 'a'.repeat(65) }), /test_event_code/i)

  // Extra keys (send_pii, is_mock) are never included
  const diffWithExtra = settingsPatchBody(metaConn, {
    enabled: true,
    send_pii: true,
    is_mock: false,
    some_secret: 'bad',
  })
  assert.deepEqual(diffWithExtra, { enabled: true })
})
