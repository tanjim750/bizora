import { createHmac, randomUUID } from 'node:crypto'
import { test, expect } from '@playwright/test'

test('signed Steadfast webhook updates the intended shipment once', async ({ page }) => {
  const username = process.env.BIZORA_E2E_USERNAME
  const password = process.env.BIZORA_E2E_PASSWORD
  const connectionId = process.env.BIZORA_E2E_STEADFAST_CONNECTION_ID
  const secret = process.env.BIZORA_E2E_STEADFAST_WEBHOOK_SECRET
  test.skip(
    !username || !password || !connectionId || !secret,
    'Use an isolated signed Steadfast connection.',
  )

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
  await page.goto(`/business/${businessId}/admin/integrations`)
  await expect(page.getByRole('cell', { name: 'Steadfast', exact: true })).toBeVisible()

  const base = `/api/backend/businesses/${businessId}`
  const orders = await (await page.request.get(`${base}/orders`)).json()
  const orderId = orders.results[0].id
  const externalId = `browser-${randomUUID()}`
  const trackingCode = `TRACK-${randomUUID()}`
  const csrf = (await page.context().cookies()).find((cookie) => cookie.name === 'csrftoken')?.value
  const created = await page.request.post(`${base}/shipments`, {
    headers: { 'X-CSRFToken': csrf, 'Idempotency-Key': `browser-${randomUUID()}` },
    data: {
      connection_id: Number(connectionId),
      data: {
        order: orderId,
        external_shipment_id: externalId,
        tracking_code: trackingCode,
        provider: 'Steadfast',
        status: 'SUBMITTED',
      },
    },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const shipmentId = (await created.json()).id
  const eventTime = new Date().toISOString()
  const djangoOrigin = process.env.BIZORA_E2E_DJANGO_URL || 'http://127.0.0.1:8000'
  const webhookUrl = `${djangoOrigin}/api/businesses/${businessId}/integrations/steadfast/${connectionId}/webhook/`

  async function send(consignmentId, status, updatedAt) {
    const body = JSON.stringify({
      notification_type: 'delivery_status',
      consignment_id: consignmentId,
      tracking_code: trackingCode,
      status,
      updated_at: updatedAt,
      delivery_charge: 75,
    })
    const signature = createHmac('sha256', secret).update(body).digest('hex')
    return page.request.post(webhookUrl, {
      data: body,
      headers: { 'Content-Type': 'application/json', 'X-Steadfast-Signature': signature },
    })
  }

  const first = await send(externalId, 'delivered', eventTime)
  expect(first.status(), await first.text()).toBe(200)
  expect((await first.json()).updated).toBe(true)
  const stale = await send(externalId, 'in_transit', new Date(Date.parse(eventTime) - 60_000).toISOString())
  expect(stale.status()).toBe(200)
  expect((await stale.json()).updated).toBe(false)
  const conflict = await send(`other-${externalId}`, 'returned', new Date().toISOString())
  expect(conflict.status()).toBe(400)

  const detail = await (await page.request.get(`${base}/shipments/${shipmentId}`)).json()
  const shipment = detail.record || detail
  expect(shipment.status).toBe('DELIVERED')
  expect(Number(shipment.delivery_charge)).toBe(75)
  expect(Date.parse(shipment.delivered_at)).toBe(Date.parse(eventTime))
})
