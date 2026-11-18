import { test, expect } from '@playwright/test'

test('manager can inspect canonical, external, and linked identities', async ({ page }) => {
  test.skip(!process.env.BIZORA_E2E_USERNAME || !process.env.BIZORA_E2E_PASSWORD)
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

  await expect(page.getByRole('heading', { name: 'Administration & Controls' })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: 'Entity Type', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: /customer/i }).first()).toBeVisible()
  await page.getByRole('button', { name: /^External \(/ }).click()
  await expect(page.getByRole('table')).toBeVisible()
  await page.getByRole('button', { name: /^Links \(/ }).click()
  await expect(page.getByRole('table')).toBeVisible()
  const response = await page.request.get(`/api/backend/businesses/${businessId}/identity/links`)
  expect(response.status()).toBe(200)
  expect((await response.json()).results.length).toBeGreaterThan(0)
})
