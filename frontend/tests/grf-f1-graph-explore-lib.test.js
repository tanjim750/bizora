import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import {
  GRAPH_ENTITY_TYPES,
  GRAPH_RELATIONSHIP_TYPES,
  GRAPH_DIRECTIONS,
  GRAPH_DIRECTION_LABELS,
  PATH_MAX_HOPS,
  PATH_RESULT_LIMIT,
  GRAPH_ID_MAX,
  parseGraphEntityId,
  graphFilterParams,
  pathSearchPath,
  graphNodeLabel,
  normalizePathSearch,
  graphErrorMessage,
} from '../src/lib/intelligence/graphExplore.js'

test('constants: entity types, relationships, directions, limits (GRF-F1)', () => {
  assert.deepEqual(GRAPH_ENTITY_TYPES, [
    'CUSTOMER',
    'PRODUCT',
    'PRODUCT_VARIANT',
    'ORDER',
    'PAYMENT',
    'SHIPMENT',
    'CAMPAIGN',
    'CAMPAIGN_CONVERSION',
    'WEBSITE_VISITOR',
    'WEBSITE_SESSION',
    'WEBSITE_EVENT',
    'CONVERSATION',
    'MESSAGE',
    'CALL',
  ])

  assert.deepEqual(GRAPH_RELATIONSHIP_TYPES, [
    'PLACED_ORDER',
    'CONTAINS_PRODUCT',
    'CONTAINS_VARIANT',
    'HAS_PAYMENT',
    'HAS_SHIPMENT',
    'HAS_CONVERSATION',
    'HAS_MESSAGE',
    'HAS_CALL',
    'HAS_VISITOR',
    'HAS_SESSION',
    'HAS_EVENT',
    'HAS_WEBSITE_EVENT',
    'REFERENCES_PRODUCT',
    'REFERENCES_ORDER',
    'HAS_REPORTED_CONVERSION',
    'REPORTED_CUSTOMER',
    'REPORTED_ORDER',
    'REPORTED_SESSION',
  ])

  assert.deepEqual(GRAPH_DIRECTIONS, ['BIDIRECTIONAL', 'OUTBOUND', 'INBOUND'])
  assert.deepEqual(GRAPH_DIRECTION_LABELS, {
    BIDIRECTIONAL: 'Either direction',
    OUTBOUND: 'Start to end only',
    INBOUND: 'End to start only',
  })
  assert.equal(PATH_MAX_HOPS, 5)
  assert.equal(PATH_RESULT_LIMIT, 10)
  assert.equal(GRAPH_ID_MAX, '9223372036854775807')
})

test('parseGraphEntityId validates integers and returns canonical string (GRF-F1)', () => {
  assert.equal(parseGraphEntityId('12'), '12')
  assert.equal(parseGraphEntityId(' 7 '), '7')
  assert.equal(parseGraphEntityId(5), '5')
  assert.equal(parseGraphEntityId('007'), '7')
  assert.equal(parseGraphEntityId('9223372036854775807'), '9223372036854775807')

  const invalidValues = [
    '',
    '-1',
    '1.5',
    '0x10',
    '1e3',
    'abc',
    null,
    undefined,
    true,
    NaN,
    1.5,
    '9223372036854775808',
    '0',
  ]
  for (const v of invalidValues) {
    assert.throws(() => parseGraphEntityId(v), /whole number between 1 and 9223372036854775807/)
  }

  assert.throws(() => parseGraphEntityId('x', 'Start ID'), /^Error: Start ID/)
})

