import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  SEARCH_MIN_CHARS,
  SEARCH_MAX_CHARS,
  SEARCH_MAX_WORDS,
  SEARCH_DEFAULT_LIMIT,
  SEARCH_MAX_LIMIT,
  SCORE_HELP,
  validateSearchQuery,
  searchPath,
  normalizeSearch,
  scoreLabel,
  searchModeNotice,
  resultCountText,
  searchErrorReason,
} from '../src/lib/knowledge/search.js'

test('constants and validateSearchQuery (KB-F2)', () => {
  assert.equal(SEARCH_MIN_CHARS, 2)
  assert.equal(SEARCH_MAX_CHARS, 200)
  assert.equal(SEARCH_MAX_WORDS, 10)
  assert.equal(SEARCH_DEFAULT_LIMIT, 10)
  assert.equal(SEARCH_MAX_LIMIT, 20)
  assert.ok(SCORE_HELP.includes('Keyword relevance for this search only'))

  // Valid queries
  assert.deepEqual(validateSearchQuery('refund'), { ok: true, query: 'refund' })
  assert.deepEqual(validateSearchQuery('  refund  '), { ok: true, query: 'refund' })
  assert.deepEqual(validateSearchQuery('ab'), { ok: true, query: 'ab' })
  assert.deepEqual(validateSearchQuery('a'.repeat(200)), { ok: true, query: 'a'.repeat(200) })
  assert.deepEqual(validateSearchQuery('one two three four five six seven eight nine ten'), {
    ok: true,
    query: 'one two three four five six seven eight nine ten',
  })

  // Failing cases
  assert.deepEqual(validateSearchQuery(undefined), {
    ok: false,
    message: 'Type at least 2 characters to search.',
  })
  assert.deepEqual(validateSearchQuery(''), {
    ok: false,
    message: 'Type at least 2 characters to search.',
  })
  assert.deepEqual(validateSearchQuery(' a '), {
    ok: false,
    message: 'Type at least 2 characters to search.',
  })
  assert.deepEqual(validateSearchQuery('a'.repeat(201)), {
    ok: false,
    message: 'Use at most 200 characters.',
  })
  assert.deepEqual(validateSearchQuery('one two three four five six seven eight nine ten eleven'), {
    ok: false,
    message: 'Use at most 10 words.',
  })
  assert.deepEqual(validateSearchQuery('refund\u0000window'), {
    ok: false,
    message: 'Remove special control characters.',
  })
})

test('searchPath builds valid path and validates parameters (KB-F2)', () => {
  assert.equal(searchPath(1, 'refund window'), 'businesses/1/knowledge/search/?q=refund%20window&limit=10')
  assert.equal(
    searchPath(1, 'refund window', { limit: 20 }),
    'businesses/1/knowledge/search/?q=refund%20window&limit=20',
  )
  assert.ok(searchPath(1, 'a&b=c').includes('q=a%26b%3Dc'))

  assert.throws(() => searchPath(1, 'a'), /Type at least 2 characters to search\./)
  assert.throws(() => searchPath(1, 'valid', { limit: 0 }), /limit must be an integer between 1 and 20/)
  assert.throws(() => searchPath(1, 'valid', { limit: 21 }), /limit must be an integer between 1 and 20/)
  assert.throws(() => searchPath(1, 'valid', { limit: 1.5 }), /limit must be an integer between 1 and 20/)
  assert.throws(() => searchPath(1, 'valid', { limit: '5' }), /limit must be an integer between 1 and 20/)
  assert.throws(() => searchPath(0, 'valid'), /Invalid business ID/)
})

test('normalizeSearch normalizes data contract and drops extra fields (KB-F2)', () => {
  const fullData = {
    business_id: 1,
    query: 'refund window',
    mode: 'KEYWORD',
    semantic_available: false,
    limit: 10,
    result_count: 1,
    results: [
      {
        chunk_id: 301,
        chunk_index: 0,
        document_id: 201,
        document_title: 'Return Policy',
        document_type: 'MANUAL',
        version: 1,
        source_id: 101,
        source_name: 'FAQ',
        section: 'Policy Details',
        score: 3.14159,
        snippet: 'Customers have a 30-day refund window...',
        extra_secret: 'ignore_me',
      },
      {
        chunk_id: null,
        snippet: 'dropped',
      },
    ],
  }

  const normalized = normalizeSearch(fullData)
  assert.equal(normalized.businessId, 1)
  assert.equal(normalized.query, 'refund window')
  assert.equal(normalized.mode, 'KEYWORD')
  assert.equal(normalized.semanticAvailable, false)
  assert.equal(normalized.limit, 10)
  assert.equal(normalized.resultCount, 1)
  assert.equal(normalized.results.length, 1)

  const res = normalized.results[0]
  assert.equal(res.chunk_id, 301)
  assert.equal(res.score, 3.14159)
  assert.equal(res.extra_secret, undefined)

  const expectedKeys = [
    'chunk_id',
    'chunk_index',
    'document_id',
    'document_title',
    'document_type',
    'score',
    'section',
    'snippet',
    'source_id',
    'source_name',
    'version',
  ]
  assert.deepEqual(Object.keys(res).sort(), expectedKeys)

  // semantic_available: 'true' gives false
  const strBool = normalizeSearch({ semantic_available: 'true', results: [] })
  assert.equal(strBool.semanticAvailable, false)

  // missing fields fallback
  const missingFields = normalizeSearch({
    results: [
      {
        chunk_id: 302,
        section: null,
        document_type: null,
        snippet: null,
        score: null,
      },
    ],
  })
  assert.equal(missingFields.results[0].section, null)
  assert.equal(missingFields.results[0].document_type, null)
  assert.equal(missingFields.results[0].snippet, '')
  assert.equal(missingFields.results[0].score, null)

  // Non-finite score
  const badScore = normalizeSearch({
    results: [{ chunk_id: 303, score: NaN }],
  })
  assert.equal(badScore.results[0].score, null)

  // Junk inputs
  assert.deepEqual(normalizeSearch(null), {
    businessId: null,
    query: '',
    mode: 'KEYWORD',
    semanticAvailable: false,
    limit: 0,
    resultCount: 0,
    results: [],
  })
  assert.deepEqual(normalizeSearch('junk'), {
    businessId: null,
    query: '',
    mode: 'KEYWORD',
    semanticAvailable: false,
    limit: 0,
    resultCount: 0,
    results: [],
  })
})

