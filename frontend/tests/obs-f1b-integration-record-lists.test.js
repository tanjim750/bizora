import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  RECORD_KINDS,
  FAILED_RECORD_STATUSES,
  WEBHOOK_STATUSES,
  RECORD_PAGE_SIZE,
  MESSAGE_PREVIEW_CHARS,
  recordListPath,
  shortenText,
  normalizeRecordPage,
  canOpenPayload,
  recordListError,
} from '../src/lib/observability/records.js'

test('constants: RECORD_KINDS, FAILED_RECORD_STATUSES, WEBHOOK_STATUSES, page size, preview chars (OBS-F1b)', () => {
  assert.deepEqual(RECORD_KINDS, ['failed-records', 'webhooks'])
  assert.deepEqual(FAILED_RECORD_STATUSES, ['OPEN', 'REVIEWING', 'RETRYING', 'RESOLVED', 'IGNORED'])
  assert.deepEqual(WEBHOOK_STATUSES, ['RECEIVED', 'ROUTING', 'PROCESSED', 'FAILED', 'REJECTED'])
  assert.equal(RECORD_PAGE_SIZE, 25)
  assert.equal(MESSAGE_PREVIEW_CHARS, 160)
  assert.ok(Object.isFrozen(RECORD_KINDS))
  assert.ok(Object.isFrozen(FAILED_RECORD_STATUSES))
  assert.ok(Object.isFrozen(WEBHOOK_STATUSES))
})

test('recordListPath builds valid path and validates parameters (OBS-F1b)', () => {
  assert.equal(
    recordListPath(1, 'failed-records'),
    'businesses/1/observability/failed-records/?page=1&page_size=25',
  )
  assert.equal(
    recordListPath(1, 'failed-records', { page: 3, pageSize: 50, status: 'OPEN' }),
    'businesses/1/observability/failed-records/?page=3&page_size=50&status=OPEN',
  )
  assert.equal(
    recordListPath(2, 'webhooks', { status: 'FAILED' }),
    'businesses/2/observability/webhooks/?page=1&page_size=25&status=FAILED',
  )
  assert.equal(
    recordListPath(1, 'failed-records', { status: '' }),
    'businesses/1/observability/failed-records/?page=1&page_size=25',
  )

  // Throwing cases
  assert.throws(() => recordListPath(1, 'errors'), /Unsupported record list: errors/)
  assert.throws(() => recordListPath(1, 'webhooks', { status: 'OPEN' }), /Unsupported status: OPEN/)
  assert.throws(() => recordListPath(1, 'failed-records', { status: 'DONE' }), /Unsupported status: DONE/)
  assert.throws(
    () => recordListPath(1, 'failed-records', { page: 0 }),
    /page must be a whole number of at least 1\./,
  )
  assert.throws(
    () => recordListPath(1, 'failed-records', { page: 1.5 }),
    /page must be a whole number of at least 1\./,
  )
  assert.throws(
    () => recordListPath(1, 'failed-records', { page: '2' }),
    /page must be a whole number of at least 1\./,
  )
  assert.throws(
    () => recordListPath(1, 'failed-records', { pageSize: 0 }),
    /pageSize must be a whole number between 1 and 100\./,
  )
  assert.throws(
    () => recordListPath(1, 'failed-records', { pageSize: 101 }),
    /pageSize must be a whole number between 1 and 100\./,
  )
  assert.throws(() => recordListPath(0, 'failed-records'), /Invalid business ID/)
})

test('shortenText collapses whitespace and truncates at max with ellipsis (OBS-F1b)', () => {
  assert.equal(shortenText('  a   b\n c '), 'a b c')
  const longText = 'x'.repeat(200)
  const shortened = shortenText(longText)
  assert.equal(shortened.length, 161)
  assert.ok(shortened.endsWith('…'))
  assert.equal(shortenText(null), '')
  assert.equal(shortenText(5), '')
})

