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
  const business = page.getByRole('link', { name: /Open workspace for/ }).first()
  await expect(business).toBeVisible()
  await business.click()
  await expect(page.getByRole('heading', { name: 'Executive Overview' })).toBeVisible()
  const businessId = new URL(page.url()).pathname.split('/')[2]
  await expect(page.getByRole('heading', { name: 'Authoritative Record Counts' })).toBeVisible()
  await page.getByRole('link', { name: 'Intelligence', exact: true }).first().click()
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await page.goto(`/business/${businessId}/overview`)
  await page.setViewportSize({ width: 320, height: 700 })
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBe(320)
  await page.getByRole('button', { name: 'Open navigation menu' }).click()
  await expect(page.getByRole('link', { name: 'Customers', exact: true })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Open navigation menu' })).toHaveAttribute(
    'aria-expanded',
    'false',
  )
  await page.getByRole('button', { name: 'Open navigation menu' }).click()
  await page.getByRole('link', { name: 'Customers', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Customer Directory & 360' })).toBeVisible()
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.getByRole('link', { name: 'Identity', exact: true }).first().click()
  await expect(page.getByRole('heading', { name: 'Administration & Controls' })).toBeVisible()
})
