import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  SERVER_ONLY_NOTICE,
  CONNECTIONS_PAGE_SIZE,
  SIMULATION_COMMANDS,
  COMMAND_EFFECTS,
  COMMAND_FLAGS_NOTE,
  simulatedConnections,
  sandboxSummary,
} from '../src/lib/simulation/sandbox.js'

test('constants: SIMULATION_COMMANDS, COMMAND_EFFECTS, SERVER_ONLY_NOTICE (SBX-F1)', () => {
  assert.equal(SERVER_ONLY_NOTICE, 'These commands run on the server and never from this screen.')
  assert.equal(CONNECTIONS_PAGE_SIZE, 50)
  assert.equal(SIMULATION_COMMANDS.length, 3)
  assert.equal(COMMAND_EFFECTS.length, 3)
  assert.ok(COMMAND_FLAGS_NOTE.includes('--at is the fixed evaluation time'))

  const expectedKeys = ['configuration', 'observability', 'overview']
  const expectedNames = ['simulate_configuration', 'simulate_observability', 'simulate_overview']
  const expectedPrefixes = ['config-demo-', 'obs-demo-', 'overview-demo-']

  SIMULATION_COMMANDS.forEach((cmd, idx) => {
    assert.equal(cmd.key, expectedKeys[idx])
    assert.equal(cmd.name, expectedNames[idx])
    assert.equal(cmd.demoPrefix, expectedPrefixes[idx])
    assert.ok(cmd.command.startsWith('python manage.py '))
    assert.ok(cmd.command.includes('--seed '))
    assert.ok(cmd.command.includes('--at '))
    assert.ok(typeof cmd.summary === 'string' && cmd.summary.length > 0)
  })
})

test('simulatedConnections filters and maps connection list safely (SBX-F1)', () => {
  const mixedList = [
    {
      id: 1,
      name: 'Mock Steadfast',
      provider: 'steadfast',
      lifecycle_status: 'ACTIVE',
      is_mock: true,
      health: { status: 'HEALTHY', reason: 'Syncing normally' },
      extra_junk: 'ignore_me',
    },
    {
      id: 2,
      name: 'Real Meta',
      provider: 'meta',
      lifecycle_status: 'ACTIVE',
      is_mock: false,
    },
    {
      id: 3,
      name: 'Mock TikTok String',
      provider: 'tiktok',
      lifecycle_status: 'DISABLED',
      is_mock: 'true', // not boolean true
    },
    {
      id: 'bad_id',
      name: 'Invalid ID',
      is_mock: true,
    },
    {
      id: 4,
      name: 'Mock No Health',
      provider: 'custom',
      lifecycle_status: null,
      is_mock: true,
    },
    null,
    'a string',
  ]

  const simulated = simulatedConnections(mixedList)
  assert.equal(simulated.length, 2)
  assert.deepEqual(simulated[0], {
    id: 1,
    name: 'Mock Steadfast',
    provider: 'steadfast',
    lifecycle_status: 'ACTIVE',
    health_status: 'HEALTHY',
    health_reason: 'Syncing normally',
  })
  assert.deepEqual(simulated[1], {
    id: 4,
    name: 'Mock No Health',
    provider: 'custom',
    lifecycle_status: null,
    health_status: null,
    health_reason: null,
  })

  // Non-array inputs
  assert.deepEqual(simulatedConnections(null), [])
  assert.deepEqual(simulatedConnections({}), [])
  assert.deepEqual(simulatedConnections('test'), [])
})

test('sandboxSummary counts connections and evaluates maybeMore (SBX-F1)', () => {
  const list49 = Array.from({ length: 49 }, (_, i) => ({
    id: i + 1,
    is_mock: i < 10,
  }))
  const summary49 = sandboxSummary(list49)
  assert.equal(summary49.total, 49)
  assert.equal(summary49.simulated, 10)
  assert.equal(summary49.notSimulated, 39)
  assert.equal(summary49.maybeMore, false)

  const list50 = Array.from({ length: 50 }, (_, i) => ({
    id: i + 1,
    is_mock: i < 10,
  }))
  const summary50 = sandboxSummary(list50)
  assert.equal(summary50.total, 50)
  assert.equal(summary50.maybeMore, true)

  const customPageSize = sandboxSummary(
    [
      { id: 1, is_mock: true },
      { id: 2, is_mock: false },
    ],
    {
      pageSize: 2,
    },
  )
  assert.equal(customPageSize.total, 2)
  assert.equal(customPageSize.maybeMore, true)

  assert.deepEqual(sandboxSummary([]), {
    total: 0,
    simulated: 0,
    notSimulated: 0,
    maybeMore: false,
  })
  assert.deepEqual(sandboxSummary(null), {
    total: 0,
    simulated: 0,
    notSimulated: 0,
    maybeMore: false,
  })
})

test('source checks: SimulationSandbox.js (SBX-F1)', () => {
  const filePath = path.join(process.cwd(), 'src/components/SimulationSandbox.js')
  assert.ok(fs.existsSync(filePath), 'SimulationSandbox.js must exist')
  const code = fs.readFileSync(filePath, 'utf8')

  assert.ok(code.trim().startsWith("'use client'"), "Must start with 'use client'")
  assert.ok(code.includes('@/components/ui'), 'Must import from ui kit')
  assert.ok(code.includes('@/lib/simulation/sandbox'), 'Must import from sandbox lib')

  const requiredTexts = [
    'SimulatedBadge',
    'CopyableCode',
    'inline={false}',
    'SERVER_ONLY_NOTICE',
    'Nothing on this page starts a simulation or changes data.',
    'Sample data (SIMULATED)',
    'No simulated connections',
    'No connections yet',
    'Read-only page',
    'Prototype Simulation & Sandbox',
  ]
  for (const text of requiredTexts) {
    assert.ok(code.includes(text), `Must contain text: ${text}`)
  }

  // Raw hex check
  const strippedCode = code.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(strippedCode), 'Must have no raw hex colors')

  // Forbidden words in entire file
  const forbidden = [
    'clientApi',
    'fetch(',
    'method:',
    'window.confirm',
    'dangerouslySetInnerHTML',
    'Run simulation',
    'Start simulation',
    'Run now',
    'Execute',
    'onClick',
  ]
  for (const word of forbidden) {
    assert.ok(!code.includes(word), `Must not contain: ${word}`)
  }
})

test('source checks: Admin.js integration (SBX-F1)', () => {
  const code = fs.readFileSync(path.join(process.cwd(), 'src/components/Admin.js'), 'utf8')
  assert.ok(code.includes("import SimulationSandbox from './SimulationSandbox'"))
  assert.ok(code.includes('<SimulationSandbox'))
  assert.ok(code.includes("currentTab === 'simulation'"))
  assert.ok(code.includes('connections={initialConnections}'))
  assert.ok(code.includes('Prototype Simulation & Sandbox'))
  assert.ok(!code.includes('What-if simulation engine and scenario sandbox are unmounted'))
})
