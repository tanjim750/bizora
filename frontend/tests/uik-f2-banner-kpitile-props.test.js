import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

function extractKpiTiles(source) {
  const matches = []
  const regex = /<KpiTile\b[\s\S]*?(?:\/>|<\/KpiTile>)/g
  let match
  while ((match = regex.exec(source)) !== null) {
    matches.push(match[0])
  }
  return matches
}

const FILES = [
  { name: 'Growth.js', path: 'src/components/Growth.js', keyText: 'Platform Spend (Platform-reported)' },
  { name: 'Admin.js', path: 'src/components/Admin.js', keyText: 'Integration Health' },
  { name: 'DialyraTelephony.js', path: 'src/components/DialyraTelephony.js', keyText: 'Dialyra Gateway' },
  { name: 'Support.js', path: 'src/components/Support.js', keyText: 'dialyraError' },
]

test('No <Banner> in specified components uses tone= (UIK-F2)', () => {
  for (const { name, path: filePath } of FILES) {
    const source = fs.readFileSync(path.join(ROOT, filePath), 'utf8')
    const lines = source.split('\n')
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      if (line.includes('<Banner')) {
        assert.ok(!line.includes('tone='), `${name} line ${i + 1} has tone= on <Banner line: ${line}`)
      }
    }
    assert.doesNotMatch(source, /<Banner\b[^>]*\btone=/, `${name} should not pass tone= to <Banner>`)
  }
})

test('All <KpiTile> in specified components use title= instead of label= (UIK-F2)', () => {
  for (const { name, path: filePath } of FILES) {
    const source = fs.readFileSync(path.join(ROOT, filePath), 'utf8')
    const tiles = extractKpiTiles(source)
    for (const tile of tiles) {
      assert.ok(!/\blabel=/.test(tile), `${name} has KpiTile with label=: ${tile.slice(0, 100)}`)
      assert.ok(/\btitle=/.test(tile), `${name} has KpiTile missing title=: ${tile.slice(0, 100)}`)
    }
  }
})

test('Growth.js has no variant="neutral" and retains key texts (UIK-F2)', () => {
  const source = fs.readFileSync(path.join(ROOT, 'src/components/Growth.js'), 'utf8')
  assert.doesNotMatch(source, /variant=["']neutral["']/)
  assert.doesNotMatch(source, /tone=["']neutral["']/)
  assert.match(source, /Platform Spend \(Platform-reported\)/)
})

test('Key texts retained in Admin, DialyraTelephony, and Support (UIK-F2)', () => {
  for (const { name, path: filePath, keyText } of FILES.slice(1)) {
    const source = fs.readFileSync(path.join(ROOT, filePath), 'utf8')
    assert.ok(source.includes(keyText), `${name} should retain key text "${keyText}"`)
  }
})
