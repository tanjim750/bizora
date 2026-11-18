import { test, expect } from '@playwright/test'

async function openIdentity(page) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(process.env.BIZORA_E2E_USERNAME)
  await page.getByLabel('Password').fill(process.env.BIZORA_E2E_PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page
    .getByRole('link', { name: /Open workspace for/ })
    .first()
    .click()
  await expect(page).toHaveURL(/\/business\/\d+\/overview$/)
  const businessId = new URL(page.url()).pathname.split('/')[2]
  await page.goto(`/business/${businessId}/admin/identity`)
  return businessId
}

test.beforeEach(() => {
  test.skip(
    !process.env.BIZORA_E2E_PASSWORD ||
      !process.env.BIZORA_E2E_MERGE_CANDIDATE_ID ||
      !process.env.BIZORA_E2E_CONFLICT_ID,
    'Use the isolated full-stack runner identity fixtures.',
  )
})

test('manager conflict review persists the decision and audit reason', async ({ page }) => {
  const businessId = await openIdentity(page)
  await page.getByRole('button', { name: /^Conflicts \(/ }).click()
  await page.getByRole('button', { name: 'Review Conflict', exact: true }).first().click()
  await page.getByLabel('Resolution Action').selectOption('RESOLVED')
  await page.getByLabel('Resolution Reason').fill('Browser tester verified the contact evidence.')
  const submitted = page.waitForResponse(
    (response) => response.request().method() === 'POST' && response.url().includes('/identity/'),
  )
  await page.getByRole('button', { name: 'Submit Resolution' }).click()
  expect((await submitted).status()).toBe(200)
  await expect(page.getByRole('dialog')).toHaveCount(0)
  const result = await page.request.get(`/api/backend/businesses/${businessId}/identity/conflicts/`)
  expect(result.status()).toBe(200)
  const row = (await result.json()).results.find(
    (item) => String(item.id) === process.env.BIZORA_E2E_CONFLICT_ID,
  )
  expect(row.status).toBe('RESOLVED')
  expect(row.resolution_note).toBe('Browser tester verified the contact evidence.')
})

test('manager merge review persists approval without executing a merge', async ({ page }) => {
  const businessId = await openIdentity(page)
  await page.getByRole('button', { name: /^Merge Candidates \(/ }).click()
  await page.getByRole('button', { name: 'Review', exact: true }).first().click()
  await page.getByLabel('Review Decision').selectOption('APPROVED')
  await page.getByLabel('Manager Decision Reason').fill('Browser tester approved the review only.')
  const submitted = page.waitForResponse(
    (response) => response.request().method() === 'POST' && response.url().includes('/identity/'),
  )
  await page.getByRole('button', { name: 'Record Decision' }).click()
  expect((await submitted).status()).toBe(200)
  await expect(page.getByRole('dialog')).toHaveCount(0)
  const result = await page.request.get(`/api/backend/businesses/${businessId}/identity/merge-candidates/`)
  expect(result.status()).toBe(200)
  const row = (await result.json()).results.find(
    (item) => String(item.id) === process.env.BIZORA_E2E_MERGE_CANDIDATE_ID,
  )
  expect(row.status).toBe('APPROVED')
  const canon = await page.request.get(`/api/backend/businesses/${businessId}/identity/canonical/`)
  expect((await canon.json()).results.every((item) => item.status === 'ACTIVE')).toBe(true)
})

test('merge review lists the canonical identities from the backend', async ({ page }) => {
  const businessId = await openIdentity(page)
  await page.getByRole('button', { name: /^Merge Candidates \(/ }).click()
  const result = await page.request.get(`/api/backend/businesses/${businessId}/identity/merge-candidates/`)
  const row = (await result.json()).results.find(
    (item) => String(item.id) === process.env.BIZORA_E2E_MERGE_CANDIDATE_ID,
  )
  await expect(page.getByRole('cell', { name: `#${row.candidate_identity}`, exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: `#${row.primary_identity}`, exact: true })).toBeVisible()
})

test('failed dry-run displays the error without inventing a plan', async ({ page }) => {
  await openIdentity(page)
  await page.getByRole('button', { name: /^Merge Candidates \(/ }).click()
  await page.route('**/api/backend/**/dry-run', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Audit fixture: merge planner unavailable.' }),
    }),
  )
  await page.getByRole('button', { name: 'Dry-Run Plan', exact: true }).first().click()
  await expect(page.getByText('Audit fixture: merge planner unavailable.')).toBeVisible()
  await expect(page.getByText('Plan Fingerprint:', { exact: true })).toHaveCount(0)
})
