import { businessApiPath } from '../catalog.js'

/**
 * Tracking API helpers and pure normalizers.
 * Contract: docs/_inbox/tracking-ui/reference/API-CONTRACT-TRACKING.md
 */

export function trackingBase(businessId) {
  return businessApiPath(businessId, 'integrations/tracking/')
}

export function summaryPath(businessId) {
  return `${trackingBase(businessId)}summary/`
}

export function attemptsPath(businessId, { connection, status, mode, limit = 25, offset = 0 } = {}) {
  const params = []

  if (connection !== undefined && connection !== null) {
    if (!Number.isInteger(connection) || connection <= 0) {
      throw new Error('connection must be a positive integer')
    }
    params.push(`connection=${connection}`)
  }

  if (status !== undefined && status !== null) {
    if (!['RUNNING', 'SUCCEEDED', 'FAILED', 'UNSUPPORTED'].includes(status)) {
      throw new Error('status must be one of RUNNING, SUCCEEDED, FAILED, UNSUPPORTED')
    }
    params.push(`status=${encodeURIComponent(status)}`)
  }

  if (mode !== undefined && mode !== null) {
    if (!['PREPARED', 'LIVE'].includes(mode)) {
      throw new Error('mode must be one of PREPARED, LIVE')
    }
    params.push(`mode=${encodeURIComponent(mode)}`)
  }

  if (!Number.isInteger(limit) || limit < 1 || limit > 200) {
    throw new Error('limit must be an integer between 1 and 200')
  }
  params.push(`limit=${limit}`)

  if (!Number.isInteger(offset) || offset < 0) {
    throw new Error('offset must be an integer >= 0')
  }
  params.push(`offset=${offset}`)

  return `${trackingBase(businessId)}attempts/?${params.join('&')}`
}

export function settingsPath(businessId, connectionId) {
  const numId = Number(connectionId)
  if (!Number.isInteger(numId) || numId <= 0) {
    throw new Error('connectionId must be a positive integer')
  }
  return `${trackingBase(businessId)}connections/${numId}/settings/`
}

export const ALLOWED_EVENTS = [
  'VIEW',
  'PAGE_VIEW',
  'PRODUCT_VIEW',
  'VIEW_ITEM',
  'CART',
  'ADD_TO_CART',
  'CHECKOUT',
  'CHECKOUT_START',
  'BEGIN_CHECKOUT',
  'PURCHASE',
  'ORDER',
  'CHECKOUT_COMPLETE',
  'ORDER_COMPLETE',
]

const ALLOWED_EVENTS_SET = new Set(ALLOWED_EVENTS)

export const PROVIDER_LABELS = {
  meta: 'Meta Conversions API',
  tiktok: 'TikTok Events API',
  ga4: 'Google Analytics 4',
}

export function providerLabel(provider) {
  if (!provider) return 'Unknown provider'
  return PROVIDER_LABELS[provider] || String(provider)
}

export function modeLabel(mode, sent) {
  if (mode === 'PREPARED') {
    return 'Prepared, not sent'
  }
  if (mode === 'LIVE') {
    return sent === true ? 'Sent and accepted' : 'Sent, not accepted'
  }
  return 'No send attempted'
}

export function statusTone(status) {
  if (status === 'SUCCEEDED') return 'success'
  if (status === 'FAILED') return 'danger'
  if (status === 'UNSUPPORTED') return 'neutral'
  if (status === 'RUNNING') return 'info'
  return 'neutral'
}

export function attemptTone(attempt) {
  if (!attempt || typeof attempt !== 'object') return 'neutral'
  if (attempt.sent === true) return 'success'
  if (attempt.status === 'SUCCEEDED' && !attempt.sent) return 'info'
  return statusTone(attempt.status)
}

export function normalizeSummary(data) {
  if (!data || typeof data !== 'object') {
    return { businessId: null, connections: [], totals: { connections: 0, attempts: 0 } }
  }

  const businessId = data.business_id ?? data.businessId ?? null
  const rawConnections = Array.isArray(data.connections) ? data.connections : []
  const connections = rawConnections
    .filter((c) => c && typeof c === 'object' && typeof c.id === 'number' && !isNaN(c.id))
    .map((c) => ({
      id: c.id,
      name: typeof c.name === 'string' ? c.name : `Connection #${c.id}`,
      provider: typeof c.provider === 'string' ? c.provider : null,
      status: typeof c.status === 'string' ? c.status : 'CONNECTED',
      is_mock: Boolean(c.is_mock),
      mode: typeof c.mode === 'string' ? c.mode : 'PREPARED',
      credentials_available: Boolean(c.credentials_available),
      settings: {
        enabled: Boolean(c.settings?.enabled),
        test_mode: Boolean(c.settings?.test_mode),
        events: Array.isArray(c.settings?.events) ? c.settings.events : [],
        test_event_code: c.settings?.test_event_code ?? null,
        measurement_id: c.settings?.measurement_id ?? null,
        api_version: c.settings?.api_version ?? null,
        send_pii: false,
      },
      counts: {
        total: Number(c.counts?.total) || 0,
        prepared: Number(c.counts?.prepared) || 0,
        live_succeeded: Number(c.counts?.live_succeeded) || 0,
        failed: Number(c.counts?.failed) || 0,
        unsupported: Number(c.counts?.unsupported) || 0,
      },
      last_attempt_at: c.last_attempt_at ?? null,
    }))

  const totals = {
    connections: Number(data.totals?.connections) || connections.length,
    attempts: Number(data.totals?.attempts) || 0,
  }

  return { businessId, connections, totals }
}

