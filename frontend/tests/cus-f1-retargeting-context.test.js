import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import {
  retargetingPath,
  safePagePath,
  normalizeRetargeting,
  isEmptyRetargeting,
  truncationNote,
  describeRetargetingError,
} from '../src/lib/customers/retargeting.js'

test('retargetingPath builds valid path and validates IDs (CUS-F1)', () => {
  assert.equal(retargetingPath(1, 12), 'businesses/1/customers/12/retargeting-context')

  const badCustomerIds = [0, -1, '1.5', true, '', null, undefined, 'abc']
  for (const cid of badCustomerIds) {
    assert.throws(() => retargetingPath(1, cid), /Invalid customer ID/)
  }

  assert.throws(() => retargetingPath(0, 12), /Invalid business ID/)
})

test('safePagePath extracts pathname only and handles edge cases (CUS-F1)', () => {
  assert.equal(safePagePath('https://shop.example/a/b?token=1#x'), '/a/b')
  assert.equal(safePagePath('/products/shoe?utm=1'), '/products/shoe')
  assert.equal(safePagePath('/'), '/')
  assert.equal(safePagePath(''), '')
  assert.equal(safePagePath(null), '')
  assert.equal(safePagePath(42), '')
  assert.equal(safePagePath('   '), '')
})

test('normalizeRetargeting handles full contract example, whitelisting, and junk (CUS-F1)', () => {
  // Junk inputs return null
  assert.equal(normalizeRetargeting(null), null)
  assert.equal(normalizeRetargeting([]), null)
  assert.equal(normalizeRetargeting({}), null)
  assert.equal(normalizeRetargeting({ customer_id: 0 }), null)
  assert.equal(normalizeRetargeting({ customer_id: 'bad' }), null)

  const fullData = {
    customer_id: 101,
    kind: 'retargeting_context',
    sessions: {
      count: 120,
      truncated: true,
      results: [
        {
          id: 1,
          started_at: '2026-11-01T10:00:00Z',
          duration_seconds: 120,
          traffic_source: 'google',
          traffic_medium: 'cpc',
          utm_campaign: 'winter_sale',
          device_type: 'mobile',
          country: 'BD',
          is_converted: true,
          landing_page_url: 'https://shop.example/winter?promo=123',
          properties: { secret: 'leak' },
          metadata: { ip: '1.2.3.4' },
          page_title: 'Winter Sale',
          visitor_key: 'vk_999',
        },
        {
          id: 'invalid-dropped',
          started_at: '2026-11-01T11:00:00Z',
        },
      ],
    },
    events: {
      count: 2,
      truncated: false,
      results: [
        {
          id: 11,
          event_type: 'VIEW_PRODUCT',
          occurred_at: '2026-11-01T10:05:00Z',
          page_url: 'https://shop.example/product/shoe?utm_source=fb',
          event_value: '250.50',
          currency: 'BDT',
          product: 45,
          order: 99,
          properties: { private: true },
        },
      ],
    },
    conversions: {
      count: 1,
      truncated: false,
      results: [
        {
          id: 21,
          conversion_type: 'PURCHASE',
          converted_at: '2026-11-01T10:30:00Z',
          conversion_value: 1200,
          currency: 'BDT',
          attribution_type: 'LAST_CLICK',
          campaign: 8,
          order: 99,
          metadata: { tracking: 'x' },
        },
      ],
    },
    audience_recommendation: {
      status: 'unavailable',
      owner: 'Business Intelligence / AI Intelligence',
      reason: 'No audience recommendation computed.',
    },
  }

  const norm = normalizeRetargeting(fullData)
  assert.ok(norm)
  assert.equal(norm.customerId, 101)
  assert.equal(norm.kind, 'retargeting_context')
  assert.equal(norm.sessions.count, 120)
  assert.equal(norm.sessions.truncated, true)
  assert.equal(norm.sessions.rows.length, 1)

  // Assert whitelist keys exactly for session row
  assert.deepEqual(norm.sessions.rows[0], {
    id: 1,
    startedAt: '2026-11-01T10:00:00Z',
    durationSeconds: 120,
    trafficSource: 'google',
    trafficMedium: 'cpc',
    utmCampaign: 'winter_sale',
    deviceType: 'mobile',
    country: 'BD',
    isConverted: true,
    landingPath: '/winter',
  })

  // Assert whitelist keys exactly for event row
  assert.deepEqual(norm.events.rows[0], {
    id: 11,
    eventType: 'VIEW_PRODUCT',
    occurredAt: '2026-11-01T10:05:00Z',
    pagePath: '/product/shoe',
    eventValue: 250.5,
    currency: 'BDT',
    productId: 45,
    orderId: 99,
  })

  // Assert whitelist keys exactly for conversion row
  assert.deepEqual(norm.conversions.rows[0], {
    id: 21,
    conversionType: 'PURCHASE',
    convertedAt: '2026-11-01T10:30:00Z',
    conversionValue: 1200,
    currency: 'BDT',
    attributionType: 'LAST_CLICK',
    campaignId: 8,
    orderId: 99,
  })

  assert.deepEqual(norm.audience, {
    status: 'UNAVAILABLE',
    owner: 'Business Intelligence / AI Intelligence',
    reason: 'No audience recommendation computed.',
  })

  // Missing audience recommendation defaults
  const noAudience = normalizeRetargeting({ customer_id: 5 })
  assert.deepEqual(noAudience.audience, {
    status: 'UNAVAILABLE',
    owner: 'Business Intelligence / AI Intelligence',
    reason: '',
  })
  assert.equal(noAudience.sessions.count, 0)
  assert.equal(noAudience.events.count, 0)
  assert.equal(noAudience.conversions.count, 0)
})

