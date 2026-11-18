import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  DOCUMENTS_PAGE_LIMIT,
  DOCUMENT_STATUS_ORDER,
  documentsPath,
  documentStatusLabel,
  documentStatusTone,
  searchabilityNote,
  normalizeDocuments,
  pageForOffset,
  offsetForPage,
} from '../src/lib/knowledge/documents.js'

test('documentsPath and parameter validation (KB-F1b)', () => {
  assert.equal(DOCUMENTS_PAGE_LIMIT, 25)
  assert.deepEqual(DOCUMENT_STATUS_ORDER, [
    'READY',
    'PUBLISHED',
    'PENDING',
    'FAILED',
    'SUPERSEDED',
    'ARCHIVED',
  ])
  assert.equal(documentsPath(1), 'businesses/1/knowledge/documents/?limit=25&offset=0')
  assert.equal(
    documentsPath(1, { source: 7, status: 'READY', limit: 25, offset: 50 }),
    'businesses/1/knowledge/documents/?limit=25&offset=50&source=7&status=READY',
  )
  assert.equal(
    documentsPath(1, { source: '7', status: 'READY', limit: 25, offset: 50 }),
    'businesses/1/knowledge/documents/?limit=25&offset=50&source=7&status=READY',
  )
  assert.equal(
    documentsPath(1, { source: '', status: '' }),
    'businesses/1/knowledge/documents/?limit=25&offset=0',
  )

  // Throwing cases
  assert.throws(() => documentsPath(1, { limit: 0 }), /limit/)
  assert.throws(() => documentsPath(1, { limit: 101 }), /limit/)
  assert.throws(() => documentsPath(1, { limit: 1.5 }), /limit/)
  assert.throws(() => documentsPath(1, { limit: '5' }), /limit/)
  assert.throws(() => documentsPath(1, { offset: -1 }), /offset/)
  assert.throws(() => documentsPath(1, { status: 'ready' }), /status/)
  assert.throws(() => documentsPath(1, { status: 'A'.repeat(31) }), /status/)
  assert.throws(() => documentsPath(1, { source: 0 }), /source/)
  assert.throws(() => documentsPath(1, { source: -1 }), /source/)
  assert.throws(() => documentsPath(1, { source: 1.5 }), /source/)
  assert.throws(() => documentsPath(1, { source: 'abc' }), /source/)
  assert.throws(() => documentsPath(0), /Invalid business ID/)
  assert.throws(() => documentsPath('x'), /Invalid business ID/)
})

test('documentStatusLabel, documentStatusTone, and searchabilityNote (KB-F1b)', () => {
  assert.equal(documentStatusLabel('READY'), 'Ready')
  assert.equal(documentStatusLabel('PUBLISHED'), 'Published')
  assert.equal(documentStatusLabel('PENDING'), 'Waiting to be processed')
  assert.equal(documentStatusLabel('FAILED'), 'Processing failed')
  assert.equal(documentStatusLabel('SUPERSEDED'), 'Replaced by a newer version')
  assert.equal(documentStatusLabel('ARCHIVED'), 'Archived')
  assert.equal(documentStatusLabel('CUSTOM_STATUS'), 'Custom status')
  assert.equal(documentStatusLabel(''), 'Unknown')
  assert.equal(documentStatusLabel(null), 'Unknown')

  assert.equal(documentStatusTone('READY'), 'success')
  assert.equal(documentStatusTone('PUBLISHED'), 'success')
  assert.equal(documentStatusTone('PENDING'), 'warning')
  assert.equal(documentStatusTone('FAILED'), 'danger')
  assert.equal(documentStatusTone('SUPERSEDED'), 'neutral')
  assert.equal(documentStatusTone('ARCHIVED'), 'neutral')
  assert.equal(documentStatusTone('OTHER'), 'neutral')

  // searchabilityNote 5 outcomes:
  // 1: searchable
  assert.equal(searchabilityNote({ searchable: true }), 'Searchable')
  // 2: source not active
  assert.equal(
    searchabilityNote({ searchable: false, source_status: 'ARCHIVED', status: 'READY', chunk_count: 5 }),
    'Not searchable: its source is not active',
  )
  // 3: document not ready
  assert.equal(
    searchabilityNote({ searchable: false, source_status: 'ACTIVE', status: 'PENDING', chunk_count: 5 }),
    'Not searchable: the document is not ready',
  )
  // 4: zero chunks
  assert.equal(
    searchabilityNote({ searchable: false, source_status: 'ACTIVE', status: 'READY', chunk_count: 0 }),
    'Not searchable: it has no text chunks yet',
  )
  // 5: fallback / other
  assert.equal(
    searchabilityNote({ searchable: false, source_status: '', status: 'READY', chunk_count: 5 }),
    'Not searchable',
  )
})

