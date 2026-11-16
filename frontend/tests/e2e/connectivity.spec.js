import { test, expect } from '@playwright/test'

test('paginated API links stay on the frontend and can be followed', async ({ page }) => {
  test.skip(!process.env.BIZORA_E2E_USERNAME || !process.env.BIZORA_E2E_PASSWORD)
  await page.goto('/login')
  await page.getByLabel('Username').fill(process.env.BIZORA_E2E_USERNAME)
  await page.getByLabel('Password').fill(process.env.BIZORA_E2E_PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await page
    .getByRole('link', { name: /Open workspace for/ })
    .first()
    .click()
  await expect(page).toHaveURL(/\/business\/\d+\/overview$/)
  const businessId = new URL(page.url()).pathname.split('/')[2]

  const first = await page.request.get(`/api/backend/businesses/${businessId}/products?page_size=1`)
  expect(first.status()).toBe(200)
  const pageOne = await first.json()
  expect(pageOne.count).toBeGreaterThanOrEqual(2)
  expect(pageOne.results).toHaveLength(1)
  expect(pageOne.next).toMatch(/^\/api\/backend\//)
  expect(new URL(pageOne.next, page.url()).pathname).toBe(`/api/backend/businesses/${businessId}/products/`)

  const second = await page.request.get(pageOne.next)
  expect(second.status()).toBe(200)
  const pageTwo = await second.json()
  expect(pageTwo.results).toHaveLength(1)
  expect(pageTwo.results[0].id).not.toBe(pageOne.results[0].id)
  expect(pageTwo.previous).toMatch(/^\/api\/backend\//)

  await page.goto(`/business/${businessId}/resources/products?page_size=1`)
  await expect(page).toHaveURL(new RegExp(`/business/${businessId}/commerce\\?tab=products`))
  await expect(page.getByRole('table')).toBeVisible()
})
