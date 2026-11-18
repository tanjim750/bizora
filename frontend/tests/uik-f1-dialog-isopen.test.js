import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('UI kit Dialog and Drawer destructure isOpen prop', () => {
  const dialogSource = fs.readFileSync(path.join(ROOT, 'src/components/ui/Dialog.js'), 'utf8')
  const drawerSource = fs.readFileSync(path.join(ROOT, 'src/components/ui/Drawer.js'), 'utf8')

  assert.match(dialogSource, /\bisOpen\b/)
  assert.match(drawerSource, /\bisOpen\b/)
})

test('Support.js passes isOpen to all modal dialogs and drawers (UIK-F1)', () => {
  const source = fs.readFileSync(path.join(ROOT, 'src/components/Support.js'), 'utf8')

  assert.doesNotMatch(source, /^\s+open=\{/m)
  assert.doesNotMatch(source, /<(Dialog|Drawer)\b[^>]*\sopen=\{/)

  assert.match(source, /isOpen=\{callDrawerOpen\}/)
  assert.match(source, /isOpen=\{handoverModalOpen\}/)
  assert.match(source, /isOpen=\{priorityModalOpen\}/)
  assert.match(source, /isOpen=\{callbackModalOpen\}/)
  assert.match(source, /isOpen=\{dialyraCallOpen\}/)
  assert.match(source, /isOpen=\{assignModalOpen\}/)
})

test('Intelligence.js passes isOpen to evidence drawer (UIK-F1)', () => {
  const source = fs.readFileSync(path.join(ROOT, 'src/components/Intelligence.js'), 'utf8')

  assert.doesNotMatch(source, /^\s+open=\{/m)
  assert.doesNotMatch(source, /<(Dialog|Drawer)\b[^>]*\sopen=\{/)

  assert.match(source, /isOpen=\{evidenceDrawerOpen\}/)
})

test('DialyraTelephony.js passes isOpen to trunk status drawer and create dialog (UIK-F1)', () => {
  const source = fs.readFileSync(path.join(ROOT, 'src/components/DialyraTelephony.js'), 'utf8')

  assert.doesNotMatch(source, /^\s+open=\{/m)
  assert.doesNotMatch(source, /<(Dialog|Drawer)\b[^>]*\sopen=\{/)

  assert.match(source, /isOpen=\{statusDrawerOpen\}/)
  assert.match(source, /isOpen=\{createModalOpen\}/)
})