test('normalizeRecordPage normalizes failed records and webhooks safely (OBS-F1b)', () => {
  const failedPage = {
    count: 42,
    next: null,
    previous: null,
    results: [
      {
        id: 9,
        connection_id: 5,
        entity_type: 'PRODUCT',
        external_id: 'sku-1',
        stage: 'MAPPING',
        code: 'MISSING_PRICE',
        message: 'Price is missing',
        payload_id: 12,
        sync_id: null,
        webhook_id: null,
        error_id: 3,
        status: 'OPEN',
        first_seen_at: '2026-11-16T09:00:00Z',
        last_seen_at: '2026-11-17T09:00:00Z',
        resolved_at: null,
        resolution: '',
        resolution_method: '',
      },
      { id: 'x' },
      { id: 10, payload_id: null, status: 'RESOLVED' },
    ],
  }

  const normalizedFailed = normalizeRecordPage(failedPage, 'failed-records')
  assert.deepEqual(normalizedFailed, {
    total: 42,
    rows: [
      {
        id: 9,
        entityType: 'PRODUCT',
        externalId: 'sku-1',
        stage: 'MAPPING',
        code: 'MISSING_PRICE',
        message: 'Price is missing',
        status: 'OPEN',
        payloadId: 12,
        lastSeenAt: '2026-11-17T09:00:00Z',
      },
      {
        id: 10,
        entityType: null,
        externalId: null,
        stage: null,
        code: null,
        message: '',
        status: 'RESOLVED',
        payloadId: null,
        lastSeenAt: null,
      },
    ],
  })

  const webhookPage = {
    count: 1,
    results: [
      {
        id: 4,
        event_id: 'evt-1',
        event_type: 'order.created',
        entity_type: 'ORDER',
        validation: 'VALID',
        status: 'FAILED',
        payload_id: 7,
        received_at: '2026-11-17T09:00:00Z',
        delivery_count: 2,
        replay_eligible: true,
      },
    ],
  }

  const normalizedWebhooks = normalizeRecordPage(webhookPage, 'webhooks')
  assert.deepEqual(normalizedWebhooks, {
    total: 1,
    rows: [
      {
        id: 4,
        eventId: 'evt-1',
        eventType: 'order.created',
        entityType: 'ORDER',
        validation: 'VALID',
        status: 'FAILED',
        payloadId: 7,
        receivedAt: '2026-11-17T09:00:00Z',
        deliveryCount: 2,
      },
    ],
  })

  // Fallback and junk handling
  assert.deepEqual(
    normalizeRecordPage(
      {
        results: [
          { id: 1, payload_id: 0 },
          { id: 2, payload_id: -1 },
          { id: 3, payload_id: '12' },
        ],
      },
      'webhooks',
    ),
    {
      total: 3,
      rows: [
        {
          id: 1,
          eventId: null,
          eventType: null,
          entityType: null,
          validation: null,
          status: null,
          payloadId: null,
          receivedAt: null,
          deliveryCount: null,
        },
        {
          id: 2,
          eventId: null,
          eventType: null,
          entityType: null,
          validation: null,
          status: null,
          payloadId: null,
          receivedAt: null,
          deliveryCount: null,
        },
        {
          id: 3,
          eventId: null,
          eventType: null,
          entityType: null,
          validation: null,
          status: null,
          payloadId: null,
          receivedAt: null,
          deliveryCount: null,
        },
      ],
    },
  )
  assert.deepEqual(normalizeRecordPage(null, 'failed-records'), { total: 0, rows: [] })
  assert.deepEqual(normalizeRecordPage('junk', 'webhooks'), { total: 0, rows: [] })
  assert.throws(() => normalizeRecordPage({}, 'errors'), /Unsupported record list: errors/)
})

test('canOpenPayload verifies role and payloadId (OBS-F1b)', () => {
  assert.equal(canOpenPayload({ payloadId: 12 }, 'OWNER'), true)
  assert.equal(canOpenPayload({ payloadId: 12 }, 'MANAGER'), true)
  assert.equal(canOpenPayload({ payloadId: 12 }, 'OPERATOR'), false)
  assert.equal(canOpenPayload({ payloadId: 12 }, 'VIEWER'), false)
  assert.equal(canOpenPayload({ payloadId: 12 }, undefined), false)
  assert.equal(canOpenPayload({ payloadId: null }, 'OWNER'), false)
  assert.equal(canOpenPayload(null, 'OWNER'), false)
  assert.equal(canOpenPayload({ payloadId: '12' }, 'OWNER'), false)
})

test('recordListError formats errors honestly (OBS-F1b)', () => {
  assert.equal(recordListError({ status: 403 }), 'You do not have access to this business.')
  assert.equal(recordListError({ status: 400 }), 'The server did not accept the request.')
  assert.equal(recordListError({ status: 400, detail: 'Unsupported value.' }), 'Unsupported value.')
  assert.equal(recordListError({ status: 500, detail: 'Broke' }), 'Broke')
  assert.equal(recordListError(new Error('boom')), 'boom')
  assert.equal(recordListError(null), 'The list could not be loaded.')
})

