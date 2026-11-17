import test from 'node:test'
import assert from 'node:assert/strict'
import { RESOURCES } from '../src/lib/catalog.js'
import { RESOURCE_CONFIGS, filterQueryParams } from '../src/lib/domain/resources.js'

test('all 32 resources have complete configuration in RESOURCE_CONFIGS', () => {
  assert.equal(RESOURCES.length, 32)
  assert.equal(Object.keys(RESOURCE_CONFIGS).length, 32)

  let searchSupportedCount = 0

  for (const resourceName of RESOURCES) {
    const config = RESOURCE_CONFIGS[resourceName]
    assert.ok(config, `Missing resource configuration for ${resourceName}`)
    assert.equal(config.name, resourceName)
    assert.ok(config.singular)
    assert.ok(config.plural)
    assert.ok(config.titleField)
    assert.ok(config.workspace)
    assert.ok(config.tab)
    assert.ok(Array.isArray(config.columns))
    assert.ok(config.columns.length > 0)
    assert.ok(Array.isArray(config.allowedFilters))

    if (config.supportsSearch) {
      searchSupportedCount++
    }
  }

  // Exactly 14 support q search; 18 return 400 if searched (per docs/frontend-api-reference.md §2.1)
  assert.equal(searchSupportedCount, 14)
  assert.equal(32 - searchSupportedCount, 18)
})

test('filterQueryParams allows only verified query keys per resource', () => {
  // Products: supports q, status, category, sku + common controls
  const productParams = filterQueryParams('products', {
    page: 2,
    page_size: 25,
    q: 'Shampoo',
    status: 'ACTIVE',
    bad_param: 'hack',
    provider: 'meta',
  })
  assert.deepEqual(productParams, {
    page: 2,
    page_size: 25,
    q: 'Shampoo',
    status: 'ACTIVE',
  })

  // Payments: does NOT support q (would return 400 on backend), does not support provider
  const paymentParams = filterQueryParams('payments', {
    q: 'SearchText',
    status: 'PAID',
    payment_method: 'BKASH',
    provider: 'sslcommerz',
  })
  assert.deepEqual(paymentParams, {
    status: 'PAID',
    payment_method: 'BKASH',
  })

  // Campaigns: platform is a field, but NOT an allowed filter; provider is NOT an allowed filter
  const campaignParams = filterQueryParams('campaigns', {
    q: 'Winter Sale',
    status: 'ACTIVE',
    provider: 'META',
    platform: 'META',
  })
  assert.deepEqual(campaignParams, {
    q: 'Winter Sale',
    status: 'ACTIVE',
  })
})
