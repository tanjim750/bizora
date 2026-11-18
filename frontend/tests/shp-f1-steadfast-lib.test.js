import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  STEADFAST_KEY,
  FINAL_SHIPMENT_STATUSES,
  SHIPMENT_LIMITS,
  canManageSteadfast,
  providersPath,
  connectionsPath,
  createShipmentPath,
  refreshShipmentPath,
  steadfastProviderId,
  normalizeConnections,
  connectionAvailability,
  invoiceFor,
  isSteadfastShipment,
  findSteadfastShipment,
  normalizePhone,
  formatCodAmount,
  prefillShipmentForm,
  validateShipmentForm,
  confirmedAbsentBody,
  normalizeCreateResult,
  describeCreateError,
  canRefreshShipment,
  normalizeRefreshResult,
  describeRefresh,
  describeRefreshError,
} from '../src/lib/shipping/steadfast.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('paths and constants (SHP-F1)', () => {
  assert.equal(STEADFAST_KEY, 'steadfast')
  assert.ok(FINAL_SHIPMENT_STATUSES.has('DELIVERED'))
  assert.ok(FINAL_SHIPMENT_STATUSES.has('RETURNED'))
  assert.ok(FINAL_SHIPMENT_STATUSES.has('CANCELLED'))
  assert.deepEqual(SHIPMENT_LIMITS, {
    name: 100,
    address: 490,
    note: 480,
    codMax: 1000000,
  })

  assert.equal(canManageSteadfast('OWNER'), true)
  assert.equal(canManageSteadfast('MANAGER'), true)
  assert.equal(canManageSteadfast('OPERATOR'), false)
  assert.equal(canManageSteadfast('VIEWER'), false)

  assert.equal(providersPath(1), 'businesses/1/observability/providers?page_size=100')
  assert.equal(connectionsPath(1, 3), 'businesses/1/observability/connections?provider=3&page_size=100')
  assert.equal(createShipmentPath(1, 5), 'businesses/1/integrations/steadfast/5/shipments')
  assert.equal(refreshShipmentPath(1, 5, 12), 'businesses/1/integrations/steadfast/5/shipments/12/refresh')

  for (const bad of [0, -1, '1.5', true, '', null, undefined]) {
    assert.throws(() => connectionsPath(1, bad), /Invalid provider ID/)
    assert.throws(() => createShipmentPath(1, bad), /Invalid connection ID/)
    assert.throws(() => refreshShipmentPath(1, bad, 12), /Invalid connection ID/)
    assert.throws(() => refreshShipmentPath(1, 5, bad), /Invalid shipment ID/)
    assert.throws(() => invoiceFor(bad), /Invalid order ID/)
  }
})

test('steadfastProviderId, normalizeConnections, connectionAvailability (SHP-F1)', () => {
  assert.equal(
    steadfastProviderId({
      results: [
        { id: 1, key: 'redx' },
        { id: 2, key: 'STEADFAST' },
      ],
    }),
    2,
  )
  assert.equal(steadfastProviderId([{ id: 3, key: 'steadfast' }]), 3)
  assert.equal(steadfastProviderId([]), null)
  assert.equal(steadfastProviderId({}), null)
  assert.equal(steadfastProviderId(null), null)
  assert.equal(steadfastProviderId([{ key: 'steadfast' }]), null)

  const rawRows = [
    {
      id: 1,
      name: 'Steadfast Live',
      provider: 'steadfast',
      lifecycle_status: 'ACTIVE',
      is_mock: false,
    },
    {
      id: 2,
      name: 'Steadfast Mock',
      provider: 'steadfast',
      lifecycle_status: 'ACTIVE',
      is_mock: true,
    },
    {
      id: 3,
      name: 'Steadfast NoMockFlag',
      provider: 'steadfast',
      lifecycle_status: 'ACTIVE',
    },
    {
      id: 4,
      name: 'Steadfast Disabled',
      provider: 'steadfast',
      lifecycle_status: 'DISABLED',
      is_mock: false,
    },
    {
      name: 'No ID',
      provider: 'steadfast',
      lifecycle_status: 'ACTIVE',
    },
  ]
  const norm = normalizeConnections(rawRows)
  assert.equal(norm.length, 4)
  assert.equal(norm[0].isLive, true)
  assert.equal(norm[1].isLive, false)
  assert.equal(norm[2].isMock, true)
  assert.equal(norm[2].isLive, false)
  assert.equal(norm[3].isLive, false)
  assert.deepEqual(normalizeConnections(null), [])

  // connectionAvailability
  assert.deepEqual(connectionAvailability([]), {
    state: 'none',
    live: [],
    message: 'No Steadfast connection is set up for this business.',
  })
  assert.deepEqual(connectionAvailability(norm), {
    state: 'ready',
    live: [norm[0]],
    message: '',
  })
  assert.deepEqual(connectionAvailability([norm[1], norm[2]]), {
    state: 'mock-only',
    live: [],
    message:
      'Only sample (mock) Steadfast connections exist for this business. Sending a parcel needs a live connection.',
  })
  assert.deepEqual(connectionAvailability([norm[3]]), {
    state: 'disabled-only',
    live: [],
    message: 'The live Steadfast connections of this business are disabled.',
  })
})