test('isEmptyRetargeting correctly evaluates counts (CUS-F1)', () => {
  assert.equal(isEmptyRetargeting(null), false)
  assert.equal(
    isEmptyRetargeting({
      sessions: { count: 0 },
      events: { count: 0 },
      conversions: { count: 0 },
    }),
    true,
  )
  assert.equal(
    isEmptyRetargeting({
      sessions: { count: 1 },
      events: { count: 0 },
      conversions: { count: 0 },
    }),
    false,
  )
  // view with count 5 and no rows is not empty
  assert.equal(
    isEmptyRetargeting({
      sessions: { count: 5, rows: [] },
      events: { count: 0, rows: [] },
      conversions: { count: 0, rows: [] },
    }),
    false,
  )
})

test('truncationNote returns formatted note only when truncated (CUS-F1)', () => {
  assert.equal(truncationNote({ truncated: false, count: 10, rows: [1, 2] }, 'sessions'), '')
  assert.equal(
    truncationNote({ truncated: true, count: 120, rows: new Array(50).fill(1) }, 'sessions'),
    'Showing the first 50 of 120 sessions, oldest first.',
  )
})

test('describeRetargetingError maps errors correctly (CUS-F1)', () => {
  assert.equal(describeRetargetingError(null), 'Observed signals could not be loaded.')
  assert.equal(
    describeRetargetingError({ status: 400, code: 'INVALID_RELATION' }),
    'This customer was not found in this business.',
  )
  assert.equal(
    describeRetargetingError({ status: 400, code: 'OTHER_ERROR', detail: 'Invalid request' }),
    'Invalid request',
  )
  assert.equal(describeRetargetingError({ status: 403 }), 'Your role cannot view this information.')
  assert.equal(
    describeRetargetingError({ status: 404 }),
    'This business was not found, or you do not have access to it.',
  )
  assert.equal(describeRetargetingError({ status: 500, detail: 'Server exploded' }), 'Server exploded')
  assert.equal(describeRetargetingError({ status: 500 }), 'Observed signals could not be loaded.')
})

test('source checks: lib, RetargetingContext.js, and Customers.js (CUS-F1)', () => {
  const libFile = path.resolve('src/lib/customers/retargeting.js')
  const compFile = path.resolve('src/components/RetargetingContext.js')
  const custFile = path.resolve('src/components/Customers.js')
  const uiIndexFile = path.resolve('src/components/ui/index.js')

  const libCode = fs.readFileSync(libFile, 'utf8')
  assert.ok(!libCode.includes('@/'), 'lib must not contain @/ imports')
  assert.ok(!libCode.includes('window'), 'lib must not contain window')
  assert.ok(!libCode.includes('fetch'), 'lib must not contain fetch')
  assert.ok(
    libCode.includes("import { businessApiPath } from '../catalog.js'"),
    'lib must import businessApiPath from ../catalog.js',
  )

  const compCode = fs.readFileSync(compFile, 'utf8')
  assert.ok(compCode.startsWith("'use client'"), "component must start with 'use client'")
  assert.ok(compCode.includes("from '@/lib/customers/retargeting'"))
  assert.ok(compCode.includes("from '@/lib/clientApi'"))
  assert.ok(compCode.includes("from '@/components/ui'"))

  // Check UI imports against ui/index.js exports
  const uiIndexCode = fs.readFileSync(uiIndexFile, 'utf8')
  const uiImportMatch = compCode.match(/import\s*\{([^}]+)\}\s*from\s*['"]@\/components\/ui['"]/)
  assert.ok(uiImportMatch, 'component must import from @/components/ui')
  const importedComponents = uiImportMatch[1]
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  for (const compName of importedComponents) {
    assert.ok(
      uiIndexCode.includes(`export { ${compName} }`) ||
        uiIndexCode.includes(`export { ${compName},`) ||
        uiIndexCode.includes(`, ${compName} }`),
      `UI export for ${compName} must exist in @/components/ui`,
    )
  }

  // Required tokens & words
  const requiredWords = [
    'retargetingPath',
    'normalizeRetargeting',
    'isEmptyRetargeting',
    'truncationNote',
    'describeRetargetingError',
    'UnavailableState',
    'Observed signals only',
    'No observed signals for this customer',
    'Audience recommendation not available',
    'Website sessions',
    'Website events',
    'Campaign conversions',
    'Loading observed signals',
    'aria-live="polite"',
  ]
  for (const word of requiredWords) {
    assert.ok(compCode.includes(word), `RetargetingContext must include "${word}"`)
  }

  // Forbidden words & patterns in RetargetingContext
  const forbiddenPatterns = [
    'properties',
    'metadata',
    'page_title',
    'visitor_key',
    'JSON.stringify',
    'tone=',
    /#[0-9a-fA-F]{3,6}/,
    /\d+px/,
  ]
  for (const pat of forbiddenPatterns) {
    if (typeof pat === 'string') {
      assert.ok(!compCode.includes(pat), `RetargetingContext must not include "${pat}"`)
    } else {
      assert.ok(!pat.test(compCode), `RetargetingContext must not match ${pat}`)
    }
  }

  // Customers.js integration checks
  const custCode = fs.readFileSync(custFile, 'utf8')
  assert.ok(custCode.includes("import RetargetingContext from './RetargetingContext'"))
  assert.ok(custCode.includes("id: 'retargeting'"))
  assert.ok(custCode.includes('Retargeting Signals'))
  assert.ok(custCode.includes("active360SubTab === 'retargeting'"))
  assert.ok(custCode.includes('<RetargetingContext'))
  assert.ok(custCode.includes('customerId={selectedCustomer.id}'))
})
