import { test, expect } from '@playwright/test'

test('authenticated read burst stays scoped and returns without server errors', async ({ page }) => {
  test.skip(!process.env.BIZORA_E2E_USERNAME || !process.env.BIZORA_E2E_PASSWORD)
  await page.goto('/login')
  await page.getByLabel('Username').fill(process.env.BIZORA_E2E_USERNAME)
  await page.getByLabel('Password').fill(process.env.BIZORA_E2E_PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await page.locator('.workspace-card').first().click()
  await expect(page).toHaveURL(/\/business\/\d+\/overview$/)
  const businessId = new URL(page.url()).pathname.split('/')[2]
  const durations = []

  for (let batch = 0; batch < 10; batch++) {
    const statuses = await Promise.all(
      Array.from({ length: 5 }, async (_, index) => {
        const started = performance.now()
        const resource = index % 2 ? 'products' : 'customers'
        const response = await page.request.get(`/api/backend/businesses/${businessId}/${resource}`)
        durations.push(performance.now() - started)
        return response.status()
      }),
    )
    expect(statuses).toEqual([200, 200, 200, 200, 200])
  }

  durations.sort((a, b) => a - b)
  console.log(
    `Local read burst: 50 requests, p50 ${durations[24].toFixed(0)} ms, p95 ${durations[47].toFixed(0)} ms`,
  )
})