test('graphFilterParams constructs query fragments and validates (GRF-F1)', () => {
  assert.deepEqual(graphFilterParams(), [])
  assert.deepEqual(graphFilterParams({}), [])
  assert.deepEqual(graphFilterParams({ minConfidence: '' }), [])

  assert.deepEqual(graphFilterParams({ minConfidence: 0.5 }), ['min_confidence=0.5'])
  assert.deepEqual(graphFilterParams({ minConfidence: '0.95' }), ['min_confidence=0.95'])
  assert.deepEqual(graphFilterParams({ minConfidence: 0 }), ['min_confidence=0'])
  assert.deepEqual(graphFilterParams({ minConfidence: 1 }), ['min_confidence=1'])
  assert.deepEqual(graphFilterParams({ minConfidence: ' 0.25 ' }), ['min_confidence=0.25'])

  assert.throws(() => graphFilterParams({ minConfidence: 1.2 }), /between 0 and 1/)
  assert.throws(() => graphFilterParams({ minConfidence: -0.1 }), /between 0 and 1/)
  assert.throws(() => graphFilterParams({ minConfidence: 'abc' }), /between 0 and 1/)
  assert.throws(() => graphFilterParams({ minConfidence: NaN }), /between 0 and 1/)

  assert.deepEqual(
    graphFilterParams({
      relationshipTypes: ['placed_order', 'HAS_PAYMENT', 'PLACED_ORDER'],
    }),
    ['relationship_types=PLACED_ORDER,HAS_PAYMENT'],
  )
  assert.deepEqual(graphFilterParams({ relationshipTypes: [] }), [])
  assert.throws(() => graphFilterParams({ relationshipTypes: ['NOPE'] }), /Unknown relationship type: NOPE/)
  assert.throws(
    () => graphFilterParams({ relationshipTypes: 'PLACED_ORDER' }),
    /Relationship types must be a list\./,
  )

  // Both options: min_confidence first
  assert.deepEqual(
    graphFilterParams({
      minConfidence: 0.8,
      relationshipTypes: ['HAS_SHIPMENT'],
    }),
    ['min_confidence=0.8', 'relationship_types=HAS_SHIPMENT'],
  )
})

test('pathSearchPath constructs valid URLs and enforces constraints (GRF-F1)', () => {
  const defaultPath = pathSearchPath(1, {
    startType: 'CUSTOMER',
    startId: 5,
    endType: 'ORDER',
    endId: '8',
  })
  assert.equal(
    defaultPath,
    'businesses/1/graph/paths/?start_entity_type=CUSTOMER&start_entity_id=5&end_entity_type=ORDER&end_entity_id=8&direction=BIDIRECTIONAL&max_depth=3',
  )

  const fullPath = pathSearchPath(1, {
    startType: 'CUSTOMER',
    startId: 5,
    endType: 'PRODUCT',
    endId: '9',
    direction: 'OUTBOUND',
    maxDepth: 2,
    explain: true,
    minConfidence: 0.9,
    relationshipTypes: ['PLACED_ORDER', 'CONTAINS_PRODUCT'],
  })
  assert.equal(
    fullPath,
    'businesses/1/graph/paths/?start_entity_type=CUSTOMER&start_entity_id=5&end_entity_type=PRODUCT&end_entity_id=9&direction=OUTBOUND&max_depth=2&explain=true&min_confidence=0.9&relationship_types=PLACED_ORDER,CONTAINS_PRODUCT',
  )

  const explainFalse = pathSearchPath(1, {
    startType: 'CUSTOMER',
    startId: 5,
    endType: 'ORDER',
    endId: '8',
    explain: false,
  })
  assert.ok(!explainFalse.includes('explain'))
  assert.ok(!fullPath.includes('limit='))

  // Throws
  assert.throws(() => pathSearchPath(0, {}), /Invalid business ID/)
  assert.throws(() => pathSearchPath('abc', {}), /Invalid business ID/)
  assert.throws(
    () =>
      pathSearchPath(1, {
        startType: 'customer',
        startId: 5,
        endType: 'ORDER',
        endId: 8,
      }),
    /Invalid start entity type: customer/,
  )
  assert.throws(
    () =>
      pathSearchPath(1, {
        startType: 'FOO',
        startId: 5,
        endType: 'ORDER',
        endId: 8,
      }),
    /Invalid start entity type: FOO/,
  )
  assert.throws(
    () =>
      pathSearchPath(1, {
        startType: 'CUSTOMER',
        startId: 5,
        endType: 'BAR',
        endId: 8,
      }),
    /Invalid end entity type: BAR/,
  )
  assert.throws(
    () =>
      pathSearchPath(1, {
        startType: 'CUSTOMER',
        startId: 0,
        endType: 'ORDER',
        endId: 8,
      }),
    /Start ID/,
  )
  assert.throws(
    () =>
      pathSearchPath(1, {
        startType: 'CUSTOMER',
        startId: 'x',
        endType: 'ORDER',
        endId: 8,
      }),
    /Start ID/,
  )
  for (const d of [0, 6, 2.5, '3']) {
    assert.throws(
      () =>
        pathSearchPath(1, {
          startType: 'CUSTOMER',
          startId: 1,
          endType: 'ORDER',
          endId: 2,
          maxDepth: d,
        }),
      /Maximum hops/,
    )
  }
  assert.throws(
    () =>
      pathSearchPath(1, {
        startType: 'CUSTOMER',
        startId: 1,
        endType: 'ORDER',
        endId: 2,
        direction: 'SIDEWAYS',
      }),
    /Invalid direction: SIDEWAYS/,
  )
  assert.throws(
    () =>
      pathSearchPath(1, {
        startType: 'CUSTOMER',
        startId: 1,
        endType: 'ORDER',
        endId: 2,
        explain: 'yes',
      }),
    /explain must be true or false\./,
  )
})