test('invoiceFor, shipments, phones, cod amounts (SHP-F1)', () => {
  assert.equal(invoiceFor(7), 'BIZORA-7')
  assert.throws(() => invoiceFor(0), /Invalid order ID/)

  assert.equal(isSteadfastShipment({ provider: 'steadfast' }), true)
  assert.equal(isSteadfastShipment({ provider: '  STEADFAST  ' }), true)
  assert.equal(isSteadfastShipment({ provider: 'pathao' }), false)
  assert.equal(isSteadfastShipment(null), false)

  const shipments = [
    { provider: 'other', id: 1 },
    {
      provider: 'steadfast',
      id: 9,
      status: 'IN_TRANSIT',
      tracking_code: 'TRK123',
      integration_connection: 5,
    },
  ]
  assert.deepEqual(findSteadfastShipment(shipments), {
    id: 9,
    status: 'IN_TRANSIT',
    trackingCode: 'TRK123',
    connectionId: 5,
  })
  assert.equal(findSteadfastShipment([]), null)
  assert.equal(findSteadfastShipment(null), null)

  // normalizePhone
  assert.equal(normalizePhone(' 0171-234 5678 '), '01712345678')
  assert.equal(normalizePhone('+8801712345678'), '01712345678')
  assert.equal(normalizePhone('8801712345678'), '01712345678')
  assert.equal(normalizePhone('12345'), '12345')

  // formatCodAmount
  assert.equal(formatCodAmount(250), '250.00')
  assert.equal(formatCodAmount('99.5'), '99.50')
  assert.equal(formatCodAmount(0), '0.00')
  assert.equal(formatCodAmount(-1), '')
  assert.equal(formatCodAmount('abc'), '')
  assert.equal(formatCodAmount(''), '')
  assert.equal(formatCodAmount(null), '')
})

test('prefillShipmentForm, validateShipmentForm, confirmedAbsentBody (SHP-F1)', () => {
  assert.deepEqual(
    prefillShipmentForm({
      order: { total_amount: 250.5 },
      customer: { display_name: 'Karim Rahman' },
    }),
    {
      recipient_name: 'Karim Rahman',
      recipient_phone: '',
      recipient_address: '',
      cod_amount: '250.50',
      note: '',
    },
  )

  assert.deepEqual(
    prefillShipmentForm({
      order: { total_amount: '100' },
      customer: { first_name: 'First', last_name: 'Last' },
    }),
    {
      recipient_name: 'First Last',
      recipient_phone: '',
      recipient_address: '',
      cod_amount: '100.00',
      note: '',
    },
  )

  const longNameCust = { display_name: 'A'.repeat(150) }
  assert.equal(prefillShipmentForm({ customer: longNameCust }).recipient_name.length, 100)

  // validateShipmentForm valid
  const validForm = {
    recipient_name: '  Karim Rahman  ',
    recipient_phone: ' 01712345678 ',
    recipient_address: '  Dhaka, Bangladesh  ',
    cod_amount: ' 500.5 ',
    note: '  Leave at door  ',
  }
  assert.deepEqual(validateShipmentForm(validForm), {
    ok: true,
    errors: {},
    body: {
      recipient_name: 'Karim Rahman',
      recipient_phone: '01712345678',
      recipient_address: 'Dhaka, Bangladesh',
      cod_amount: '500.50',
      note: 'Leave at door',
    },
  })

  // Valid with empty note
  assert.deepEqual(validateShipmentForm({ ...validForm, note: '   ' }), {
    ok: true,
    errors: {},
    body: {
      recipient_name: 'Karim Rahman',
      recipient_phone: '01712345678',
      recipient_address: 'Dhaka, Bangladesh',
      cod_amount: '500.50',
    },
  })

  // Field validation errors
  assert.equal(
    validateShipmentForm({ ...validForm, recipient_name: '' }).errors.recipient_name,
    'Recipient name is required.',
  )
  assert.equal(
    validateShipmentForm({
      ...validForm,
      recipient_name: 'A'.repeat(101),
    }).errors.recipient_name,
    'Recipient name can be at most 100 characters.',
  )
  assert.equal(
    validateShipmentForm({ ...validForm, recipient_phone: '0123' }).errors.recipient_phone,
    'Phone must be 11 digits starting with 01.',
  )
  assert.equal(
    validateShipmentForm({ ...validForm, recipient_address: '' }).errors.recipient_address,
    'Delivery address is required.',
  )
  assert.equal(
    validateShipmentForm({
      ...validForm,
      recipient_address: 'A'.repeat(491),
    }).errors.recipient_address,
    'Delivery address can be at most 490 characters.',
  )
  assert.equal(
    validateShipmentForm({ ...validForm, cod_amount: '' }).errors.cod_amount,
    'Cash on delivery amount is required. Enter 0 if there is nothing to collect.',
  )
  assert.equal(
    validateShipmentForm({ ...validForm, cod_amount: '1000000.01' }).errors.cod_amount,
    'Cash on delivery amount must be a number from 0 to 1,000,000 with at most 2 decimals.',
  )
  assert.equal(
    validateShipmentForm({ ...validForm, cod_amount: '1,000' }).errors.cod_amount,
    'Cash on delivery amount must be a number from 0 to 1,000,000 with at most 2 decimals.',
  )
  assert.equal(
    validateShipmentForm({ ...validForm, note: 'A'.repeat(481) }).errors.note,
    'Note can be at most 480 characters.',
  )

  // confirmedAbsentBody
  const orig = { recipient_name: 'Karim' }
  const copy = confirmedAbsentBody(orig)
  assert.deepEqual(copy, { recipient_name: 'Karim', confirmed_absent: true })
  assert.equal(orig.confirmed_absent, undefined)
})

