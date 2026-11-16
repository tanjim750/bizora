import { test, expect } from '@playwright/test'
import { assessmentPayload, reviewedMapping } from '../../src/lib/productReview.js'

test('manager reviews a shared SKU before linking its source record', async ({ page }) => {
  const username = process.env.BIZORA_E2E_USERNAME
  const password = process.env.BIZORA_E2E_PASSWORD
  const connectionId = process.env.BIZORA_E2E_CONNECTION_ID
  const candidateId = Number(process.env.BIZORA_E2E_PRODUCT_ID)
  test.skip(!username || !password || !connectionId || !candidateId)
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
  await page.goto(`/business/${businessId}/commerce/products`)
  await expect(page.getByRole('heading', { name: 'Catalog Products & Variants' })).toBeVisible()

  const csrf = (await page.context().cookies()).find((cookie) => cookie.name === 'csrftoken')?.value
  const payload = assessmentPayload({
    name: 'Source Tea',
    sku: 'TEA',
    connectionId,
    externalProductId: `browser-review-${crypto.randomUUID()}`,
  })
  const assessmentResponse = await page.request.post(
    `/api/backend/businesses/${businessId}/products/assess/`,
    {
      headers: { 'X-CSRFToken': csrf },
      data: payload,
    },
  )
  expect(assessmentResponse.status(), await assessmentResponse.text()).toBe(200)
  const assessment = await assessmentResponse.json()
  expect(assessment.decision).toBe('REVIEW')
  expect(assessment.candidate_ids).toContain(candidateId)

  const mapping = reviewedMapping(assessment, candidateId, 'Verified supplier catalog and SKU.', payload)
  const saved = await page.request.post(`/api/backend/businesses/${businessId}/product-references`, {
    headers: { 'X-CSRFToken': csrf, 'Idempotency-Key': `browser-${crypto.randomUUID()}` },
    data: mapping,
  })
  expect(saved.ok(), await saved.text()).toBeTruthy()
  const response = await page.request.get(
    `/api/backend/businesses/${businessId}/product-references?connection_id=${connectionId}&external_id=${encodeURIComponent(payload.data.external_reference.external_product_id)}`,
  )
  expect(response.status()).toBe(200)
  expect((await response.json()).results.some((row) => row.product === candidateId)).toBe(true)
})
