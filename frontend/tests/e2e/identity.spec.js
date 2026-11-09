import { test, expect } from '@playwright/test'

const username = process.env.BIZORA_E2E_USERNAME
const password = process.env.BIZORA_E2E_PASSWORD
const connectionId = process.env.BIZORA_E2E_CONNECTION_ID
const productId = process.env.BIZORA_E2E_PRODUCT_ID

test('manager links source identity to a reviewed canonical product', async ({ page }) => {
  test.skip(
    !username || !password || !connectionId || !productId,
    'Use an isolated manager, source connection, and product.',
  )
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.locator('.workspace-card').first().click()
  await expect(page).toHaveURL(/\/business\/\d+\/overview$/)
  const businessId = new URL(page.url()).pathname.split('/')[2]
  await page.goto(`/business/${businessId}/identity`)

  const canonical = page
    .locator('details')
    .filter({ has: page.locator('summary', { hasText: 'Create or find canonical identity' }) })
  await canonical.locator('summary').click()
  await canonical.getByLabel('Entity Type *').fill('PRODUCT')
  await canonical.getByLabel('Entity Id *').fill(productId)
  await canonical.getByRole('button', { name: 'Create or find canonical identity' }).click()
  await expect(canonical.getByText('Command completed')).toBeVisible()
  const canonicalId = JSON.parse(await canonical.locator('pre').innerText()).id

  const external = page
    .locator('details')
    .filter({ has: page.locator('summary', { hasText: 'Register external identity' }) })
  await external.locator('summary').click()
  await external.getByLabel('Connection Id *').fill(connectionId)
  await external.getByLabel('Entity Type *', { exact: true }).fill('PRODUCT')
  await external.getByLabel('Identity Type *').fill('EXTERNAL_PRODUCT_ID')
  await external.getByLabel('Value *').fill(`source-${crypto.randomUUID()}`)
  await external.getByLabel('External Id *').fill(`source-${crypto.randomUUID()}`)
  await external.getByRole('button', { name: 'Register external identity' }).click()
  await expect(external.getByText('Command completed')).toBeVisible()
  const externalId = JSON.parse(await external.locator('pre').innerText()).result.id

  const link = page
    .locator('details')
    .filter({ has: page.locator('summary', { hasText: /^Link reviewed identity$/ }) })
  await link.locator('summary').click()
  await link.getByLabel('External Identity Id *').fill(String(externalId))
  await link.getByLabel('Canonical Identity Id *').fill(String(canonicalId))
  await link.getByLabel('Reason *').fill('Source ID and supplier catalog checked')
  await link.getByRole('button', { name: 'Link reviewed identity' }).click()
  await expect(link.getByText('Command completed')).toBeVisible()
  const result = JSON.parse(await link.locator('pre').innerText())
  expect(result.status).toBe('RESOLVED')
  const response = await page.request.get(`/api/backend/businesses/${businessId}/identity/links`)
  expect(response.ok()).toBeTruthy()
  expect((await response.json()).results.some((row) => row.external_identity === externalId)).toBe(true)
})