export function normalizeAttempts(data) {
  if (!data || typeof data !== 'object') {
    return { total: 0, limit: 0, offset: 0, results: [] }
  }

  const total = Number(data.total_count ?? data.count ?? data.total) || 0
  const limit = Number(data.limit) || 0
  const offset = Number(data.offset) || 0
  const rawResults = Array.isArray(data.results) ? data.results : []

  const results = rawResults
    .filter((r) => r && typeof r === 'object')
    .map((row) => ({
      id: row.id,
      connection_id: row.connection_id,
      connection_name: row.connection_name,
      provider: row.provider,
      website_event_id: row.website_event_id ?? null,
      event_type: row.event_type ?? null,
      event_id: row.event_id ?? null,
      status: row.status,
      mode: row.mode ?? null,
      sent: Boolean(row.sent),
      outcome: row.outcome ?? null,
      http_status: row.http_status ?? null,
      latency_ms: row.latency_ms ?? null,
      retry_after_seconds: row.retry_after_seconds ?? null,
      error: row.error ?? null,
      reason: row.reason ?? null,
      created_at: row.created_at ?? null,
      completed_at: row.completed_at ?? null,
      next_retry_at: row.next_retry_at ?? null,
    }))

  return { total, limit, offset, results }
}

export function settingsPatchBody(connection, draft) {
  if (!draft || typeof draft !== 'object') {
    return {}
  }

  const provider = connection?.provider
  const currentSettings = connection?.settings || {}
  const body = {}

  // 1. enabled
  if (draft.enabled !== undefined) {
    if (typeof draft.enabled !== 'boolean') {
      throw new Error('enabled must be a boolean')
    }
    if (draft.enabled !== currentSettings.enabled) {
      body.enabled = draft.enabled
    }
  }

  // 2. test_mode
  if (draft.test_mode !== undefined) {
    if (typeof draft.test_mode !== 'boolean') {
      throw new Error('test_mode must be a boolean')
    }
    if (draft.test_mode !== currentSettings.test_mode) {
      body.test_mode = draft.test_mode
    }
  }

  // 3. events
  if (draft.events !== undefined) {
    if (!Array.isArray(draft.events)) {
      throw new Error('events must be an array of event names')
    }
    const normalizedEvents = []
    const seen = new Set()
    for (const ev of draft.events) {
      if (typeof ev !== 'string') {
        throw new Error('Each event must be a string')
      }
      const upper = ev.trim().toUpperCase()
      if (!ALLOWED_EVENTS_SET.has(upper)) {
        throw new Error(`Invalid event name: ${ev}`)
      }
      if (!seen.has(upper)) {
        seen.add(upper)
        normalizedEvents.push(upper)
      }
    }
    if (normalizedEvents.length > 30) {
      throw new Error('events list exceeds maximum length of 30')
    }

    const currentEventsSet = new Set(
      (currentSettings.events || []).map((e) => (typeof e === 'string' ? e.trim().toUpperCase() : e)),
    )
    const areSetsEqual =
      seen.size === currentEventsSet.size && [...seen].every((val) => currentEventsSet.has(val))

    if (!areSetsEqual) {
      body.events = normalizedEvents
    }
  }

  // 4. test_event_code (Meta, TikTok only)
  if (draft.test_event_code !== undefined) {
    const code = draft.test_event_code === '' || draft.test_event_code === null ? null : draft.test_event_code

    if (code !== null) {
      if (provider === 'ga4') {
        throw new Error('test_event_code is not supported for GA4')
      }
      if (typeof code !== 'string' || code.length > 64) {
        throw new Error('test_event_code must be a string up to 64 characters')
      }
    }

    const currentCode = currentSettings.test_event_code ?? null
    if (code !== currentCode) {
      body.test_event_code = code
    }
  }

  // 5. measurement_id (GA4 only)
  if (draft.measurement_id !== undefined) {
    const meas = draft.measurement_id === '' || draft.measurement_id === null ? null : draft.measurement_id

    if (meas !== null) {
      if (provider !== 'ga4') {
        throw new Error('measurement_id is only supported for GA4')
      }
      if (typeof meas !== 'string' || !/^G-[A-Z0-9]{4,20}$/.test(meas)) {
        throw new Error('measurement_id must match format ^G-[A-Z0-9]{4,20}$')
      }
    }

    const currentMeas = currentSettings.measurement_id ?? null
    if (meas !== currentMeas) {
      body.measurement_id = meas
    }
  }

  // 6. api_version (Meta only)
  if (draft.api_version !== undefined) {
    const ver = draft.api_version === '' || draft.api_version === null ? null : draft.api_version

    if (ver !== null) {
      if (provider !== 'meta') {
        throw new Error('api_version is only supported for Meta')
      }
      if (typeof ver !== 'string' || !/^v\d{1,2}\.\d{1,2}$/.test(ver)) {
        throw new Error('api_version must match format ^v\\d{1,2}\\.\\d{1,2}$')
      }
    }

    const currentVer = currentSettings.api_version ?? null
    if (ver !== currentVer) {
      body.api_version = ver
    }
  }

  return body
}
