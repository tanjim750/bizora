import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8')

test('BizoraLogo component renders geometric neural graph SVG with proper accessibility attributes', () => {
  const logoSource = read('../src/components/ui/BizoraLogo.js')

  // Accessible SVG structure
  assert.match(logoSource, /<svg/)
  assert.match(logoSource, /aria-hidden="true"/)
  assert.match(logoSource, /viewBox="0 0 32 32"/)

  // Geometric facets and neural node elements
  assert.match(logoSource, /<linearGradient id="bizora-logo-bg"/)
  assert.match(logoSource, /<circle cx="16" cy="16"/) // central brain node
  assert.match(logoSource, /bizora-logo-specular/)

  // Configurable props
  assert.match(logoSource, /size = 32/)
  assert.match(logoSource, /showText = true/)
  assert.match(logoSource, /bizora-brand-text/)
  assert.match(logoSource, /bizora-brand-dot/)
})

test('BizoraLogo is exported from the shared UI kit barrel index', () => {
  const uiIndex = read('../src/components/ui/index.js')
  assert.match(uiIndex, /BizoraLogo/)
})

test('Workspace picker client integrates BizoraLogo, accessible search bar, and shortcuts', () => {
  const workspacePicker = read('../src/app/workspace/WorkspacePickerClient.js')

  // Logo integration
  assert.match(workspacePicker, /<BizoraLogo/)

  // Accessible search input and clear button
  assert.match(workspacePicker, /id="workspace-search"/)
  assert.match(workspacePicker, /aria-label="Search workspaces"/)
  assert.match(workspacePicker, /aria-label="Clear search query"/)
  assert.match(workspacePicker, /workspace-search-badge/)

  // Multi-tenant enterprise environment hero
  assert.match(workspacePicker, /workspace-hero-badge/)
  assert.match(workspacePicker, /Enterprise Multi-Tenant Environment/)

  // Direct quick-jump shortcuts
  assert.match(workspacePicker, /shortcut-pill/)
  assert.match(workspacePicker, /Overview/)
  assert.match(workspacePicker, /Commerce/)
  assert.match(workspacePicker, /Support/)
  assert.match(workspacePicker, /AI Studio/)
})
