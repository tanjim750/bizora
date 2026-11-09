import { test, expect } from '@playwright/test'
import { MODULE_VIEWS, RESOURCES, SECTIONS } from '../../src/lib/catalog.js'
import { label } from '../../src/lib/format.js'

const username = process.env.BIZORA_E2E_USERNAME
const password = process.env.BIZORA_E2E_PASSWORD

test('all mounted frontend sections and canonical lists load from Django', async ({ page }) => {
  test.skip(!username || !password, 'Set credentials for an isolated local test business.')
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.locator('.workspace-card').first().click()
  await expect(page).toHaveURL(/\/business\/\d+\/overview$/)
  const businessId = new URL(page.url()).pathname.split('/')[2]

  for (const section of SECTIONS) {
    await page.goto(`/business/${businessId}/${section.key}`)
    await expect(page.getByRole('heading', { name: section.label, exact: true, level: 1 })).toBeVisible()
    await expect(page.locator('.alert-danger')).toHaveCount(0)
  }
  for (const [section, module] of Object.entries(MODULE_VIEWS)) {
    for (const view of module.views) {
      await page.goto(`/business/${businessId}/${section}?view=${encodeURIComponent(view)}`)
      await expect(
        page.getByRole('heading', { name: SECTIONS.find((item) => item.key === section).label, level: 1 }),
      ).toBeVisible()
      await expect(page.locator('.alert-danger')).toHaveCount(0)
    }
  }
  for (const resource of RESOURCES) {
    await page.goto(`/business/${businessId}/resources/${resource}`)
    await expect(page.getByRole('heading', { name: label(resource), exact: true, level: 1 })).toBeVisible()
    await expect(page.locator('.alert-danger')).toHaveCount(0)
    await expect(page.getByRole('table')).toBeVisible()
  }
  if (process.env.BIZORA_E2E_CONNECTION_ID) {
    await page.goto(`/business/${businessId}/observability?view=connections`)
    await page.locator('.disclosure').first().locator('summary').click()
    await page.getByRole('link', { name: 'Open full evidence' }).first().click()
    await expect(page).toHaveURL(/view=connections&record=\d+/)
    await expect(page.getByText('Back to connections')).toBeVisible()
  }
})