test('scoreLabel, searchModeNotice, resultCountText, searchErrorReason (KB-F2)', () => {
  assert.equal(scoreLabel(3.142), 'Score 3.14')
  assert.equal(scoreLabel(0), 'Score 0.00')
  assert.equal(scoreLabel(null), 'No score')
  assert.equal(scoreLabel(NaN), 'No score')
  assert.equal(scoreLabel('3'), 'No score')

  assert.equal(
    searchModeNotice({ mode: 'KEYWORD', semanticAvailable: false }),
    'Keyword search: results contain the words you typed. Semantic (meaning-based) search is not available in this version.',
  )
  assert.equal(
    searchModeNotice({ mode: '', semanticAvailable: false }),
    'Keyword search: results contain the words you typed. Semantic (meaning-based) search is not available in this version.',
  )
  assert.equal(
    searchModeNotice({ mode: 'HYBRID', semanticAvailable: false }),
    'Keyword search: results contain the words you typed. Semantic (meaning-based) search is not available in this version.',
  )
  assert.equal(searchModeNotice({ mode: 'HYBRID', semanticAvailable: true }), 'Search mode: Hybrid.')

  assert.equal(resultCountText(0, 10), 'No matches')
  assert.equal(resultCountText(1, 10), '1 match')
  assert.equal(resultCountText(7, 10), '7 matches')
  assert.equal(resultCountText(10, 10), 'Showing the best 10 matches. There may be more.')
  assert.equal(resultCountText(1, 1), 'Showing the best 1 match. There may be more.')
  assert.equal(resultCountText(3, 3), 'Showing the best 3 matches. There may be more.')

  // searchErrorReason
  assert.equal(
    searchErrorReason({ status: 400, raw: { fields: { q: 'Query word is banned.' } } }),
    'Query word is banned.',
  )
  assert.equal(searchErrorReason({ status: 400, detail: 'Malformed query.' }), 'Malformed query.')
  assert.equal(searchErrorReason({ status: 404 }), 'The knowledge service is not available on this server.')
  assert.equal(searchErrorReason(null), 'The knowledge base could not be loaded.')
})

test('source checks: KnowledgeSearch.js (KB-F2)', () => {
  const filePath = path.join(process.cwd(), 'src/components/KnowledgeSearch.js')
  assert.ok(fs.existsSync(filePath), 'KnowledgeSearch.js must exist')
  const code = fs.readFileSync(filePath, 'utf8')

  assert.ok(code.trim().startsWith("'use client'"), "Must start with 'use client'")
  assert.ok(code.includes('@/lib/knowledge/search'), 'Must import from search lib')
  assert.ok(code.includes('@/lib/clientApi'), 'Must import clientApi')
  assert.ok(code.includes('@/components/ui'), 'Must import from ui')

  const requiredTexts = [
    'Search the knowledge base',
    'role="search"',
    'aria-live="polite"',
    'searchModeNotice',
    'SCORE_HELP',
    'No matches',
    'Type a word or phrase',
    'Try different words',
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
    'innerHTML',
    'window.confirm',
    "method: 'POST'",
    "method: 'PUT'",
    "method: 'PATCH'",
    "method: 'DELETE'",
    'AI search',
    'smart',
    'intelligent',
    'similar results',
    'recommended',
  ]
  for (const word of forbidden) {
    assert.ok(!code.includes(word), `Must not contain: ${word}`)
  }
})

test('source checks: KnowledgeBase.js integration (KB-F2)', () => {
  const code = fs.readFileSync(path.join(process.cwd(), 'src/components/KnowledgeBase.js'), 'utf8')
  assert.ok(code.includes("import KnowledgeSearch from './KnowledgeSearch'"))
  assert.ok(code.includes('<KnowledgeSearch'))
  assert.ok(!code.includes('KNOWLEDGE_SEARCH_MOUNT'))
})
