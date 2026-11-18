import { businessApiPath } from '../catalog.js'

export function retargetingPath(businessId, customerId) {
  if (!customerId || !/^[1-9]\d*$/.test(String(customerId))) {
    throw new Error('Invalid customer ID')
  }
  return businessApiPath(businessId, `customers/${customerId}/retargeting-context`)
}

export function safePagePath(url) {
  if (typeof url !== 'string' || !url.trim()) {
    return ''
  }
  try {
    return new URL(url.trim(), 'http://placeholder.invalid').pathname
  } catch {
    return ''
  }
}

export function normalizeRetargeting(data) {
  if (
    !data ||
    typeof data !== 'object' ||
    Array.isArray(data) ||
    !/^[1-9]\d*$/.test(String(data.customer_id))
  ) {
    return null
  }

  const customerId = Number(data.customer_id)
  const kind = String(data.kind ?? '')

  const sessRaw =
    data.sessions && typeof data.sessions === 'object' && !Array.isArray(data.sessions) ? data.sessions : {}
  const sessResults = Array.isArray(sessRaw.results) ? sessRaw.results : []
  const sessRows = sessResults
    .filter((r) => r && typeof r === 'object' && /^[1-9]\d*$/.test(String(r.id)))
    .map((r) => ({
      id: Number(r.id),
      startedAt: typeof r.started_at === 'string' ? r.started_at : null,
      durationSeconds: Number.isFinite(r.duration_seconds) ? r.duration_seconds : null,
      trafficSource: String(r.traffic_source ?? ''),
      trafficMedium: String(r.traffic_medium ?? ''),
      utmCampaign: String(r.utm_campaign ?? ''),
      deviceType: String(r.device_type ?? ''),
      country: String(r.country ?? ''),
      isConverted: r.is_converted === true,
      landingPath: safePagePath(r.landing_page_url),
    }))
  const sessCount = Number.isInteger(sessRaw.count) && sessRaw.count >= 0 ? sessRaw.count : sessRows.length
  const sessTruncated = sessRaw.truncated === true
  const sessions = { count: sessCount, truncated: sessTruncated, rows: sessRows }

  const evRaw =
    data.events && typeof data.events === 'object' && !Array.isArray(data.events) ? data.events : {}
  const evResults = Array.isArray(evRaw.results) ? evRaw.results : []
  const evRows = evResults
    .filter((r) => r && typeof r === 'object' && /^[1-9]\d*$/.test(String(r.id)))
    .map((r) => ({
      id: Number(r.id),
      eventType: String(r.event_type ?? ''),
      occurredAt: typeof r.occurred_at === 'string' ? r.occurred_at : null,
      pagePath: safePagePath(r.page_url),
      eventValue:
        r.event_value !== null &&
        r.event_value !== undefined &&
        !Number.isNaN(Number(r.event_value)) &&
        Number.isFinite(Number(r.event_value))
          ? Number(r.event_value)
          : null,
      currency: String(r.currency ?? ''),
      productId: /^[1-9]\d*$/.test(String(r.product)) ? Number(r.product) : null,
      orderId: /^[1-9]\d*$/.test(String(r.order)) ? Number(r.order) : null,
    }))
  const evCount = Number.isInteger(evRaw.count) && evRaw.count >= 0 ? evRaw.count : evRows.length
  const evTruncated = evRaw.truncated === true
  const events = { count: evCount, truncated: evTruncated, rows: evRows }

  const convRaw =
    data.conversions && typeof data.conversions === 'object' && !Array.isArray(data.conversions)
      ? data.conversions
      : {}
  const convResults = Array.isArray(convRaw.results) ? convRaw.results : []
  const convRows = convResults
    .filter((r) => r && typeof r === 'object' && /^[1-9]\d*$/.test(String(r.id)))
    .map((r) => ({
      id: Number(r.id),
      conversionType: String(r.conversion_type ?? ''),
      convertedAt: typeof r.converted_at === 'string' ? r.converted_at : null,
      conversionValue:
        r.conversion_value !== null &&
        r.conversion_value !== undefined &&
        !Number.isNaN(Number(r.conversion_value)) &&
        Number.isFinite(Number(r.conversion_value))
          ? Number(r.conversion_value)
          : null,
      currency: String(r.currency ?? ''),
      attributionType: String(r.attribution_type ?? ''),
      campaignId: /^[1-9]\d*$/.test(String(r.campaign)) ? Number(r.campaign) : null,
      orderId: /^[1-9]\d*$/.test(String(r.order)) ? Number(r.order) : null,
    }))
  const convCount = Number.isInteger(convRaw.count) && convRaw.count >= 0 ? convRaw.count : convRows.length
  const convTruncated = convRaw.truncated === true
  const conversions = { count: convCount, truncated: convTruncated, rows: convRows }

  const audRaw =
    data.audience_recommendation &&
    typeof data.audience_recommendation === 'object' &&
    !Array.isArray(data.audience_recommendation)
      ? data.audience_recommendation
      : null
  const audience = {
    status: audRaw && typeof audRaw.status === 'string' ? audRaw.status.toUpperCase() : 'UNAVAILABLE',
    owner:
      audRaw && typeof audRaw.owner === 'string' ? audRaw.owner : 'Business Intelligence / AI Intelligence',
    reason: audRaw && typeof audRaw.reason === 'string' ? audRaw.reason : '',
  }

  return { customerId, kind, sessions, events, conversions, audience }
}

export function isEmptyRetargeting(view) {
  return Boolean(
    view &&
    view.sessions &&
    view.events &&
    view.conversions &&
    view.sessions.count === 0 &&
    view.events.count === 0 &&
    view.conversions.count === 0,
  )
}

export function truncationNote(section, noun) {
  if (!section || !section.truncated) {
    return ''
  }
  const rowCount = section.rows ? section.rows.length : 0
  return `Showing the first ${rowCount} of ${section.count} ${noun}, oldest first.`
}

export function describeRetargetingError(err) {
  if (!err) {
    return 'Observed signals could not be loaded.'
  }
  if (err.status === 400 && err.code === 'INVALID_RELATION') {
    return 'This customer was not found in this business.'
  }
  if (err.status === 403) {
    return 'Your role cannot view this information.'
  }
  if (err.status === 404) {
    return 'This business was not found, or you do not have access to it.'
  }
  return err.detail || 'Observed signals could not be loaded.'
}
