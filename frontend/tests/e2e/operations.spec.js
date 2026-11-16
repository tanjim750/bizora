import { test, expect } from '@playwright/test'

test('manager records a refund through the commerce drawer', async ({ page }) => {
  const username = process.env.BIZORA_E2E_USERNAME
  const password = process.env.BIZORA_E2E_PASSWORD
  const connectionId = process.env.BIZORA_E2E_CONNECTION_ID
  test.skip(!username || !password || !connectionId, 'Use an isolated local writer and source connection.')

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
  const csrf = (await page.context().cookies()).find((cookie) => cookie.name === 'csrftoken')?.value
  const base = `/api/backend/businesses/${businessId}`
  const unique = crypto.randomUUID()

  async function post(resource, data, sourced = false) {
    const response = await page.request.post(`${base}/${resource}`, {
      headers: { 'X-CSRFToken': csrf, 'Idempotency-Key': `browser-${crypto.randomUUID()}` },
      data: { data, ...(sourced ? { connection_id: Number(connectionId) } : {}) },
    })
    expect(response.ok(), `${resource}: ${await response.text()}`).toBeTruthy()
    return response.json()
  }

  const customer = await post('customers', { display_name: `Browser ${unique}` })
  const order = await post(
    'orders',
    {
      external_order_id: `order-${unique}`,
      customer: customer.id,
      items: [{ product_name: 'Tea', quantity: 1, unit_price: '10.00' }],
    },
    true,
  )
  const payment = await post(
    'payments',
    {
      external_payment_id: `payment-${unique}`,
      customer: customer.id,
      order: order.id,
      amount: '10.00',
      status: 'PAID',
    },
    true,
  )

  await page.goto(`/business/${businessId}/records/payments/${payment.id}`)
  await page.getByRole('button', { name: 'Issue Refund' }).click()
  await page.getByLabel('Refund Amount (BDT)').fill('2.50')
  await page.getByRole('button', { name: 'Process Refund (Idempotent)' }).click()
  await expect(page.getByText('Refund recorded in financial ledger. Idempotency key verified.')).toBeVisible()

  const refunds = await (await page.request.get(`${base}/refunds?payment=${payment.id}`)).json()
  expect(refunds.results.some((row) => row.payment === payment.id && Number(row.amount) === 2.5)).toBe(true)
})
