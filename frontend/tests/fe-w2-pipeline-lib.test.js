import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  PIPELINE_RUN_PATH,
  GRAPH_REBUILD_PATH,
  rebuildBody,
  summarizePipelineResult,
  summarizeRebuildResult,
  isManager,
} from '../src/lib/intelligence/pipeline.js'

test('pipeline and graph path helpers produce expected paths', () => {
  assert.equal(PIPELINE_RUN_PATH(1), 'businesses/1/intelligence/pipeline/run/')
  assert.equal(PIPELINE_RUN_PATH('42'), 'businesses/42/intelligence/pipeline/run/')
  assert.equal(GRAPH_REBUILD_PATH(1), 'businesses/1/graph/rebuild/')
  assert.equal(GRAPH_REBUILD_PATH('42'), 'businesses/42/graph/rebuild/')
})

test('rebuildBody accepts boolean and throws for non-booleans', () => {
  assert.deepEqual(rebuildBody(), { clean: false })
  assert.deepEqual(rebuildBody({ clean: false }), { clean: false })
  assert.deepEqual(rebuildBody({ clean: true }), { clean: true })

  assert.throws(() => rebuildBody({ clean: 'false' }), /boolean/i)
  assert.throws(() => rebuildBody({ clean: 0 }), /boolean/i)
  assert.throws(() => rebuildBody({ clean: 1 }), /boolean/i)
  assert.throws(() => rebuildBody({ clean: null }), /boolean/i)
})

test('isManager correctly validates roles', () => {
  assert.equal(isManager('OWNER'), true)
  assert.equal(isManager('MANAGER'), true)
  assert.equal(isManager('owner'), true)
  assert.equal(isManager('manager'), true)
  assert.equal(isManager('OPERATOR'), false)
  assert.equal(isManager('VIEWER'), false)
  assert.equal(isManager(''), false)
  assert.equal(isManager(undefined), false)
  assert.equal(isManager(null), false)
})

test('summarizePipelineResult handles data with and without metrics_computed and handles junk', () => {
  assert.deepEqual(summarizePipelineResult(null), [])
  assert.deepEqual(summarizePipelineResult(undefined), [])
  assert.deepEqual(summarizePipelineResult('junk'), [])
  assert.deepEqual(summarizePipelineResult({}), [])

  const dataWithoutMetrics = {
    status: 'COMPLETED',
    relationships_reconciled: {
      created: 3,
      updated: 1,
      unchanged: 10,
      invalidated: 0,
    },
    quarantined_records: 0,
    active_facts_count: 5,
    open_issues_count: 2,
  }
  const summary1 = summarizePipelineResult(dataWithoutMetrics)
  const labels1 = summary1.map((r) => r.label)
  assert.ok(labels1.includes('Status'))
  assert.ok(labels1.includes('Relationships created'))
  assert.ok(labels1.includes('Relationships updated'))
  assert.ok(labels1.includes('Quarantined records'))
  assert.ok(labels1.includes('Active facts'))
  assert.ok(labels1.includes('Open issues'))
  assert.ok(!labels1.includes('Metrics computed'))

  const dataWithMetrics = {
    ...dataWithoutMetrics,
    metrics_computed: 14,
  }
  const summary2 = summarizePipelineResult(dataWithMetrics)
  const metricRow = summary2.find((r) => r.label === 'Metrics computed')
  assert.ok(metricRow)
  assert.equal(metricRow.value, 14)
})

test('summarizeRebuildResult handles rebuild output fields and skips missing ones', () => {
  assert.deepEqual(summarizeRebuildResult(null), [])
  assert.deepEqual(summarizeRebuildResult({}), [])

  const rebuildData = {
    nodes_created: 12,
    nodes_updated: 4,
    nodes_pruned: 0,
    edges_created: 25,
    edges_updated: 2,
    edges_pruned: 1,
    total_nodes: 50,
    total_edges: 70,
  }
  const summary = summarizeRebuildResult(rebuildData)
  assert.equal(summary.length, 8)
  assert.deepEqual(
    summary.find((r) => r.label === 'Nodes created'),
    {
      label: 'Nodes created',
      value: 12,
    },
  )
  assert.deepEqual(
    summary.find((r) => r.label === 'Total edges'),
    {
      label: 'Total edges',
      value: 70,
    },
  )
})

test('Intelligence.js imports from @/lib/intelligence/pipeline, has buttons, and removes offline text', () => {
  const filePath = path.join(process.cwd(), 'src/components/Intelligence.js')
  const content = fs.readFileSync(filePath, 'utf8')
  assert.ok(
    content.includes('@/lib/intelligence/pipeline'),
    'Intelligence.js must import from @/lib/intelligence/pipeline',
  )
  assert.ok(content.includes('Run data pipeline'), 'Must contain "Run data pipeline"')
  assert.ok(content.includes('Rebuild graph'), 'Must contain "Rebuild graph"')
  assert.ok(
    !content.includes('Pipeline orchestration and continuous ingestion runners are offline'),
    'Must no longer contain offline text',
  )
})
