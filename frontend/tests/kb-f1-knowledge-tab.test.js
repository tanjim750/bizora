import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  knowledgeBase,
  SOURCES_PAGE_LIMIT,
  sourcesPath,
  cleanText,
  cleanCount,
  cleanId,
  sourceStatusLabel,
  sourceStatusTone,
  normalizeSources,
  knowledgeErrorReason,
} from '../src/lib/knowledge/api.js'

test('knowledge paths and validations (KB-F1)', () => {
  assert.equal(knowledgeBase(7), 'businesses/7/knowledge/')
  assert.equal(SOURCES_PAGE_LIMIT, 100)
  assert.equal(sourcesPath(1), 'businesses/1/knowledge/sources/?limit=25&offset=0')
  assert.equal(
    sourcesPath(1, { status: 'ACTIVE', limit: 100, offset: 25 }),
    'businesses/1/knowledge/sources/?limit=100&offset=25&status=ACTIVE',
  )
  assert.equal(sourcesPath(1, { status: '' }), 'businesses/1/knowledge/sources/?limit=25&offset=0')

  // Throwing cases
  assert.throws(() => sourcesPath(1, { limit: 0 }), /limit/)
  assert.throws(() => sourcesPath(1, { limit: 101 }), /limit/)
  assert.throws(() => sourcesPath(1, { limit: 1.5 }), /limit/)
  assert.throws(() => sourcesPath(1, { limit: '5' }), /limit/)
  assert.throws(() => sourcesPath(1, { offset: -1 }), /offset/)
  assert.throws(() => sourcesPath(1, { offset: '0' }), /offset/)
  assert.throws(() => sourcesPath(1, { status: 'active' }), /status/)
  assert.throws(() => sourcesPath(1, { status: 'A'.repeat(31) }), /status/)
  assert.throws(() => sourcesPath(0), /Invalid business ID/)
  assert.throws(() => sourcesPath(-1), /Invalid business ID/)
  assert.throws(() => sourcesPath('x'), /Invalid business ID/)
})

test('cleanText, cleanCount, cleanId helpers (KB-F1)', () => {
  assert.equal(cleanText('hello'), 'hello')
  assert.equal(cleanText(''), null)
  assert.equal(cleanText(null), null)
  assert.equal(cleanText(123), null)

  assert.equal(cleanCount(0), 0)
  assert.equal(cleanCount(12), 12)
  assert.equal(cleanCount(-1), null)
  assert.equal(cleanCount(1.5), null)
  assert.equal(cleanCount('12'), null)
  assert.equal(cleanCount(null), null)

  assert.equal(cleanId(1), 1)
  assert.equal(cleanId(0), null)
  assert.equal(cleanId(-1), null)
  assert.equal(cleanId(1.5), null)
  assert.equal(cleanId('1'), null)
  assert.equal(cleanId(null), null)
})

test('sourceStatusLabel and sourceStatusTone (KB-F1)', () => {
  assert.equal(sourceStatusLabel('ACTIVE'), 'Active')
  assert.equal(sourceStatusLabel('DRAFT'), 'Draft (not approved)')
  assert.equal(sourceStatusLabel('DISABLED'), 'Disabled')
  assert.equal(sourceStatusLabel('SUPERSEDED'), 'Superseded')
  assert.equal(sourceStatusLabel('ARCHIVED'), 'Archived')
  assert.equal(sourceStatusLabel('WEIRD_THING'), 'Weird thing')
  assert.equal(sourceStatusLabel(''), 'Unknown')
  assert.equal(sourceStatusLabel(null), 'Unknown')

  assert.equal(sourceStatusTone('ACTIVE'), 'success')
  assert.equal(sourceStatusTone('DRAFT'), 'warning')
  assert.equal(sourceStatusTone('DISABLED'), 'neutral')
  assert.equal(sourceStatusTone('SUPERSEDED'), 'neutral')
  assert.equal(sourceStatusTone('ARCHIVED'), 'neutral')
  assert.equal(sourceStatusTone('OTHER'), 'neutral')
})