test('normalizeDocuments normalizes full example and discards unknown keys (KB-F1b)', () => {
  const fullData = {
    business_id: 1,
    total_count: 10,
    limit: 25,
    offset: 0,
    results: [
      {
        id: 201,
        source_id: 101,
        source_name: 'FAQ Source',
        source_status: 'ACTIVE',
        title: 'Return Policy',
        document_type: 'MANUAL',
        mime_type: 'text/markdown',
        version: 2,
        status: 'READY',
        searchable: true,
        is_duplicate: false,
        chunk_count: 4,
        preview: 'Our return policy allows 30 days...',
        ingested_at: '2026-11-17T09:00:00Z',
        processed_at: '2026-11-17T09:05:00Z',
        created_at: '2026-11-17T09:00:00Z',
        updated_at: '2026-11-17T09:05:00Z',
        extra_secret: 'ignore_me',
      },
      {
        id: 202,
        source_id: null,
        source_name: null,
        source_status: null,
        title: null,
        document_type: null,
        mime_type: null,
        version: null,
        status: 'PENDING',
        searchable: 'yes', // must become false
        is_duplicate: 1, // must become false
        chunk_count: null,
        preview: null,
        ingested_at: null,
        processed_at: null,
        created_at: null,
        updated_at: null,
      },
      {
        id: 'bad_id',
        title: 'Dropped',
      },
    ],
  }

  const normalized = normalizeDocuments(fullData)
  assert.equal(normalized.businessId, 1)
  assert.equal(normalized.total, 10)
  assert.equal(normalized.limit, 25)
  assert.equal(normalized.offset, 0)
  assert.equal(normalized.results.length, 2)

  const doc1 = normalized.results[0]
  assert.equal(doc1.id, 201)
  assert.equal(doc1.searchable, true)
  assert.equal(doc1.is_duplicate, false)
  assert.equal(doc1.extra_secret, undefined)

  const doc2 = normalized.results[1]
  assert.equal(doc2.id, 202)
  assert.equal(doc2.version, null)
  assert.equal(doc2.chunk_count, null)
  assert.equal(doc2.searchable, false)
  assert.equal(doc2.is_duplicate, false)

  const expectedKeys = [
    'chunk_count',
    'created_at',
    'document_type',
    'id',
    'ingested_at',
    'is_duplicate',
    'mime_type',
    'preview',
    'processed_at',
    'searchable',
    'source_id',
    'source_name',
    'source_status',
    'status',
    'title',
    'updated_at',
    'version',
  ]
  assert.deepEqual(Object.keys(doc1).sort(), expectedKeys)

  // Junk input
  assert.deepEqual(normalizeDocuments(null), { businessId: null, total: 0, limit: 0, offset: 0, results: [] })
  assert.deepEqual(normalizeDocuments('junk'), {
    businessId: null,
    total: 0,
    limit: 0,
    offset: 0,
    results: [],
  })
  assert.deepEqual(normalizeDocuments([]), { businessId: null, total: 0, limit: 0, offset: 0, results: [] })
})

test('pageForOffset and offsetForPage (KB-F1b)', () => {
  assert.equal(pageForOffset(0, 25), 1)
  assert.equal(pageForOffset(24, 25), 1)
  assert.equal(pageForOffset(25, 25), 2)
  assert.equal(pageForOffset(50, 25), 3)
  assert.equal(pageForOffset(-1, 25), 1)
  assert.equal(pageForOffset(NaN, 25), 1)
  assert.equal(pageForOffset(0, 0), 1)

  assert.equal(offsetForPage(1, 25), 0)
  assert.equal(offsetForPage(2, 25), 25)
  assert.equal(offsetForPage(3, 25), 50)
  assert.equal(offsetForPage(0, 25), 0)
  assert.equal(offsetForPage(-1, 25), 0)
  assert.equal(offsetForPage(NaN, 25), 0)
  assert.equal(offsetForPage(1, 0), 0)
})

test('source checks: KnowledgeDocuments.js (KB-F1b)', () => {
  const filePath = path.join(process.cwd(), 'src/components/KnowledgeDocuments.js')
  assert.ok(fs.existsSync(filePath), 'KnowledgeDocuments.js must exist')
  const code = fs.readFileSync(filePath, 'utf8')

  assert.ok(code.trim().startsWith("'use client'"), "Must start with 'use client'")
  assert.ok(code.includes('@/lib/knowledge/documents'), 'Must import from knowledge documents')
  assert.ok(code.includes('@/lib/clientApi'), 'Must import clientApi')
  assert.ok(code.includes('@/components/ui'), 'Must import from ui kit')

  const requiredTexts = [
    'Filter documents by source',
    'Filter documents by status',
    'No documents',
    'No documents match these filters.',
    'No documents have been stored for this business yet.',
    'Duplicate of a ready document',
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
    'file_name',
    'source_reference',
    'embedding',
    'metadata',
  ]
  for (const word of forbidden) {
    assert.ok(!code.includes(word), `Must not contain: ${word}`)
  }
})

test('source checks: KnowledgeBase.js integration (KB-F1b)', () => {
  const code = fs.readFileSync(path.join(process.cwd(), 'src/components/KnowledgeBase.js'), 'utf8')
  assert.ok(code.includes("import KnowledgeDocuments from './KnowledgeDocuments'"))
  assert.ok(code.includes('<KnowledgeDocuments'))
  assert.ok(code.includes('View documents'))
  assert.ok(!code.includes('KNOWLEDGE_DOCUMENTS_MOUNT'))
  assert.ok(code.includes('KNOWLEDGE_SEARCH_MOUNT') || code.includes('<KnowledgeSearch'))
})