test('normalize results and describe errors (SHP-F1)', () => {
  const createData = {
    created: true,
    shipment: {
      id: 10,
      order_id: 5,
      status: 'BOOKED',
      tracking_code: 'TRK99',
      consignment_id: 'CS123',
    },
  }
  assert.deepEqual(normalizeCreateResult(createData), {
    created: true,
    shipment: {
      id: 10,
      orderId: 5,
      status: 'BOOKED',
      trackingCode: 'TRK99',
      consignmentId: 'CS123',
    },
  })
  assert.equal(normalizeCreateResult(null), null)
  assert.equal(normalizeCreateResult({ shipment: { id: 0 } }), null)

  // describeCreateError
  assert.deepEqual(describeCreateError({ status: 409 }, 7), {
    kind: 'uncertain',
    message:
      'Bizora already tried to send this order to Steadfast and does not know whether Steadfast received it. Open the Steadfast portal and look for invoice BIZORA-7. If the parcel is there, it is already booked: do not send again.',
    fieldErrors: {},
  })
  assert.deepEqual(describeCreateError({ status: 409 }, null), {
    kind: 'uncertain',
    message:
      'Bizora already tried to send this order to Steadfast and does not know whether Steadfast received it. Open the Steadfast portal and look for the invoice of this order. If the parcel is there, it is already booked: do not send again.',
    fieldErrors: {},
  })

  assert.deepEqual(describeCreateError({ status: 502, detail: 'Connection timeout' }, 7), {
    kind: 'courier',
    message:
      'Steadfast did not confirm the shipment (Connection timeout). Before sending again, check invoice BIZORA-7 in the Steadfast portal: if it exists, the parcel was already booked.',
    fieldErrors: {},
  })
  assert.deepEqual(describeCreateError({ status: 502, detail: '' }, 7), {
    kind: 'courier',
    message:
      'Steadfast did not confirm the shipment. Before sending again, check invoice BIZORA-7 in the Steadfast portal: if it exists, the parcel was already booked.',
    fieldErrors: {},
  })

  assert.deepEqual(describeCreateError({ status: 403 }), {
    kind: 'forbidden',
    message: 'Only owners and managers can send orders to Steadfast.',
    fieldErrors: {},
  })

  assert.deepEqual(describeCreateError({ status: 404, detail: 'Order not found' }), {
    kind: 'not-found',
    message: 'Order not found',
    fieldErrors: {},
  })

  assert.deepEqual(
    describeCreateError({
      status: 400,
      fieldErrors: { recipient_phone: ['Invalid phone number'] },
    }),
    {
      kind: 'validation',
      message: 'Steadfast rejected some of the shipment details. Correct the marked fields and try again.',
      fieldErrors: { recipient_phone: ['Invalid phone number'] },
    },
  )

  assert.deepEqual(
    describeCreateError({
      status: 400,
      fieldErrors: { other_key: ['Some error'] },
      detail: 'Bad request',
    }),
    {
      kind: 'rejected',
      message: 'Bad request',
      fieldErrors: {},
    },
  )

  assert.deepEqual(describeCreateError(null), {
    kind: 'other',
    message: 'Sending to Steadfast failed.',
    fieldErrors: {},
  })

  // canRefreshShipment
  const validShipment = {
    id: 10,
    provider: 'steadfast',
    integration_connection: 5,
    tracking_code: 'TRK100',
  }
  assert.equal(canRefreshShipment(validShipment, 'MANAGER'), true)
  assert.equal(canRefreshShipment(validShipment, 'OPERATOR'), false)
  assert.equal(canRefreshShipment({ ...validShipment, provider: 'redx' }, 'MANAGER'), false)
  assert.equal(canRefreshShipment({ ...validShipment, integration_connection: null }, 'MANAGER'), false)
  assert.equal(canRefreshShipment({ ...validShipment, tracking_code: '   ' }, 'MANAGER'), false)

  // normalizeRefreshResult
  assert.deepEqual(
    normalizeRefreshResult({
      changed: true,
      shipment: {
        id: 10,
        order_id: 4,
        status: 'DELIVERED',
        tracking_code: 'TRK',
      },
    }),
    {
      changed: true,
      shipment: {
        id: 10,
        orderId: 4,
        status: 'DELIVERED',
        trackingCode: 'TRK',
        consignmentId: '',
      },
    },
  )
  assert.equal(normalizeRefreshResult(null), null)

  // describeRefresh
  assert.deepEqual(
    describeRefresh('in_transit', {
      changed: true,
      shipment: { status: 'DELIVERED' },
    }),
    {
      changed: true,
      status: 'DELIVERED',
      tone: 'success',
      message: 'Status updated from IN_TRANSIT to DELIVERED.',
    },
  )
  assert.deepEqual(
    describeRefresh('', {
      changed: true,
      shipment: { status: 'DELIVERED' },
    }),
    {
      changed: true,
      status: 'DELIVERED',
      tone: 'success',
      message: 'Status updated to DELIVERED.',
    },
  )
  assert.deepEqual(
    describeRefresh('IN_TRANSIT', {
      changed: false,
      shipment: { status: 'IN_TRANSIT' },
    }),
    {
      changed: false,
      status: 'IN_TRANSIT',
      tone: 'info',
      message: 'Checked with Steadfast: no change recorded. Bizora still shows IN_TRANSIT.',
    },
  )
  assert.deepEqual(
    describeRefresh('DELIVERED', {
      changed: false,
      shipment: { status: 'DELIVERED' },
    }),
    {
      changed: false,
      status: 'DELIVERED',
      tone: 'info',
      message:
        'Checked with Steadfast: no change recorded. Bizora still shows DELIVERED. This is a final status; a refresh never changes it.',
    },
  )

  // describeRefreshError
  assert.equal(describeRefreshError({ status: 403 }), 'Only owners and managers can check courier status.')
  assert.equal(
    describeRefreshError({ status: 404 }),
    'This shipment was not found for the Steadfast connection.',
  )
  assert.equal(
    describeRefreshError({ status: 502, detail: 'Gateway timeout' }),
    'Steadfast did not answer (Gateway timeout). Nothing was changed in Bizora.',
  )
  assert.equal(
    describeRefreshError({ status: 502, detail: '' }),
    'Steadfast did not answer. Nothing was changed in Bizora.',
  )
  assert.equal(describeRefreshError({ status: 400, detail: 'Rejected' }), 'Rejected')
  assert.equal(describeRefreshError({ status: 500, detail: 'Server error' }), 'Server error')
  assert.equal(describeRefreshError(null), 'Checking the status failed.')
})

test('source checks of shipping/steadfast.js (SHP-F1)', () => {
  const libPath = path.join(ROOT, 'src/lib/shipping/steadfast.js')
  assert.ok(fs.existsSync(libPath), 'steadfast.js must exist')
  const content = fs.readFileSync(libPath, 'utf8')
  assert.doesNotMatch(content, /@\//)
  assert.doesNotMatch(content, /\bwindow\b/)
  assert.doesNotMatch(content, /\bfetch\b/)
  const imports = content.match(/import\s+[^;]+;/g) || []
  assert.equal(imports.length, 1)
  assert.match(imports[0], /from\s+['"]\.\.\/catalog\.js['"]/)
})
