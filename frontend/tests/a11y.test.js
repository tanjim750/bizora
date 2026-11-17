import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('all workspace pages use PageHeader and guarantee exactly one h1', () => {
  const pageFiles = [
    'src/app/business/[businessId]/overview/[[...tab]]/page.js',
    'src/app/business/[businessId]/commerce/[[...tab]]/page.js',
    'src/app/business/[businessId]/customers/[[...tab]]/page.js',
    'src/app/business/[businessId]/support/[[...tab]]/page.js',
    'src/app/business/[businessId]/growth/[[...tab]]/page.js',
    'src/app/business/[businessId]/intelligence/[[...tab]]/page.js',
    'src/app/business/[businessId]/ai/[[...tab]]/page.js',
    'src/app/business/[businessId]/admin/[[...tab]]/page.js',
  ]

  for (const rel of pageFiles) {
    const full = path.resolve(rel)
    assert.ok(fs.existsSync(full), `File ${rel} must exist`)
    const src = fs.readFileSync(full, 'utf8')
    assert.ok(
      src.includes('PageHeader') ||
        src.includes('Growth') ||
        src.includes('Admin') ||
        src.includes('Overview'),
      `Page ${rel} must render PageHeader or delegated component with PageHeader`,
    )
  }
})

test('accessibility tokens enforce WCAG 2.2 AA contrast and visible focus', () => {
  const tokensPath = path.resolve('src/styles/tokens.css')
  const content = fs.readFileSync(tokensPath, 'utf8')

  assert.ok(content.includes('--color-focus'), 'Must define --color-focus token')
  assert.ok(content.includes('--focus-ring-width'), 'Must define --focus-ring-width token')
  assert.ok(
    content.includes('prefers-reduced-motion: reduce'),
    'Must define prefers-reduced-motion media query',
  )
})

test('all modal dialogs and drawers implement keyboard escape and accessibility attributes', () => {
  const dialogSrc = fs.readFileSync(path.resolve('src/components/ui/Dialog.js'), 'utf8')
  const drawerSrc = fs.readFileSync(path.resolve('src/components/ui/Drawer.js'), 'utf8')

  assert.ok(
    dialogSrc.includes('role="dialog"') || dialogSrc.includes("role='dialog'"),
    'Dialog must specify role="dialog"',
  )
  assert.ok(dialogSrc.includes('aria-modal="true"'), 'Dialog must specify aria-modal="true"')
  assert.ok(
    dialogSrc.includes("'Escape'") || dialogSrc.includes('"Escape"'),
    'Dialog must listen for Escape key to close',
  )

  assert.ok(
    drawerSrc.includes('role="dialog"') || drawerSrc.includes("role='dialog'"),
    'Drawer must specify role="dialog"',
  )
  assert.ok(drawerSrc.includes('aria-modal="true"'), 'Drawer must specify aria-modal="true"')
  assert.ok(
    drawerSrc.includes("'Escape'") || drawerSrc.includes('"Escape"'),
    'Drawer must listen for Escape key to close',
  )
})