test('graphNodeLabel handles custom labels, fallbacks, and unknowns (GRF-F1)', () => {
  assert.equal(graphNodeLabel({ label: '  Custom Name  ' }), 'Custom Name')
  assert.equal(graphNodeLabel({ label: '   ', entity_type: 'ORDER', entity_id: 20 }), 'ORDER #20')
  assert.equal(graphNodeLabel({ entity_type: 'ORDER', entity_id: 20 }), 'ORDER #20')
  assert.equal(graphNodeLabel({ label: '' }), 'Unknown entity')
  assert.equal(graphNodeLabel(null), 'Unknown entity')
  assert.equal(graphNodeLabel('some string'), 'Unknown entity')
})

test('normalizePathSearch transforms responses and protects privacy (GRF-F1)', () => {
  // (a) Non-explained answer
  const rawNonExplained = {
    business_id: 1,
    paths_found: 1,
    paths: [
      {
        length: 2,
        nodes: [
          { id: 11, entity_type: 'CUSTOMER', entity_id: 5 },
          { id: 12, entity_type: 'ORDER', entity_id: 8 },
          { id: 13, entity_type: 'PRODUCT', entity_id: 2 },
        ],
        edges: [
          { id: 21, relationship_type: 'PLACED_ORDER' },
          { id: 22, relationship_type: 'CONTAINS_PRODUCT' },
        ],
      },
    ],
  }

  const normNonExp = normalizePathSearch(rawNonExplained)
  assert.equal(normNonExp.pathsFound, 1)
  assert.equal(normNonExp.mayHaveMore, false)
  assert.equal(normNonExp.paths.length, 1)
  const p1 = normNonExp.paths[0]
  assert.equal(p1.explained, false)
  assert.equal(p1.length, 2)
  assert.equal(p1.steps.length, 3)
  assert.equal(p1.steps[0].node.label, 'CUSTOMER #5')
  assert.equal(p1.steps[1].node.label, 'ORDER #8')
  assert.equal(p1.steps[2].node.label, 'PRODUCT #2')
  assert.equal(p1.steps[0].edge.relationshipType, 'PLACED_ORDER')
  assert.equal(p1.steps[1].edge.relationshipType, 'CONTAINS_PRODUCT')
  assert.equal(p1.steps[2].edge, null)

  // (b) Explained answer
  const rawExplained = {
    business_id: 1,
    paths_found: 1,
    paths: [
      {
        explanation: [
          {
            node: { id: 101, entity_type: 'CUSTOMER', entity_id: 1, label: 'Alice' },
            edge: null,
          },
          {
            node: {
              id: 102,
              entity_type: 'ORDER',
              entity_id: 50,
              label: 'Order #50',
              facts: [
                {
                  fact_id: 3,
                  fact_type: 'TOTAL_AMOUNT',
                  statement: 'Amount is 500',
                  status: 'VERIFIED',
                  confidence: 0.99,
                },
              ],
              issues: [
                {
                  issue_id: 4,
                  issue_type: 'HIGH_RISK',
                  title: 'Fraud Alert',
                  severity: 'HIGH',
                  status: 'OPEN',
                  description: 'SENTINEL_DESC',
                },
              ],
            },
            edge: {
              id: 201,
              relationship_type: 'PLACED_ORDER',
              confidence: '0.9500',
              evidence: {
                rule_key: 'bi.relationship.customer_order.v1',
                relationship_source: 'DETERMINISTIC',
                valid_from: null,
                valid_to: null,
                metadata: { note: 'SENTINEL_METADATA' },
              },
            },
          },
        ],
      },
    ],
  }

  const normExp = normalizePathSearch(rawExplained)
  assert.equal(normExp.paths.length, 1)
  const expP = normExp.paths[0]
  assert.equal(expP.explained, true)
  assert.equal(expP.steps.length, 2)
  const step2 = expP.steps[1]
  assert.equal(step2.edge.confidencePercent, 95)
  assert.equal(step2.edge.ruleKey, 'bi.relationship.customer_order.v1')
  assert.equal(step2.edge.source, 'DETERMINISTIC')
  assert.deepEqual(step2.facts, [
    {
      id: 3,
      factType: 'TOTAL_AMOUNT',
      statement: 'Amount is 500',
      status: 'VERIFIED',
    },
  ])
  assert.deepEqual(step2.issues, [
    {
      id: 4,
      issueType: 'HIGH_RISK',
      title: 'Fraud Alert',
      severity: 'HIGH',
      status: 'OPEN',
    },
  ])

  const jsonStr = JSON.stringify(normExp)
  assert.ok(!jsonStr.includes('SENTINEL_METADATA'))
  assert.ok(!jsonStr.includes('SENTINEL_DESC'))

  // (c) Edge with evidence: {}
  const rawEmptyEv = {
    paths: [
      {
        explanation: [
          {
            node: { id: 1, entity_type: 'CUSTOMER', entity_id: 1 },
            edge: { id: 2, relationship_type: 'PLACED_ORDER', evidence: {} },
          },
        ],
      },
    ],
  }
  const normEmptyEv = normalizePathSearch(rawEmptyEv)
  assert.equal(normEmptyEv.paths[0].steps[0].edge.ruleKey, null)

  // (d) mayHaveMore boundary: 10 paths vs 9 paths
  const tenPaths = { paths: new Array(10).fill({ nodes: [] }) }
  assert.equal(normalizePathSearch(tenPaths).mayHaveMore, true)
  const ninePaths = { paths: new Array(9).fill({ nodes: [] }) }
  assert.equal(normalizePathSearch(ninePaths).mayHaveMore, false)

  // (e) paths_found fallback
  const noCount = { paths: [{ nodes: [] }, { nodes: [] }] }
  assert.equal(normalizePathSearch(noCount).pathsFound, 2)

  // (f) Junk inputs
  const junkInputs = [null, 'x', {}, { paths: 'no' }, { paths: [null, 5] }]
  for (const j of junkInputs) {
    assert.deepEqual(normalizePathSearch(j), {
      pathsFound: 0,
      mayHaveMore: false,
      paths: [],
    })
  }

  // (g) Length fallback
  const noLength = {
    paths: [
      {
        nodes: [
          { id: 1, entity_type: 'CUSTOMER', entity_id: 1 },
          { id: 2, entity_type: 'ORDER', entity_id: 2 },
        ],
      },
    ],
  }
  assert.equal(normalizePathSearch(noLength).paths[0].length, 1)
})

