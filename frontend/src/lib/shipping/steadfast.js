import { businessApiPath, MANAGER_ROLES } from '../catalog.js'

export const STEADFAST_KEY = 'steadfast'

export const FINAL_SHIPMENT_STATUSES = new Set(['DELIVERED', 'RETURNED', 'CANCELLED'])

export const SHIPMENT_LIMITS = {
  name: 100,
  address: 490,
  note: 480,
  codMax: 1000000,
}

function validatePositiveId(id, thing) {
  if (typeof id === 'boolean' || id === null || id === undefined) {
    throw new Error(`Invalid ${thing} ID`)
  }
  const str = String(id)
  if (!/^[1-9]\d*$/.test(str)) {
    throw new Error(`Invalid ${thing} ID`)
  }
  return str
}

export function canManageSteadfast(role) {
  return MANAGER_ROLES.has(role)
}

export function providersPath(businessId) {
  return `${businessApiPath(businessId, 'observability/providers')}?page_size=100`
}

export function connectionsPath(businessId, providerId) {
  const pId = validatePositiveId(providerId, 'provider')
  return `${businessApiPath(businessId, 'observability/connections')}?provider=${pId}&page_size=100`
}

export function createShipmentPath(businessId, connectionId) {
  const cId = validatePositiveId(connectionId, 'connection')
  return businessApiPath(businessId, `integrations/steadfast/${cId}/shipments`)
}

export function refreshShipmentPath(businessId, connectionId, shipmentId) {
  const cId = validatePositiveId(connectionId, 'connection')
  const sId = validatePositiveId(shipmentId, 'shipment')
  return businessApiPath(businessId, `integrations/steadfast/${cId}/shipments/${sId}/refresh`)
}

export function steadfastProviderId(payload) {
  const rows = Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : []

  for (const row of rows) {
    if (
      String(row?.key ?? '').toLowerCase() === STEADFAST_KEY &&
      row?.id != null &&
      /^[1-9]\d*$/.test(String(row.id))
    ) {
      return Number(row.id)
    }
  }
  return null
}

export function normalizeConnections(payload) {
  const rows = Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : []

  const list = []
  for (const row of rows) {
    if (!row || row.id == null || !/^[1-9]\d*$/.test(String(row.id))) {
      continue
    }
    const id = Number(row.id)
    const name = row.name || row.provider || 'Steadfast connection'
    const provider = String(row.provider ?? '')
    const lifecycleStatus = String(row.lifecycle_status ?? '')
    const isMock = row.is_mock !== false
    const isLive = row.is_mock === false && lifecycleStatus.toUpperCase() !== 'DISABLED'

    list.push({ id, name, provider, lifecycleStatus, isMock, isLive })
  }
  return list
}

export function connectionAvailability(connections) {
  if (!Array.isArray(connections) || connections.length === 0) {
    return {
      state: 'none',
      live: [],
      message: 'No Steadfast connection is set up for this business.',
    }
  }

  const live = connections.filter((c) => c.isLive)
  if (live.length > 0) {
    return { state: 'ready', live, message: '' }
  }

  if (connections.every((c) => c.isMock)) {
    return {
      state: 'mock-only',
      live: [],
      message:
        'Only sample (mock) Steadfast connections exist for this business. Sending a parcel needs a live connection.',
    }
  }

  return {
    state: 'disabled-only',
    live: [],
    message: 'The live Steadfast connections of this business are disabled.',
  }
}

export function invoiceFor(orderId) {
  const oId = validatePositiveId(orderId, 'order')
  return `BIZORA-${oId}`
}

export function isSteadfastShipment(shipment) {
  return (
    String(shipment?.provider ?? '')
      .trim()
      .toLowerCase() === STEADFAST_KEY
  )
}

export function findSteadfastShipment(shipments) {
  if (!Array.isArray(shipments)) return null
  const found = shipments.find(isSteadfastShipment)
  if (!found) return null

  return {
    id: Number(found.id),
    status: String(found.status ?? ''),
    trackingCode: String(found.tracking_code ?? ''),
    connectionId: found.integration_connection != null ? Number(found.integration_connection) : null,
  }
}

