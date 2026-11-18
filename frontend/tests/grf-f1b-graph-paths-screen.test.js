import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('source text: GraphPathFinder.js, GraphExplorerPanel.js, and Intelligence.js (GRF-F1b)', () => {
  const pathFinderFile = path.resolve('src/components/GraphPathFinder.js')
  const explorerPanelFile = path.resolve('src/components/GraphExplorerPanel.js')
  const intelFile = path.resolve('src/components/Intelligence.js')

  assert.ok(fs.existsSync(pathFinderFile), 'GraphPathFinder.js must exist')
  assert.ok(fs.existsSync(explorerPanelFile), 'GraphExplorerPanel.js must exist')

  const pathFinderContent = fs.readFileSync(pathFinderFile, 'utf8')
  assert.ok(pathFinderContent.startsWith("'use client'"), "GraphPathFinder.js must start with 'use client'")
  assert.ok(
    pathFinderContent.includes("from '@/lib/intelligence/graphExplore'"),
    'Must import from graphExplore',
  )
  assert.ok(pathFinderContent.includes("from '@/lib/clientApi'"), 'Must import from clientApi')
  assert.ok(pathFinderContent.includes("from '@/components/ui'"), 'Must import from components/ui')

  const requiredCodeTokens = [
    'pathSearchPath(',
    'normalizePathSearch(',
    'graphErrorMessage(',
    'GRAPH_ENTITY_TYPES',
    'GRAPH_DIRECTIONS',
    'PATH_RESULT_LIMIT',
  ]
  for (const tok of requiredCodeTokens) {
    assert.ok(pathFinderContent.includes(tok), `GraphPathFinder.js must include ${tok}`)
  }

  const requiredPhrases = [
    'Find a path between two entities',
    'Find paths',
    'Start entity type',
    'Start entity ID',
    'End entity type',
    'End entity ID',
    'Direction',
    'Maximum hops',
    'Explain each step',
    'Minimum confidence',
    'The path search did not run',
    'The path search failed',
    'No path found',
    'Missing relationships are never invented',
    'Choose two entities and select Find paths.',
    'The server returns at most 10 paths',
    'aria-live="polite"',
  ]
  for (const phrase of requiredPhrases) {
    assert.ok(pathFinderContent.includes(phrase), `GraphPathFinder.js must include phrase "${phrase}"`)
  }

  // Strip comments for regex checks
  const strippedCode = pathFinderContent.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(strippedCode), 'No raw hex color allowed')
  assert.ok(!strippedCode.includes('dangerouslySetInnerHTML'))
  assert.ok(!strippedCode.includes('window.confirm'))
  assert.ok(!strippedCode.includes('localStorage'))
  assert.ok(!strippedCode.includes('limit='))
  assert.ok(!/<Banner[^>]*\btone=/.test(strippedCode), 'No tone= on Banner')

  const forbiddenClasses = ['text-caption', 'text-muted', 'text-secondary', 'stack-xs', 'stack-md']
  for (const cls of forbiddenClasses) {
    const classRegex = new RegExp(`className=["'][^"']*\\b${cls}\\b[^"']*["']`)
    assert.ok(!classRegex.test(strippedCode), `GraphPathFinder.js must not contain forbidden class ${cls}`)
  }

  // GraphExplorerPanel checks
  const explorerContent = fs.readFileSync(explorerPanelFile, 'utf8')
  assert.ok(explorerContent.startsWith("'use client'"), "GraphExplorerPanel.js must start with 'use client'")
  assert.ok(explorerContent.includes("from '@/components/ui'"), 'Must import from @/components/ui')
  assert.ok(explorerContent.includes("from './GraphPathFinder'"), 'Must import from ./GraphPathFinder')
  assert.ok(explorerContent.includes('EXPLORER_VIEWS'))
  assert.ok(explorerContent.includes('Explore the graph'))
  assert.ok(explorerContent.includes('Find a path'))
  assert.ok(explorerContent.includes('Graph exploration tools'))
  assert.ok(explorerContent.includes('role="tabpanel"'))

  // Intelligence.js checks
  const intelContent = fs.readFileSync(intelFile, 'utf8')
  assert.ok(intelContent.includes("import GraphExplorerPanel from './GraphExplorerPanel'"))
  assert.ok(intelContent.includes('<GraphExplorerPanel'))

  const journeyEndIdx = intelContent.indexOf('No journey data available for this entity.')
  const mountIdx = intelContent.indexOf('<GraphExplorerPanel')
  const metricsIdx = intelContent.indexOf('TAB 3: METRICS & ANALYSIS')

  assert.ok(journeyEndIdx > 0, 'Journey end phrase must exist')
  assert.ok(mountIdx > journeyEndIdx, 'Mount must be after Journey end')
  assert.ok(metricsIdx > mountIdx, 'Mount must be before Tab 3 Metrics')
  assert.ok(intelContent.includes('graph/traversal'))
  assert.ok(intelContent.includes('Journey timeline'))
})