test('graphErrorMessage maps status, kind, and detail properly (GRF-F1)', () => {
  assert.equal(graphErrorMessage({ status: 403 }), 'You do not have access to this business graph.')
  assert.equal(
    graphErrorMessage({ status: 409, code: 'GRAPH_NOT_BUILT' }),
    'The business graph has not been built yet. An owner or manager can rebuild it from the Data Pipeline tab.',
  )
  assert.equal(
    graphErrorMessage({ status: 404 }),
    'Nothing was found in the graph for that request. If the record is new, rebuild the graph first.',
  )
  assert.equal(graphErrorMessage({ status: 404 }, { notFound: 'Custom not found' }), 'Custom not found')
  assert.equal(
    graphErrorMessage({ status: 400, detail: 'max_depth must be at most 5.' }),
    'max_depth must be at most 5.',
  )
  assert.equal(graphErrorMessage({ status: 400 }), 'The request was not accepted by the server.')
  assert.equal(graphErrorMessage({ status: 500, detail: 'Server broke' }), 'Server broke')
  assert.equal(graphErrorMessage(new Error('boom')), 'boom')
  assert.equal(graphErrorMessage(null), 'The graph request failed. Try again.')
})

test('source checks: graphExplore.js imports and cleanliness (GRF-F1)', () => {
  const libFile = path.resolve('src/lib/intelligence/graphExplore.js')
  const libCode = fs.readFileSync(libFile, 'utf8')

  assert.ok(!libCode.includes('@/'), 'lib must not contain @/ imports')
  assert.ok(!libCode.includes('window'), 'lib must not contain window')
  assert.ok(!libCode.includes('fetch'), 'lib must not contain fetch')

  const importLines = libCode.split('\n').filter((line) => line.trim().startsWith('import '))
  assert.equal(importLines.length, 3, 'Must have exactly three import lines')
  assert.ok(
    libCode.includes("import { businessApiPath } from '../catalog.js'"),
    'Must import businessApiPath from ../catalog.js',
  )
  assert.ok(
    libCode.includes("import { confidencePercent } from './facts.js'"),
    'Must import confidencePercent from ./facts.js',
  )
  assert.ok(
    libCode.includes("import { graphErrorKind } from './graph.js'"),
    'Must import graphErrorKind from ./graph.js',
  )
})
