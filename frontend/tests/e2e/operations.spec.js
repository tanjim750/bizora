import { test, expect } from '@playwright/test'

const username = process.env.BIZORA_E2E_USERNAME
const password = process.env.BIZORA_E2E_PASSWORD
const connectionId = process.env.BIZORA_E2E_CONNECTION_ID

test('refund, callback, and outbound preparation use the mounted Django contracts', async ({ page }) => {
  test.skip(!username || !password || !connectionId, 'Use an isolated local writer and source connection.')
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.locator('.workspace-card').first().click()
  await expect(page).toHaveURL(/\/business\/\d+\/overview$/)
  const businessId = new URL(page.url()).pathname.split('/')[2]
  const csrf = (await page.context().cookies()).find((cookie) => cookie.name === 'csrftoken')?.value
  expect(csrf).toBeTruthy()
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
  await page.locator('summary').filter({ hasText: 'Record refund request' }).click()
  await page.getByLabel('Amount *').fill('2.50')
  await page.getByLabel('Reason *').last().fill('Customer requested partial refund')
  await page.getByRole('button', { name: 'Record refund request' }).click()
  await expect(page.getByText('Internal change saved.')).toBeVisible()
  const refunds = await (await page.request.get(`${base}/refunds?payment=${payment.id}`)).json()
  expect(refunds.results.some((row) => row.payment === payment.id && Number(row.amount) === 2.5)).toBe(true)

  const call = await post(
    'calls',
    {
      customer: customer.id,
      external_call_id: `call-${unique}`,
      direction: 'OUTGOING',
      receiver_number: '01712345678',
      status: 'INITIATED',
    },
    true,
  )
  await page.goto(`/business/${businessId}/records/calls/${call.id}`)
  await page.locator('summary').filter({ hasText: 'Request callback' }).click()
  await page.locator('#callback-reason').fill('Follow up on the order')
  await page.getByRole('button', { name: 'Request callback' }).click()
  await expect(page.getByText('Internal change saved.')).toBeVisible()
  const callbacks = await (await page.request.get(`${base}/callbacks?customer=${customer.id}`)).json()
  const callback = callbacks.results.find((row) => row.customer === customer.id)
  expect(callback).toBeTruthy()
  await page.goto(`/business/${businessId}/records/callbacks/${callback.id}`)
  await page.locator('summary').filter({ hasText: 'Schedule callback' }).click()
  await page
    .getByLabel('Schedule at (ISO time with offset) *')
    .fill(new Date(Date.now() + 86_400_000).toISOString())
  await page.getByRole('button', { name: 'Schedule callback' }).click()
  await expect(page.getByText('Internal change saved.')).toBeVisible()

  await page.goto(`/business/${businessId}/records/calls/${call.id}`)
  await page.locator('summary').filter({ hasText: 'Prepare call request' }).click()
  await page.getByRole('button', { name: 'Prepare call request' }).click()
  await expect(page.getByText('Request prepared; execution remains unavailable.')).toBeVisible()
  const freshCall = await (await page.request.get(`${base}/calls/${call.id}`)).json()
  expect(freshCall.record.status).toBe('INITIATED')

  const campaign = await post(
    'campaigns',
    { external_campaign_id: `campaign-${unique}`, name: `Campaign ${unique}`, platform: 'META' },
    true,
  )
  await page.goto(`/business/${businessId}/marketing`)
  await page.getByLabel('Platform').fill('META')
  await page.getByRole('button', { name: 'Apply filters' }).click()
  await expect(page).toHaveURL(/platform=META/)
  await expect(page.getByRole('link', { name: 'Open record' }).first()).toHaveAttribute(
    'href',
    `/business/${businessId}/records/campaigns/${campaign.id}`,
  )

  await page.goto(`/business/${businessId}/contracts`)
  for (const owner of ['integrations', 'bi', 'graph', 'ai', 'memory', 'configuration', 'monitoring']) {
    await page.getByLabel('Service owner').selectOption(owner)
    if (owner === 'integrations') {
      await page.locator('#contract-operation').selectOption('CALL_INITIATE')
      await expect(page.locator('#contract-entity_type')).toHaveValue('CALL')
      await page.locator('#contract-entity_id').fill(String(call.id))
    } else if (['bi', 'graph', 'ai'].includes(owner)) {
      await page.locator('#contract-entity_type').fill('CALL')
      await page.locator('#contract-entity_id').fill(String(call.id))
    } else if (owner === 'memory') {
      await page.locator('#contract-query').fill('Refund policy')
    } else if (owner === 'configuration') {
      await page.locator('#contract-policy_key').fill('refund_policy')
    } else {
      await page.locator('#contract-resource').fill('calls')
    }
    await page.getByRole('button', { name: 'Check contract' }).click()
    await expect(page.locator('.plan-result')).toBeVisible()
    await expect(page.locator('.form-error')).toHaveCount(0)
  }
})
