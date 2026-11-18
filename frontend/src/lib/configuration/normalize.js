export function actorLabel(actorId) {
  if (typeof actorId === 'number' && Number.isSafeInteger(actorId) && actorId > 0) {
    return `User #${actorId}`
  }
  return 'System or unknown user'
}

export function normalizePage(data, mapRow = (row) => row) {
  if (!data || typeof data !== 'object' || !Array.isArray(data.results)) {
    return { count: 0, next: null, previous: null, results: [] }
  }

  const results = data.results.filter((r) => r && typeof r === 'object' && !Array.isArray(r)).map(mapRow)

  let count = results.length
  if (typeof data.count === 'number' && Number.isInteger(data.count) && data.count >= 0) {
    count = data.count
  } else if (
    typeof data.total_count === 'number' &&
    Number.isInteger(data.total_count) &&
    data.total_count >= 0
  ) {
    count = data.total_count
  }

  const next = typeof data.next === 'string' ? data.next : null
  const previous = typeof data.previous === 'string' ? data.previous : null

  return { count, next, previous, results }
}

export function normalizeRecord(data) {
  const id = typeof data?.id === 'number' && Number.isInteger(data.id) ? data.id : null
  const kind = typeof data?.kind === 'string' ? data.kind : null
  const key = data?.key !== undefined && data?.key !== null && data.key !== '' ? String(data.key) : null

  const version =
    typeof data?.version === 'number' && Number.isInteger(data.version) && data.version >= 0
      ? data.version
      : null

  const status = typeof data?.status === 'string' ? data.status : 'ACTIVE'

  const priority =
    typeof data?.priority === 'number' && Number.isInteger(data.priority) && data.priority >= 0
      ? data.priority
      : 0

  const valid_from = typeof data?.valid_from === 'string' ? data.valid_from : null
  const valid_to = typeof data?.valid_to === 'string' ? data.valid_to : null

  const settings =
    data?.settings && typeof data.settings === 'object' && !Array.isArray(data.settings) ? data.settings : {}

  const updated_at = typeof data?.updated_at === 'string' ? data.updated_at : null
  const updated_by_id =
    typeof data?.updated_by_id === 'number' && Number.isInteger(data.updated_by_id)
      ? data.updated_by_id
      : null

  return {
    id,
    kind,
    key,
    version,
    status,
    priority,
    valid_from,
    valid_to,
    settings,
    updated_at,
    updated_by_id,
  }
}

export function recordSource(record) {
  const norm = normalizeRecord(record)
  return {
    ...norm.settings,
    status: norm.status,
    priority: norm.priority,
  }
}