test('normalizeSources normalizes data contract and drops extra fields (KB-F1)', () => {
  const fullData = {
    business_id: 1,
    total_count: 10,
    limit: 25,
    offset: 0,
    totals: {
      sources: 5,
      documents: 12,
      ready_documents: 8,
      chunks: 40,
    },
    results: [
      {
        id: 101,
        name: 'FAQ Source',
        source_type: 'MANUAL',
        knowledge_type: 'FAQ',
        status: 'ACTIVE',
        document_count: 3,
        ready_document_count: 2,
        chunk_count: 15,
        created_at: '2026-11-17T09:00:00Z',
        updated_at: '2026-11-17T10:00:00Z',
        extra_secret: 'ignore_me',
      },
      {
        id: 102,
        name: 'Draft Source',
        source_type: 'POLICY',
        knowledge_type: 'GUIDELINES',
        status: 'DRAFT',
        document_count: null,
        ready_document_count: null,
        chunk_count: null,
        created_at: null,
        updated_at: null,
      },
      {
        id: 'bad_id',
        name: 'Dropped',
      },
    ],
  }

  const normalized = normalizeSources(fullData)
  assert.equal(normalized.businessId, 1)
  assert.equal(normalized.total, 10)
  assert.equal(normalized.limit, 25)
  assert.equal(normalized.offset, 0)
  assert.deepEqual(normalized.totals, {
    sources: 5,
    documents: 12,
    ready_documents: 8,
    chunks: 40,
  })
  assert.equal(normalized.results.length, 2)
  assert.equal(normalized.results[0].id, 101)
  assert.equal(normalized.results[0].extra_secret, undefined)
  assert.equal(normalized.results[1].id, 102)
  assert.equal(normalized.results[1].document_count, null)
  assert.equal(normalized.results[1].ready_document_count, null)
  assert.equal(normalized.results[1].chunk_count, null)

  const keys = Object.keys(normalized.results[0]).sort()
  const expectedKeys = [
    'chunk_count',
    'created_at',
    'document_count',
    'id',
    'knowledge_type',
    'name',
    'ready_document_count',
    'source_type',
    'status',
    'updated_at',
  ]
  assert.deepEqual(keys, expectedKeys)

  // Junk and missing totals
  assert.deepEqual(normalizeSources(null), {
    businessId: null,
    total: 0,
    limit: 0,
    offset: 0,
    totals: null,
    results: [],
  })
  assert.deepEqual(normalizeSources('junk'), {
    businessId: null,
    total: 0,
    limit: 0,
    offset: 0,
    totals: null,
    results: [],
  })
  assert.deepEqual(normalizeSources([]), {
    businessId: null,
    total: 0,
    limit: 0,
    offset: 0,
    totals: null,
    results: [],
  })

  const noTotals = normalizeSources({ results: [{ id: 1, name: 'S1' }] })
  assert.equal(noTotals.totals, null)
  assert.equal(noTotals.total, 1)
  assert.equal(noTotals.results.length, 1)
})

test('knowledgeErrorReason formats errors according to contract (KB-F1)', () => {
  assert.equal(
    knowledgeErrorReason({ status: 403 }),
    "You do not have access to this business's knowledge base.",
  )
  assert.equal(
    knowledgeErrorReason({ status: 404 }),
    'The knowledge service is not available on this server.',
  )
  assert.equal(knowledgeErrorReason({ status: 0 }), 'The server could not be reached. Try again in a moment.')
  assert.equal(
    knowledgeErrorReason({ status: 408 }),
    'The server could not be reached. Try again in a moment.',
  )
  assert.equal(
    knowledgeErrorReason({ status: 500 }),
    'The server could not read the knowledge base. Try again later.',
  )
  assert.equal(
    knowledgeErrorReason({ status: 503 }),
    'The server could not read the knowledge base. Try again later.',
  )
  assert.equal(knowledgeErrorReason({ status: 400, detail: 'Bad query' }), 'Bad query')
  assert.equal(knowledgeErrorReason({ status: 400 }), 'The knowledge base could not be loaded.')
  assert.equal(knowledgeErrorReason(null), 'The knowledge base could not be loaded.')
})

test('source checks: KnowledgeBase.js (KB-F1)', () => {
  const filePath = path.join(process.cwd(), 'src/components/KnowledgeBase.js')
  assert.ok(fs.existsSync(filePath), 'KnowledgeBase.js must exist')
  const code = fs.readFileSync(filePath, 'utf8')

  assert.ok(code.trim().startsWith("'use client'"), "Must start with 'use client'")
  assert.ok(code.includes('@/lib/knowledge/api'), 'Must import from knowledge api')
  assert.ok(code.includes('@/lib/clientApi'), 'Must import clientApi')
  assert.ok(code.includes('@/components/ui'), 'Must import from ui')

  const requiredTexts = [
    'Read-only view',
    'Nothing can be added, edited or deleted here.',
    'No knowledge sources yet',
    'Business Memory',
    'aria-live="polite"',
  ]
  for (const text of requiredTexts) {
    assert.ok(code.includes(text), `Must contain text: ${text}`)
  }

  // Raw hex check
  const strippedCode = code.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(strippedCode), 'Must have no raw hex colors')

  // Forbidden words in entire file
  const forbidden = [
    'dangerouslySetInnerHTML',
    'window.confirm',
    "method: 'POST'",
    "method: 'PUT'",
    "method: 'PATCH'",
    "method: 'DELETE'",
    'content_hash',
    'file_url',
    'source_reference',
    'embedding',
    'metadata',
  ]
  for (const word of forbidden) {
    assert.ok(!code.includes(word), `Must not contain: ${word}`)
  }
})

test('source checks: Admin.js integration (KB-F1)', () => {
  const code = fs.readFileSync(path.join(process.cwd(), 'src/components/Admin.js'), 'utf8')
  assert.ok(code.includes("import KnowledgeBase from './KnowledgeBase'"))
  assert.ok(code.includes('<KnowledgeBase'))
  assert.ok(code.includes("currentTab === 'knowledge'"))
  assert.ok(code.includes('Memory & Knowledge Base'))
  assert.ok(!code.includes('Vector knowledge repository'))
})
