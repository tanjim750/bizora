import { test, expect } from '@playwright/test'

const username = process.env.BIZORA_E2E_USERNAME
const password = process.env.BIZORA_E2E_PASSWORD

test('session login, live overview, and mobile navigation', async ({ page }) => {
  test.skip(
    !username || !password,
    'Set BIZORA_E2E_USERNAME and BIZORA_E2E_PASSWORD for a local test business.',
  )
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  const business = page.locator('.workspace-card').first()
  await expect(business).toBeVisible()
  await business.click()
  await expect(page.getByRole('heading', { name: 'Overview', exact: true })).toBeVisible()
  await expect(page.getByText('Analytics unavailable')).toBeVisible()
  await page.setViewportSize({ width: 320, height: 700 })
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBe(320)
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await expect(page.getByRole('link', { name: 'Customers', exact: true })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Open navigation' })).toHaveAttribute(
    'aria-expanded',
    'false',
  )
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('link', { name: 'Customers', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Customers', exact: true })).toBeVisible()
  await page.setViewportSize({ width: 1440, height: 900 })
  if (await page.getByRole('link', { name: 'Identity review' }).count()) {
    await page.getByRole('link', { name: 'Identity review' }).click()
    await expect(page.getByRole('heading', { name: 'Identity review' })).toBeVisible()
    await page.getByRole('link', { name: 'Service contracts' }).click()
    await expect(page.getByRole('heading', { name: 'Service contracts' })).toBeVisible()
  }
})