export function normalizePhone(value) {
  const clean = String(value ?? '').replace(/[\s-]/g, '')
  if (/^\+?8801\d{9}$/.test(clean)) {
    return clean.replace(/^\+?880/, '0')
  }
  return clean
}

export function formatCodAmount(value) {
  if (value === null || value === undefined || value === '') return ''
  const num = Number(value)
  if (isNaN(num) || !isFinite(num) || num < 0) return ''
  return num.toFixed(2)
}

export function prefillShipmentForm({ order, customer } = {}) {
  let name = ''
  if (customer?.display_name) {
    name = customer.display_name
  } else {
    name = [customer?.first_name, customer?.last_name].filter(Boolean).join(' ')
  }

  return {
    recipient_name: name.slice(0, SHIPMENT_LIMITS.name),
    recipient_phone: '',
    recipient_address: '',
    cod_amount: formatCodAmount(order?.total_amount),
    note: '',
  }
}

export function validateShipmentForm(form) {
  const errors = {}
  const name = String(form?.recipient_name ?? '').trim()
  const rawPhone = String(form?.recipient_phone ?? '')
  const phone = normalizePhone(rawPhone)
  const address = String(form?.recipient_address ?? '').trim()
  const rawCod = String(form?.cod_amount ?? '').trim()
  const note = String(form?.note ?? '').trim()

  if (!name) {
    errors.recipient_name = 'Recipient name is required.'
  } else if (name.length > SHIPMENT_LIMITS.name) {
    errors.recipient_name = `Recipient name can be at most ${SHIPMENT_LIMITS.name} characters.`
  }

  if (!/^01\d{9}$/.test(phone)) {
    errors.recipient_phone = 'Phone must be 11 digits starting with 01.'
  }

  if (!address) {
    errors.recipient_address = 'Delivery address is required.'
  } else if (address.length > SHIPMENT_LIMITS.address) {
    errors.recipient_address = `Delivery address can be at most ${SHIPMENT_LIMITS.address} characters.`
  }

  if (!rawCod) {
    errors.cod_amount = 'Cash on delivery amount is required. Enter 0 if there is nothing to collect.'
  } else if (!/^\d{1,7}(\.\d{1,2})?$/.test(rawCod) || Number(rawCod) > SHIPMENT_LIMITS.codMax) {
    errors.cod_amount =
      'Cash on delivery amount must be a number from 0 to 1,000,000 with at most 2 decimals.'
  }

  if (note.length > SHIPMENT_LIMITS.note) {
    errors.note = `Note can be at most ${SHIPMENT_LIMITS.note} characters.`
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors, body: null }
  }

  const body = {
    recipient_name: name,
    recipient_phone: phone,
    recipient_address: address,
    cod_amount: Number(rawCod).toFixed(2),
  }
  if (note) {
    body.note = note
  }

  return { ok: true, errors: {}, body }
}

export function confirmedAbsentBody(body) {
  return { ...body, confirmed_absent: true }
}

export function normalizeCreateResult(data) {
  const ship = data?.shipment
  if (!ship || !/^[1-9]\d*$/.test(String(ship.id))) {
    return null
  }
  return {
    created: data.created === true,
    shipment: {
      id: Number(ship.id),
      orderId: ship.order_id != null ? Number(ship.order_id) : null,
      status: String(ship.status ?? ''),
      trackingCode: String(ship.tracking_code ?? ''),
      consignmentId: String(ship.consignment_id ?? ''),
    },
  }
}

