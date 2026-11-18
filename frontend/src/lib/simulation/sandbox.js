export const SERVER_ONLY_NOTICE = 'These commands run on the server and never from this screen.'
export const CONNECTIONS_PAGE_SIZE = 50

export const SIMULATION_COMMANDS = Object.freeze([
  {
    key: 'configuration',
    name: 'simulate_configuration',
    title: 'Business configuration',
    command: 'python manage.py simulate_configuration --seed 77001 --at 2026-10-25T12:00:00+00:00',
    demoPrefix: 'config-demo-',
    summary: 'Validates all Business Configuration areas in an isolated demo business.',
  },
  {
    key: 'observability',
    name: 'simulate_observability',
    title: 'Integration observability',
    command: 'python manage.py simulate_observability --seed 75001 --at 2026-10-25T12:00:00+00:00',
    demoPrefix: 'obs-demo-',
    summary:
      'Runs deterministic integration-observability scenarios (connection health, data freshness, partial syncs, failed webhooks, a provider outage and a replay) in an isolated demo business and checks the expected outcomes.',
  },
  {
    key: 'overview',
    name: 'simulate_overview',
    title: 'Overview monitoring',
    command: 'python manage.py simulate_overview --seed 76001 --at 2026-10-25T12:00:00+00:00',
    demoPrefix: 'overview-demo-',
    summary:
      'Validates the Overview APIs against declared upstream Business Intelligence fixtures in an isolated demo business.',
  },
])

export const COMMAND_EFFECTS = Object.freeze([
  'Creates or reuses its own demo business, with demo users and sample records. The business slug starts with the prefix shown for the command.',
  'Refuses to change any existing business that is not its own demo.',
  'Runs its acceptance checks, prints one line of JSON with "passed" true or false, and exits with an error if a check fails.',
])

export const COMMAND_FLAGS_NOTE =
  '--at is the fixed evaluation time and must include a time zone. --seed picks the deterministic scenario. --business-slug is optional and must start with the prefix shown. Run these where demo data is acceptable, such as a development or test database.'

export function simulatedConnections(list) {
  if (!Array.isArray(list)) return []
  const results = []
  for (const entry of list) {
    if (
      entry &&
      typeof entry === 'object' &&
      typeof entry.id === 'number' &&
      Number.isInteger(entry.id) &&
      entry.id > 0 &&
      entry.is_mock === true
    ) {
      results.push({
        id: entry.id,
        name: typeof entry.name === 'string' ? entry.name : null,
        provider: typeof entry.provider === 'string' ? entry.provider : null,
        lifecycle_status: typeof entry.lifecycle_status === 'string' ? entry.lifecycle_status : null,
        health_status: typeof entry.health?.status === 'string' ? entry.health.status : null,
        health_reason: typeof entry.health?.reason === 'string' ? entry.health.reason : null,
      })
    }
  }
  return results
}

export function sandboxSummary(list, { pageSize = CONNECTIONS_PAGE_SIZE } = {}) {
  if (!Array.isArray(list)) {
    return { total: 0, simulated: 0, notSimulated: 0, maybeMore: false }
  }
  let total = 0
  let simulated = 0
  for (const entry of list) {
    if (
      entry &&
      typeof entry === 'object' &&
      typeof entry.id === 'number' &&
      Number.isInteger(entry.id) &&
      entry.id > 0
    ) {
      total++
      if (entry.is_mock === true) {
        simulated++
      }
    }
  }
  const notSimulated = total - simulated
  const maybeMore = total >= pageSize
  return { total, simulated, notSimulated, maybeMore }
}
