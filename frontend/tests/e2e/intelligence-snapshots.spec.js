import { test, expect } from '@playwright/test'

const password = process.env.BIZORA_E2E_PASSWORD

async function signIn(page, username) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await page.getByRole('link', { name: /Open workspace for/ }).first().click()
  await expect(page).toHaveURL(/\/business\/\d+\/overview$/)
  return new URL(page.url()).pathname.split('/')[2]
}

test('manager creates and opens a whole-business graph snapshot', async ({ page }) => {
  test.skip(!password || !process.env.BIZORA_E2E_USERNAME, 'Set credentials for a local manager fixture.')

  const businessId = await signIn(page, process.env.BIZORA_E2E_USERNAME)
  await page.goto(`/business/${businessId}/intelligence/graph`)
  await page.getByRole('tab', { name: 'Snapshots' }).click()
  await expect(page.getByRole('heading', { name: 'Saved snapshots' })).toBeVisible()
  await page.getByRole('button', { name: 'Create snapshot' }).click()

  const name = `Browser snapshot ${Date.now()}`
  await page.getByLabel('Name').fill(name)
  await page.getByRole('dialog').getByRole('button', { name: 'Create snapshot' }).click()

  const snapshotRow = page.getByRole('row').filter({ hasText: name })
  await expect(snapshotRow).toBeVisible()
  await snapshotRow.getByRole('button', { name: `Open snapshot ${name}` }).click()
  await expect(page.getByRole('dialog', { name })).toBeVisible()
  await expect(page.getByText(/This is a stored copy taken on/)).toBeVisible()

  const response = await page.request.get(`/api/backend/businesses/${businessId}/graph/snapshots/`)
  expect(response.status()).toBe(200)
  expect((await response.json()).some((snapshot) => snapshot.name === name)).toBe(true)
})

test('viewer can browse snapshots but does not see snapshot creation controls', async ({ page }) => {
  test.skip(
    !password || !process.env.BIZORA_E2E_VIEWER_USERNAME,
    'Set credentials for a local viewer fixture.',
  )

  const businessId = await signIn(page, process.env.BIZORA_E2E_VIEWER_USERNAME)
  await page.goto(`/business/${businessId}/intelligence/graph`)
  await page.getByRole('tab', { name: 'Snapshots' }).click()
  await expect(page.getByRole('heading', { name: 'Saved snapshots' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Create snapshot' })).toHaveCount(0)
})
