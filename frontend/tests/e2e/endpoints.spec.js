import { test, expect } from '@playwright/test'
import { RESOURCES } from '../../src/lib/catalog.js'

const username = process.env.BIZORA_E2E_USERNAME
const password = process.env.BIZORA_E2E_PASSWORD

test('current workspaces and canonical lists load from Django', async ({ page }) => {
  test.skip(!username || !password, 'Set credentials for an isolated local test business.')
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page
    .getByRole('link', { name: /Open workspace for/ })
    .first()
    .click()
  await expect(page).toHaveURL(/\/business\/\d+\/overview$/)
  const businessId = new URL(page.url()).pathname.split('/')[2]

  for (const workspace of [
    'overview',
    'commerce',
    'support',
    'growth',
    'intelligence',
    'ai',
    'customers',
    'admin',
  ]) {
    await page.goto(`/business/${businessId}/${workspace}`)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(page.locator('.alert-danger')).toHaveCount(0)
  }

  for (const resource of RESOURCES) {
    const response = await page.request.get(`/api/backend/businesses/${businessId}/${resource}`)
    expect(response.status(), `${resource}: ${await response.text()}`).toBe(200)
  }
})
