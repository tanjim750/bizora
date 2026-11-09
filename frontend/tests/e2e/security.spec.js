import { test, expect } from '@playwright/test'

const password = process.env.BIZORA_E2E_PASSWORD
const foreignBusinessId = process.env.BIZORA_E2E_FOREIGN_BUSINESS_ID

async function signIn(page, username) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await page.locator('.workspace-card').first().click()
  await expect(page).toHaveURL(/\/business\/\d+\/overview$/)
  return new URL(page.url()).pathname.split('/')[2]
}

test('viewer sees scoped records but cannot write or open manager screens', async ({ page }) => {
  test.skip(!password || !process.env.BIZORA_E2E_VIEWER_USERNAME || !foreignBusinessId)
  const businessId = await signIn(page, process.env.BIZORA_E2E_VIEWER_USERNAME)
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Identity review' })).toHaveCount(0)
  await page.goto(`/business/${businessId}/identity`)
  await expect(page.getByRole('heading', { name: '404' })).toBeVisible()

  const base = `/api/backend/businesses/${businessId}`
  expect((await page.request.get(`${base}/products`)).status()).toBe(200)
  const token = (await page.context().cookies()).find((cookie) => cookie.name === 'csrftoken')?.value
  const write = await page.request.post(`${base}/products`, {
    headers: { 'X-CSRFToken': token },
    data: { data: { name: 'Unauthorized product' } },
  })
  expect(write.status()).toBe(403)
  expect([403, 404]).toContain(
    (await page.request.get(`/api/backend/businesses/${foreignBusinessId}/products`)).status(),
  )
})

test('session writes require CSRF and logout removes access', async ({ page }) => {
  test.skip(!password || !process.env.BIZORA_E2E_USERNAME || !foreignBusinessId)
  const businessId = await signIn(page, process.env.BIZORA_E2E_USERNAME)
  expect([403, 404]).toContain(
    (await page.request.get(`/api/backend/businesses/${foreignBusinessId}/products`)).status(),
  )
  const noCsrf = await page.request.post('/api/backend/frontend/logout')
  expect(noCsrf.status()).toBe(403)
  const crossOrigin = await page.request.post('/api/backend/frontend/logout', {
    headers: { origin: 'https://attacker.example' },
  })
  expect(crossOrigin.status()).toBe(403)
  const token = (await page.context().cookies()).find((cookie) => cookie.name === 'csrftoken')?.value
  const logout = await page.request.post('/api/backend/frontend/logout', {
    headers: { 'X-CSRFToken': token },
  })
  expect(logout.status()).toBe(200)
  await page.goto(`/business/${businessId}/overview`)
  await expect(page).toHaveURL(/\/login$/)
})