export function describeCreateError(err, orderId) {
  const hasOrder = orderId != null && /^[1-9]\d*$/.test(String(orderId))
  const inv = hasOrder ? `invoice BIZORA-${orderId}` : 'the invoice of this order'

  if (err?.status === 409) {
    return {
      kind: 'uncertain',
      message: `Bizora already tried to send this order to Steadfast and does not know whether Steadfast received it. Open the Steadfast portal and look for ${inv}. If the parcel is there, it is already booked: do not send again.`,
      fieldErrors: {},
    }
  }

  if (err?.status === 502) {
    const detailPart = err.detail ? ` (${err.detail})` : ''
    return {
      kind: 'courier',
      message: `Steadfast did not confirm the shipment${detailPart}. Before sending again, check ${inv} in the Steadfast portal: if it exists, the parcel was already booked.`,
      fieldErrors: {},
    }
  }

  if (err?.status === 403) {
    return {
      kind: 'forbidden',
      message: 'Only owners and managers can send orders to Steadfast.',
      fieldErrors: {},
    }
  }

  if (err?.status === 404) {
    return {
      kind: 'not-found',
      message: err.detail || 'The order or the Steadfast connection was not found.',
      fieldErrors: {},
    }
  }

  if (err?.status === 400) {
    const formKeys = ['recipient_name', 'recipient_phone', 'recipient_address', 'cod_amount', 'note']
    const matched = {}
    if (err.fieldErrors && typeof err.fieldErrors === 'object') {
      for (const k of formKeys) {
        if (err.fieldErrors[k]) {
          matched[k] = err.fieldErrors[k]
        }
      }
    }

    if (Object.keys(matched).length > 0) {
      return {
        kind: 'validation',
        message: 'Steadfast rejected some of the shipment details. Correct the marked fields and try again.',
        fieldErrors: matched,
      }
    }

    return {
      kind: 'rejected',
      message: err.detail || 'Steadfast shipment details were rejected.',
      fieldErrors: {},
    }
  }

  return {
    kind: 'other',
    message: err?.detail || 'Sending to Steadfast failed.',
    fieldErrors: {},
  }
}

export function canRefreshShipment(shipment, role) {
  return Boolean(
    canManageSteadfast(role) &&
    isSteadfastShipment(shipment) &&
    shipment?.id != null &&
    /^[1-9]\d*$/.test(String(shipment.id)) &&
    shipment?.integration_connection != null &&
    /^[1-9]\d*$/.test(String(shipment.integration_connection)) &&
    typeof shipment?.tracking_code === 'string' &&
    shipment.tracking_code.trim().length > 0,
  )
}

export function normalizeRefreshResult(data) {
  const ship = data?.shipment
  if (!ship || !/^[1-9]\d*$/.test(String(ship.id))) {
    return null
  }
  return {
    changed: data.changed === true,
    shipment: {
      id: Number(ship.id),
      orderId: ship.order_id != null ? Number(ship.order_id) : null,
      status: String(ship.status ?? ''),
      trackingCode: String(ship.tracking_code ?? ''),
      consignmentId: String(ship.consignment_id ?? ''),
    },
  }
}

export function describeRefresh(previousStatus, result) {
  const newStatus = result?.shipment?.status || ''
  if (result?.changed) {
    const prev = String(previousStatus || '')
      .trim()
      .toUpperCase()
    const msg = prev ? `Status updated from ${prev} to ${newStatus}.` : `Status updated to ${newStatus}.`
    return {
      changed: true,
      status: newStatus,
      tone: 'success',
      message: msg,
    }
  }

  let msg = `Checked with Steadfast: no change recorded. Bizora still shows ${newStatus}.`
  if (FINAL_SHIPMENT_STATUSES.has(newStatus)) {
    msg += ' This is a final status; a refresh never changes it.'
  }

  return {
    changed: false,
    status: newStatus,
    tone: 'info',
    message: msg,
  }
}

export function describeRefreshError(err) {
  if (err?.status === 403) {
    return 'Only owners and managers can check courier status.'
  }
  if (err?.status === 404) {
    return 'This shipment was not found for the Steadfast connection.'
  }
  if (err?.status === 502) {
    const detailPart = err.detail ? ` (${err.detail})` : ''
    return `Steadfast did not answer${detailPart}. Nothing was changed in Bizora.`
  }
  if (err?.status === 400) {
    return err.detail || 'The status check was rejected.'
  }
  return err?.detail || 'Checking the status failed.'
}
