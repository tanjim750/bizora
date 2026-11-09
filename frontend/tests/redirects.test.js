import test from 'node:test'
import assert from 'node:assert/strict'
import { SECTIONS, RESOURCES } from '../src/lib/catalog.js'
import {
  LEGACY_SECTION_REDIRECTS,
  resolveLegacySectionUrl,
  resolveResourceListUrl,
  resolveRecordDetailUrl,
} from '../src/lib/domain/redirects.js'

test('all SECTIONS map cleanly to a valid workspace and tab in LEGACY_SECTION_REDIRECTS', () => {
  for (const section of SECTIONS) {
    const mapping = LEGACY_SECTION_REDIRECTS[section.key]
    assert.ok(mapping, `Missing redirect mapping for legacy section: ${section.key}`)
    assert.ok(mapping.workspace, `Section ${section.key} has no target workspace`)
    assert.ok(
      ['overview', 'customers', 'commerce', 'support', 'growth', 'intelligence', 'ai', 'admin'].includes(
        mapping.workspace,
      ),
      `Section ${section.key} maps to invalid workspace: ${mapping.workspace}`,
    )
    assert.ok(mapping.tab, `Section ${section.key} has no target tab`)
  }
})

test('resolveLegacySectionUrl produces correct query strings and paths', () => {
  // Inbox -> Support workspace, inbox tab
  const inboxUrl = resolveLegacySectionUrl('1', 'inbox', { q: 'John Doe', page: '2' })
  assert.equal(inboxUrl, '/business/1/support?tab=inbox&q=John+Doe&page=2')

  // Orders -> Commerce workspace, orders tab
  const ordersUrl = resolveLegacySectionUrl('42', 'orders', { status: 'CONFIRMED' })
  assert.equal(ordersUrl, '/business/42/commerce?tab=orders&status=CONFIRMED')

  // Unknown section returns null
  assert.equal(resolveLegacySectionUrl('1', 'unknown_section'), null)
})

test('all 32 RESOURCES resolve to a workspace and tab in resolveResourceListUrl', () => {
  assert.equal(RESOURCES.length, 32)
  for (const resource of RESOURCES) {
    const url = resolveResourceListUrl('1', resource)
    assert.ok(url, `Resource ${resource} failed to resolve list URL`)
    assert.ok(url.startsWith('/business/1/'), `Resource ${resource} generated bad URL: ${url}`)
    assert.ok(url.includes('?tab='), `Resource ${resource} missing ?tab=: ${url}`)
  }
})

test('resolveRecordDetailUrl attaches the open drawer param with resource and ID', () => {
  const orderUrl = resolveRecordDetailUrl('1', 'orders', '1042', { filter: 'active' })
  assert.equal(orderUrl, '/business/1/commerce?tab=orders&open=orders%3A1042&filter=active')

  const customerUrl = resolveRecordDetailUrl('5', 'customers', '99')
  assert.equal(customerUrl, '/business/5/customers?tab=list&open=customers%3A99')

  const paymentUrl = resolveRecordDetailUrl('1', 'payments', '555')
  assert.equal(paymentUrl, '/business/1/commerce?tab=payments&open=payments%3A555')
})