test('source checks: records.js (OBS-F1b)', () => {
  const code = fs.readFileSync(path.join(process.cwd(), 'src/lib/observability/records.js'), 'utf8')
  assert.ok(!code.includes('@/'), 'records.js must not import via @/')
  assert.ok(!code.includes('window'), 'records.js must not reference window')
  assert.ok(!code.includes('fetch'), 'records.js must not reference fetch')

  const importMatches = code.match(/import\s+[\s\S]*?from\s+['"][^'"]+['"]/g) || []
  assert.equal(importMatches.length, 2, 'records.js must have exactly two import statements')
})

test('source checks: IntegrationRecordLists.js (OBS-F1b)', () => {
  const filePath = path.join(process.cwd(), 'src/components/IntegrationRecordLists.js')
  assert.ok(fs.existsSync(filePath), 'IntegrationRecordLists.js must exist')
  const code = fs.readFileSync(filePath, 'utf8')

  assert.ok(code.trim().startsWith("'use client'"), "Must start with 'use client'")
  assert.ok(code.includes('export function FailedRecordsList'), 'Must export FailedRecordsList')
  assert.ok(code.includes('export function WebhooksList'), 'Must export WebhooksList')
  assert.ok(code.includes('@/lib/observability/records'), 'Must import from records lib')
  assert.ok(code.includes('@/lib/clientApi'), 'Must import clientApi')
  assert.ok(code.includes('@/components/ui'), 'Must import from ui')
  assert.ok(code.includes('./PayloadDiagnosticDrawer'), 'Must import PayloadDiagnosticDrawer')

  assert.ok(code.includes('recordListPath('), 'Must call recordListPath')
  assert.ok(code.includes('normalizeRecordPage('), 'Must call normalizeRecordPage')
  assert.ok(code.includes('canOpenPayload('), 'Must call canOpenPayload')
  assert.ok(code.includes('<PayloadDiagnosticDrawer'), 'Must mount PayloadDiagnosticDrawer')

  const requiredTexts = [
    'Failed records',
    'Inbound webhooks',
    'View payload',
    'Managers only',
    'No payload stored',
    'All statuses',
    'Refresh',
    'The list could not be loaded',
    'Try again',
    'No failed records',
    'No webhook deliveries',
    'Opening a payload is limited to owners and managers and is recorded in the audit log.',
    'aria-live="polite"',
  ]
  for (const text of requiredTexts) {
    assert.ok(code.includes(text), `Must contain text: ${text}`)
  }

  const clientApiCalls = code.match(/\bclientApi\s*\(/g) || []
  assert.equal(clientApiCalls.length, 1, 'Must contain exactly one clientApi call')

  const forbiddenStrings = [
    'diagnostic_payload',
    'JSON.stringify',
    'localStorage',
    'clipboard',
    'dangerouslySetInnerHTML',
    'payload_id',
  ]
  for (const str of forbiddenStrings) {
    assert.ok(!code.includes(str), `Must not contain ${str}`)
  }

  assert.ok(!/\bopen=\{/.test(code), 'Must not use open={')
  assert.ok(!/<Banner[^>]*\btone=/.test(code), 'Banner must not use tone=')
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(code), 'Must have no raw hex colors')

  const forbiddenClasses = ['text-caption', 'text-muted', 'text-secondary', 'stack-xs', 'stack-md']
  for (const cls of forbiddenClasses) {
    const rx = new RegExp('className=["\'][^"\']*\\b' + cls + '\\b[^"\']*["\']')
    assert.ok(!rx.test(code), `Must not use forbidden class: ${cls}`)
  }
})

test('source checks: Admin.js integration (OBS-F1b)', () => {
  const code = fs.readFileSync(path.join(process.cwd(), 'src/components/Admin.js'), 'utf8')
  assert.ok(code.includes('FailedRecordsList'), 'Admin.js must reference FailedRecordsList')
  assert.ok(code.includes('WebhooksList'), 'Admin.js must reference WebhooksList')
  assert.ok(code.includes('./IntegrationRecordLists'), 'Admin.js must import from IntegrationRecordLists')
  assert.ok(code.includes("integrationsSubTab === 'failed-records'"), 'Admin.js must handle failed-records')
  assert.ok(code.includes("integrationsSubTab === 'webhooks'"), 'Admin.js must handle webhooks')
  assert.ok(
    !code.includes('No failed ingestion records'),
    'Admin.js must no longer contain No failed ingestion records',
  )
  assert.ok(
    !code.includes('No inbound webhook traffic'),
    'Admin.js must no longer contain No inbound webhook traffic',
  )
})
