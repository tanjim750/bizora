import { test, expect } from '@playwright/test'

const username = process.env.BIZORA_E2E_USERNAME
const password = process.env.BIZORA_E2E_PASSWORD
const connectionId = process.env.BIZORA_E2E_CONNECTION_ID
const candidateId = process.env.BIZORA_E2E_PRODUCT_ID

test('manager assesses a shared SKU and records an evidenced source mapping', async ({ page }) => {
  test.skip(
    !username || !password || !connectionId || !candidateId,
    'Use an isolated business with a manager, source connection, and product candidate.',
  )
  const externalId = `browser-review-${crypto.randomUUID()}`
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await page.locator('.workspace-card').first().click()
  await page.getByRole('link', { name: 'Products', exact: true }).click()
  await page.getByLabel('Name', { exact: true }).fill('Source Tea')
  await page.getByLabel('SKU', { exact: true }).fill('TEA')
  await page.getByLabel('Connection ID for a source product').fill(connectionId)
  await page.getByLabel('External product ID').fill(externalId)
  await page.getByRole('button', { name: 'Assess product', exact: true }).click()
  await expect(page.getByText('A shared SKU is not proof of identity.')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Inspect product record' })).toBeVisible()
  await page.getByLabel('Canonical product').selectOption(candidateId)
  await page.getByLabel('Evidence for this decision').fill('Verified supplier catalog and SKU.')
  await page.getByRole('checkbox', { name: /I compared the source product/ }).check()
  await page.getByRole('button', { name: 'Save reviewed mapping' }).click()
  await expect(page.getByText('Reviewed source mapping saved internally.')).toBeVisible()
  const businessId = new URL(page.url()).pathname.split('/')[2]
  const response = await page.request.get(
    `/api/backend/businesses/${businessId}/product-references?connection_id=${connectionId}&external_id=${encodeURIComponent(externalId)}`,
  )
  expect(response.ok()).toBeTruthy()
  const rows = (await response.json()).results
  expect(
    rows.some((row) => row.external_product_id === externalId && row.product === Number(candidateId)),
  ).toBe(true)
})
